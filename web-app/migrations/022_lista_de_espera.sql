-- =====================================================================
-- 022_lista_de_espera.sql — UI-14
--
-- O QUE MUDA
--
-- A lista de espera do lançamento: quem ainda não tem conta deixa o e-mail
-- (e, se quiser, como prefere ser chamado) para ser avisado do lançamento e
-- convidado para os primeiros testes. É dado pessoal de quem NÃO é titular de
-- conta nenhuma, e por isso vive numa tabela à parte, sem `user_id`.
--
--   1. `lista_de_espera`: e-mail, nome opcional, a versão do texto que a
--      pessoa aceitou e quando. RLS LIGADO e NENHUMA policy; nenhum papel do
--      cliente (`anon`, `authenticated`) nem a ingestão tem privilégio de
--      tabela. Ninguém lê pela API: o autor vê a lista pelo painel do
--      Supabase, que usa o dono do banco.
--   2. `versao_da_lista_de_espera()`: o texto vigente do consentimento. O
--      backend (`lista_de_espera.py`) e o frontend (`lib/listaDeEspera.ts`)
--      têm a mesma constante; `test_lista_de_espera.py` confere as três.
--   3. `inscrever_na_lista_de_espera(e-mail, nome, versão)`: o ÚNICO caminho
--      de escrita. Normaliza e valida no banco (as restrições da tabela são a
--      última palavra), recusa versão errada, ignora e-mail repetido sem
--      dizer se ele já estava lá (ninguém descobre quem está na lista), e
--      recusa com `PT429` acima de 100 inscrições na última hora — o teto
--      global contra enxurrada, sem guardar IP de ninguém.
--      Só o papel `dormio_ingestao` executa: o backend a chama depois do
--      honeypot e da validação; com a chave `anon`, que é pública, ninguém a
--      alcança direto.
--   4. `expurgar_lista_de_espera()`: apaga inscrições com mais de 12 meses
--      (o prazo da política, seção 7). Ninguém do cliente executa; o
--      agendamento é no `pg_cron`, como o expurgo da 013.
--
-- ORDEM COM O RELEASE
--
-- Aplicar ANTES do release que publica a página: sem a 022, a rota responde
-- 503 a toda inscrição. Nada do que já existe muda.
--
-- Conferir depois: `DIAGNOSTICO-migracoes-aplicadas.sql`, linha da 022.
-- =====================================================================

begin;

-- ---------------------------------------------------------------------
-- 1. A tabela
-- ---------------------------------------------------------------------
create table if not exists public.lista_de_espera (
    id                   uuid primary key default gen_random_uuid(),
    email                text not null,
    nome                 text,
    consentimento_versao text not null,
    inscrito_em          timestamptz not null default now(),
    constraint lista_de_espera_email_valido check (
        char_length(email) between 6 and 254
        and email = lower(email)
        and email ~ '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]{2,}$'),
    constraint lista_de_espera_nome_valido check (
        nome is null or char_length(nome) between 1 and 80)
);

create unique index if not exists lista_de_espera_email_unico
    on public.lista_de_espera (email);

comment on table public.lista_de_espera is
    'UI-14. Contatos de quem quer ser avisado do lancamento. Finalidade unica: o '
    'aviso e o convite para os primeiros testes (politica, secao 2.6). Sem '
    'policy e sem privilegio para o cliente: escrita so por '
    'inscrever_na_lista_de_espera(), leitura so pelo dono do banco.';
comment on column public.lista_de_espera.email is
    'UI-14. O e-mail para o aviso, em minusculas.';
comment on column public.lista_de_espera.nome is
    'UI-14. Como a pessoa prefere ser chamada. Opcional.';
comment on column public.lista_de_espera.consentimento_versao is
    'UI-14. A versao do texto do consentimento aceita (versao_da_lista_de_espera()).';
comment on column public.lista_de_espera.inscrito_em is
    'UI-14. Quando a inscricao entrou, pelo relogio do banco. Conta o prazo de 12 meses.';

alter table public.lista_de_espera enable row level security;

-- Os privilégios padrão do Supabase dão tudo a `anon` e `authenticated` em
-- tabela nova (a 009 revoga os das tabelas que existiam). Esta nasce sem nada.
revoke all on public.lista_de_espera from public;
do $$
declare
    papel text;
begin
    foreach papel in array array['anon', 'authenticated', 'service_role', 'dormio_ingestao'] loop
        if exists (select 1 from pg_roles where rolname = papel) then
            execute format('revoke all on public.lista_de_espera from %I', papel);
        end if;
    end loop;
end $$;

-- ---------------------------------------------------------------------
-- 2. A versão vigente do texto do consentimento
-- ---------------------------------------------------------------------
create or replace function public.versao_da_lista_de_espera()
returns text
language sql
immutable
set search_path = ''
as $$ select '2026-11-19'::text $$;

-- ---------------------------------------------------------------------
-- 3. Inscrever
-- ---------------------------------------------------------------------
create or replace function public.inscrever_na_lista_de_espera(
    p_email text, p_nome text, p_versao text)
returns void
language plpgsql
volatile
security definer
set search_path = ''
as $$
declare
    v_email text := lower(btrim(coalesce(p_email, '')));
    v_nome  text := nullif(btrim(coalesce(p_nome, '')), '');
begin
    if p_versao is distinct from public.versao_da_lista_de_espera() then
        raise exception using errcode = 'check_violation',
            message = 'UI-14: versao do texto do consentimento desatualizada';
    end if;

    -- O teto conta com a tabela travada para escrita da lista: duas
    -- inscrições simultâneas não passam juntas do limite.
    perform pg_advisory_xact_lock(hashtext('public.lista_de_espera'));
    if (select count(*) from public.lista_de_espera
         where inscrito_em > now() - interval '1 hour') >= 100 then
        raise exception using errcode = 'PT429', message = 'lista_cheia';
    end if;

    insert into public.lista_de_espera (email, nome, consentimento_versao)
    values (v_email, v_nome, p_versao)
    on conflict (email) do nothing;
end;
$$;

comment on function public.inscrever_na_lista_de_espera(text, text, text) is
    'UI-14. Unico caminho de escrita da lista. E-mail repetido nao muda nada e '
    'nao e revelado. Acima de 100 inscricoes na ultima hora: PT429 lista_cheia.';

-- ---------------------------------------------------------------------
-- 4. O expurgo dos 12 meses
-- ---------------------------------------------------------------------
create or replace function public.expurgar_lista_de_espera()
returns integer
language plpgsql
volatile
security definer
set search_path = ''
as $$
declare
    v_apagadas integer;
begin
    delete from public.lista_de_espera
     where inscrito_em < now() - interval '12 months';
    get diagnostics v_apagadas = row_count;
    return v_apagadas;
end;
$$;

comment on function public.expurgar_lista_de_espera() is
    'UI-14. Apaga as inscricoes com mais de 12 meses (politica, secao 7). '
    'Agendada no pg_cron; nenhum papel do cliente executa.';

-- ---------------------------------------------------------------------
-- 5. Quem executa o quê
--    Os privilégios padrão do Supabase dão EXECUTE a `anon`, `authenticated`
--    e `service_role` em função nova. Tudo sai; só a inscrição volta, e só
--    para a ingestão.
-- ---------------------------------------------------------------------
revoke all on function public.versao_da_lista_de_espera() from public;
revoke all on function public.inscrever_na_lista_de_espera(text, text, text) from public;
revoke all on function public.expurgar_lista_de_espera() from public;
do $$
declare
    papel text;
begin
    foreach papel in array array['anon', 'authenticated', 'service_role', 'dormio_ingestao'] loop
        if exists (select 1 from pg_roles where rolname = papel) then
            execute format('revoke all on function public.versao_da_lista_de_espera() from %I', papel);
            execute format('revoke all on function public.inscrever_na_lista_de_espera(text, text, text) from %I', papel);
            execute format('revoke all on function public.expurgar_lista_de_espera() from %I', papel);
        end if;
    end loop;
    if exists (select 1 from pg_roles where rolname = 'dormio_ingestao') then
        grant execute on function public.inscrever_na_lista_de_espera(text, text, text) to dormio_ingestao;
    end if;
end $$;

-- ---------------------------------------------------------------------
-- 6. O agendamento diário, se houver `pg_cron`
--    04:37 UTC, vinte minutos depois do expurgo das contas (013).
-- ---------------------------------------------------------------------
do $$
begin
    if exists (select 1 from pg_extension where extname = 'pg_cron') then
        perform cron.schedule(
            'dormio-expurgo-da-lista-de-espera',
            '37 4 * * *',
            'select public.expurgar_lista_de_espera()'
        );
        raise notice 'UI-14: expurgo da lista de espera agendado (diario, 04:37 UTC).';
    else
        raise notice
            'UI-14: a extensao pg_cron NAO esta ligada; a lista foi criada, mas o '
            'expurgo dos 12 meses NAO foi agendado. Ligue-a e rode este arquivo de novo.';
    end if;
end $$;

commit;
