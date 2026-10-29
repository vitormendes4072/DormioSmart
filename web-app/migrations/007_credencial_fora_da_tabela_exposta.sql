-- =====================================================================
-- 007_credencial_fora_da_tabela_exposta.sql — SEC-08
--
-- Move `devices.token_hash` para uma tabela que o PostgREST não alcança.
--
-- ---------------------------------------------------------------------
-- O QUE ESTAVA ERRADO — e era o comentário, antes do código
-- ---------------------------------------------------------------------
--
-- `web-app/dispositivos.py` declarava:
--
--     # Campos devolvidos ao cliente. `token_hash` NUNCA entra nesta lista:
--     # ele não tem utilidade para a interface e é material sensível.
--
-- A lista está correta e a intenção também. O problema é que ela **não
-- protege nada**: a lista de campos é da camada Python, e o cliente do
-- navegador não passa pela camada Python. O frontend fala direto com o
-- PostgREST usando a chave `anon` — que é pública por design, está dito em
-- `frontend/src/lib/supabase.ts` — mais um JWT de usuário. Com os dois, um
-- `select=token_hash` devolve a coluna, porque o GRANT do Supabase é de
-- TABELA: `authenticated` tinha select em `devices`, e select de tabela
-- alcança toda coluna dela.
--
-- Severidade real: baixa. O que se obtinha era o SHA-256 do token do PRÓPRIO
-- dispositivo (o RLS nunca deixou ler o de outro — verificado em
-- `tests/rls/test_rls_isolamento.py::test_ana_nao_le_o_token_hash_do_bruno`).
-- Do hash não se volta ao token: 256 bits de entropia aleatória, sem
-- dicionário a atacar. Ninguém sequestra dispositivo com isso.
--
-- Mas a proteção que o comentário anunciava não existia, e essa distância
-- entre o que o código diz e o que o código faz é o problema a consertar --
-- mais do que o hash em si. Um comentário que promete proteção inexistente é
-- pior que nenhum comentário: ele encerra a análise de quem for revisar.
--
-- ---------------------------------------------------------------------
-- POR QUE TABELA SEPARADA, E NÃO PERMISSÃO POR COLUNA
-- ---------------------------------------------------------------------
--
-- A alternativa era `revoke select on devices` + `grant select (colunas)`. O
-- Postgres não deixa revogar uma coluna de um GRANT de tabela — privilégio de
-- tabela implica todas as colunas — então seria preciso trocar o grant de
-- tabela por um de colunas. Funciona, e tem duas consequências ruins:
--
--   1. `select *` passa a falhar por permissão. É o default do PostgREST e de
--      qualquer cliente novo. Quem escrevesse uma consulta inocente receberia
--      "permission denied for table devices" — mensagem que aponta para a
--      tabela toda e não diz qual coluna é o problema.
--
--   2. O INSERT do pareamento volta com `return=representation`, que também é
--      um select. Limitar as colunas do retorno depende de como a lib
--      monta o `?select=` no POST — detalhe de versão da `postgrest-py`, não
--      de esquema. Prender a proteção da credencial a isso é frágil.
--
-- Com a coluna em outra tabela, sem GRANT nenhum para `anon`/`authenticated`,
-- não há o que revogar nem o que escapar: o PostgREST não expõe tabela em que
-- o papel não tem privilégio. `select *` em `devices` volta a funcionar e não
-- traz credencial porque ela não está lá.
--
-- ---------------------------------------------------------------------
-- CONSEQUÊNCIA: O PAREAMENTO VIRA FUNÇÃO
-- ---------------------------------------------------------------------
--
-- Se `authenticated` não tem privilégio na tabela nova, o cliente do usuário
-- não pode mais gravar o hash direto. O pareamento passa por
-- `parear_dispositivo()`, `security definer`, que cria as duas linhas numa
-- transação e deriva o dono de `auth.uid()`.
--
-- Ganho colateral, e não pequeno: o hash deixa de trafegar por uma consulta
-- que o cliente monta. Ele vai como argumento de uma função que decide o que
-- fazer com ele. O `user_id` também deixa de ser informado pelo cliente.
--
-- Idempotente: pode rodar mais de uma vez sem efeito adicional.
-- =====================================================================

begin;

-- ---------------------------------------------------------------------
-- 1. A tabela da credencial
--
--    RLS ligado E sem policy nenhuma, de propósito — cinto e suspensório. O
--    que de fato barra o acesso é a ausência de GRANT (o PostgREST não expõe a
--    tabela), mas se um dia alguém der `grant select` aqui por engano, o RLS
--    sem policy ainda nega. As duas camadas erram por caminhos diferentes.
-- ---------------------------------------------------------------------
create table if not exists public.device_tokens (
    device_id   uuid primary key references public.devices(id) on delete cascade,
    token_hash  text not null unique,
    created_at  timestamptz not null default now()
);

comment on table public.device_tokens is
    'SHA-256 do token de cada dispositivo. FORA de `devices` porque aquela '
    'tabela e exposta ao PostgREST e GRANT de tabela alcanca toda coluna. '
    'Sem GRANT para anon/authenticated: nao e alcancavel pelo cliente.';

alter table public.device_tokens enable row level security;

-- Revogação NOMINAL (SEC-12, 28/10). No Supabase a tabela nasce com ALL para
-- `anon` e `authenticated` (privilégios padrão de `public`); sem esta linha o
-- comentário acima seria falso e a única proteção seria o RLS. Medido: até
-- 28/10 esta migração não tinha a linha, e a suíte não via porque não
-- reproduzia os privilégios padrão.
revoke all on public.device_tokens from anon, authenticated;

-- `on delete cascade`: apagar o dispositivo apaga a credencial dele. Importa
-- para a SEC-07 — a exclusão de conta apaga `devices`, e uma credencial órfã
-- sobrevivente seria dado remanescente de uma conta que não existe mais.
create index if not exists device_tokens_hash_idx
    on public.device_tokens (token_hash);

-- ---------------------------------------------------------------------
-- 2. Migrar os hashes existentes
--
--    Condicional: se a coluna já não existe, esta migração já rodou.
-- ---------------------------------------------------------------------
do $$
begin
    if exists (
        select 1 from information_schema.columns
         where table_schema = 'public'
           and table_name = 'devices'
           and column_name = 'token_hash'
    ) then
        insert into public.device_tokens (device_id, token_hash)
        select id, token_hash from public.devices
         where token_hash is not null
        on conflict (device_id) do nothing;

        raise notice 'Hashes migrados de devices para device_tokens.';
    end if;
end $$;

-- ---------------------------------------------------------------------
-- 3. resolver_dispositivo() — agora faz junção
--
--    Reescrita da 005. A assinatura e o retorno não mudam, então nada no
--    Python precisa saber que a credencial mudou de lugar.
-- ---------------------------------------------------------------------
create or replace function public.resolver_dispositivo(p_token_hash text)
returns table (id uuid, user_id uuid)
language sql
stable
security definer
set search_path = ''
as $$
    select d.id, d.user_id
      from public.device_tokens t
      join public.devices d on d.id = t.device_id
     where t.token_hash = p_token_hash
       and d.revoked_at is null
     limit 1
$$;

comment on function public.resolver_dispositivo(text) is
    'Token -> (device, dono). A credencial vive em device_tokens (SEC-08); a '
    'revogacao continua em devices.revoked_at e vale aqui dentro (SEC-02).';

-- ---------------------------------------------------------------------
-- 4. registrar_leitura() — mesma junção
-- ---------------------------------------------------------------------
create or replace function public.registrar_leitura(
    p_token_hash text,
    p_leitura    jsonb
)
returns bigint
language plpgsql
volatile
security definer
set search_path = ''
as $$
declare
    v_device uuid;
    v_dono   uuid;
    v_id     bigint;
begin
    select d.id, d.user_id into v_device, v_dono
      from public.device_tokens t
      join public.devices d on d.id = t.device_id
     where t.token_hash = p_token_hash
       and d.revoked_at is null
     limit 1;

    if v_device is null then
        return null;
    end if;

    insert into public.sleep_data (
        accel_x, accel_y, accel_z,
        gyro_x,  gyro_y,  gyro_z,
        temp, movimento_total, status,
        captured_at, epoca_segundos, metodo_agregacao, amostras,
        user_id, device_id
    ) values (
        (p_leitura ->> 'accel_x')::double precision,
        (p_leitura ->> 'accel_y')::double precision,
        (p_leitura ->> 'accel_z')::double precision,
        (p_leitura ->> 'gyro_x')::double precision,
        (p_leitura ->> 'gyro_y')::double precision,
        (p_leitura ->> 'gyro_z')::double precision,
        (p_leitura ->> 'temp')::double precision,
        (p_leitura ->> 'movimento_total')::double precision,
        (p_leitura ->> 'status')::text,
        (p_leitura ->> 'captured_at')::timestamptz,
        (p_leitura ->> 'epoca_segundos')::integer,
        (p_leitura ->> 'metodo_agregacao')::text,
        (p_leitura ->> 'amostras')::integer,
        v_dono,
        v_device
    )
    returning id into v_id;

    begin
        update public.devices set last_seen_at = now() where id = v_device;
    exception when others then
        null;
    end;

    return v_id;
end;
$$;

-- ---------------------------------------------------------------------
-- 5. parear_dispositivo() — cria dispositivo e credencial numa transação
--
--    `security definer` só por causa de `device_tokens`. O dono vem de
--    `auth.uid()`, nunca de parâmetro — mesma regra das outras funções.
--
--    Devolve a linha do dispositivo SEM a credencial. O token em claro nunca
--    entra no banco: quem o gera é o backend, que devolve ao usuário uma única
--    vez e guarda só o hash.
-- ---------------------------------------------------------------------
create or replace function public.parear_dispositivo(
    p_nome       text,
    p_tipo       text,
    p_token_hash text
)
returns table (
    id           uuid,
    nome         text,
    tipo         text,
    created_at   timestamptz,
    last_seen_at timestamptz,
    revoked_at   timestamptz
)
language plpgsql
volatile
security definer
set search_path = ''
as $$
declare
    v_dono   uuid := auth.uid();
    v_device uuid;
begin
    if v_dono is null then
        return;
    end if;

    -- A validação de `tipo` também existe em Python (`dispositivos.validar_tipo`).
    -- Aqui é a `check constraint` da 004 que segura, e ela é a autoridade: a
    -- validação em Python melhora a mensagem de erro, não a garantia.
    insert into public.devices (user_id, nome, tipo)
    values (v_dono, p_nome, coalesce(p_tipo, 'travesseiro'))
    returning devices.id into v_device;

    insert into public.device_tokens (device_id, token_hash)
    values (v_device, p_token_hash);

    return query
        select d.id, d.nome, d.tipo, d.created_at, d.last_seen_at, d.revoked_at
          from public.devices d
         where d.id = v_device;
end;
$$;

comment on function public.parear_dispositivo(text, text, text) is
    'Cria dispositivo + credencial numa transacao. Dono de auth.uid(), nunca '
    'de parametro. Nao devolve o token_hash.';

revoke all on function public.parear_dispositivo(text, text, text) from public;
-- `from public` não alcança o EXECUTE nominal que o Supabase dá a `anon` em
-- toda função nova (SEC-12). Precisa ser dito pelo nome.
revoke all on function public.parear_dispositivo(text, text, text) from anon;
grant execute on function public.parear_dispositivo(text, text, text) to authenticated;

-- ---------------------------------------------------------------------
-- 6. A policy de insert em `devices` deixa de ser necessária
--
--    O único caminho de criação passou a ser `parear_dispositivo()`, que é
--    definer. Manter `devices_insert_own` deixaria aberta a criação de
--    dispositivo SEM credencial — linha que o caminho por token nunca resolve
--    e que ninguém consegue explicar depois. Removida.
--
--    `select`, `update` e `delete` continuam: listar, renomear, revogar e
--    apagar seguem sendo operações diretas do dono, sob RLS.
-- ---------------------------------------------------------------------
drop policy if exists devices_insert_own on public.devices;

-- ---------------------------------------------------------------------
-- 7. Finalmente, a coluna sai de `devices`
--
--    Depois da migração dos dados (bloco 2) e da reescrita das funções
--    (blocos 3-5). Nesta ordem: se a migração for interrompida entre eles, o
--    pior estado é hash duplicado em dois lugares — recuperável. Na ordem
--    inversa, seria credencial perdida.
--
--    Derruba com ela o índice `devices_token_hash_idx` e a restrição de
--    unicidade, substituídos pelos de `device_tokens`.
-- ---------------------------------------------------------------------
alter table public.devices drop column if exists token_hash;

commit;

-- =====================================================================
-- VERIFICAÇÃO — rodar depois do commit
-- =====================================================================
--
-- 1. A coluna saiu de `devices` (esperado: 0 linhas)
--
-- select column_name from information_schema.columns
--  where table_schema = 'public' and table_name = 'devices'
--    and column_name = 'token_hash';
--
-- 2. Nenhum hash foi perdido (esperado: as duas contagens iguais)
--
-- select (select count(*) from public.devices) as dispositivos,
--        (select count(*) from public.device_tokens) as credenciais;
--
-- 3. `anon` e `authenticated` NAO alcancam a tabela nova (esperado: 0 linhas)
--
-- select grantee, privilege_type from information_schema.table_privileges
--  where table_schema = 'public' and table_name = 'device_tokens'
--    and grantee in ('anon', 'authenticated');
--
-- 4. O caminho de ingestao continua resolvendo (esperado: 1 linha por token valido)
--
-- select * from public.resolver_dispositivo(
--     (select token_hash from public.device_tokens limit 1));
-- =====================================================================
