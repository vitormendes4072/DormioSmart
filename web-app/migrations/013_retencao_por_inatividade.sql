-- =====================================================================
-- 013_retencao_por_inatividade.sql — LGPD-02
-- =====================================================================
-- O QUE MUDA
--
-- Até aqui não havia política de retenção: uma leitura ficava no banco até o
-- titular apagar a conta (seção 7 da política de privacidade, que declarava
-- isso como lacuna). A regra adotada em 05/11/2026 é a do mercado de
-- aparelhos de sono e atividade:
--
--   · enquanto a conta é usada, os dados ficam (a finalidade é o histórico do
--     próprio titular, e ele os apaga quando quiser — migração 006);
--   · conta INATIVA HÁ 12 MESES é eliminada por inteiro, do mesmo jeito que a
--     exclusão pedida pelo titular.
--
-- "Inativa" = nenhum dos quatro sinais nos últimos 12 meses: criação da conta,
-- último login (`auth.users.last_sign_in_at`), uso de uma sessão (a criação, a
-- `updated_at` e a `refreshed_at` de `auth.sessions`) e última leitura recebida
-- (`sleep_data.created_at`). A leitura conta porque o dispositivo pode seguir
-- enviando sem que a pessoa entre no site.
--
-- ✏️ A SESSÃO ENTROU EM 10/11/2026, ANTES DE ESTA MIGRAÇÃO SER APLICADA EM
-- QUALQUER LUGAR (LGPD-09). A versão de 05/11 tinha três sinais e confiava no
-- `last_sign_in_at` para "a pessoa usou o serviço". Ele só muda num login: a
-- renovação de uma sessão aberta não o toca, e o app mantém a sessão aberta.
-- Medido na produção em 10/11: em 2 de 6 contas a sessão tinha sido renovada
-- até 1 dia e 16 h depois do último login. Com três sinais, quem usa o painel
-- todo dia sem nunca sair e sem dispositivo enviando seria apagado em 12 meses.
-- Corrigida aqui, e não numa migração nova, porque nunca foi aplicada: aplicar
-- uma versão sabidamente errada para consertá-la em seguida seria pior.
--
-- ✏️ POR QUE OS TRÊS CAMPOS DA SESSÃO (10/11): o código do Supabase Auth grava
-- explicitamente a `refreshed_at` na renovação (`Session.UpdateOnlyRefreshInfo`),
-- como `timestamp` SEM fuso, em UTC; e a produção mostrou a `updated_at` mudando
-- junto (2 de 2 sessões renovadas, consulta de 10/11). Ler os dois, mais a
-- criação, cobre uma mudança futura em qualquer um deles. O maior dos três vale.
--
-- AS PEÇAS
--
-- 1. `_eliminar_titular(uuid)`: os deletes que a `apagar_minha_conta()` da 006
--    fazia, extraídos para um lugar só. A `apagar_minha_conta()` passa a
--    chamá-la, com o mesmo recibo. Tabela nova com dado pessoal entra AQUI e
--    vale para os dois caminhos — antes seriam duas listas para manter iguais.
-- 2. `expurgar_contas_inativas()`: acha as contas inativas e chama a de cima
--    para cada uma. Devolve só contagens: nenhum identificador sai dela, nem
--    para log.
-- 3. O agendamento diário, se a extensão `pg_cron` estiver ligada.
--
-- POR QUE AS DUAS FUNÇÕES NOVAS SÃO `security invoker`
--
-- Rodam com o privilégio de QUEM CHAMA. Chamadas de dentro da
-- `apagar_minha_conta()` (`security definer`) ou pelo agendamento (que roda
-- como o dono do banco), têm o privilégio de que precisam. Chamadas por
-- qualquer outro papel, não teriam — e além disso o EXECUTE é revogado de
-- todos. Duas barreiras, e nenhuma função nova que eleve privilégio.
--
-- POR QUE O PRAZO NÃO É PARÂMETRO
--
-- Pelo mesmo motivo da `apagar_minha_conta()` não ter parâmetro de usuário: um
-- `expurgar_contas_inativas(1)` digitado por engano no SQL Editor apagaria
-- quem não entra há um mês. O prazo é o da política, e mudá-lo é migração.
--
-- APLICAR (passo do autor, como nas anteriores)
--
-- 1. Ligar a extensão `pg_cron` no painel do Supabase (Database → Extensions),
--    se ainda não estiver. Sem ela, esta migração cria as funções e AVISA que
--    não agendou; nada falha.
-- 2. Rodar este arquivo no SQL Editor.
-- 3. Rodar `DIAGNOSTICO-migracoes-aplicadas.sql`.
-- Idempotente: pode rodar duas vezes. Não muda backend nem frontend.
-- =====================================================================

begin;

-- ---------------------------------------------------------------------
-- 1. Os deletes do titular, num lugar só
-- ---------------------------------------------------------------------
create or replace function public._eliminar_titular(p_titular uuid)
returns jsonb
language plpgsql
volatile
security invoker
set search_path = ''
as $$
declare
    v_leituras  bigint;
    v_devices   bigint;
    v_perfis    bigint;
    v_conta     boolean := false;
begin
    if p_titular is null then
        return null;
    end if;

    delete from public.sleep_data where user_id = p_titular;
    get diagnostics v_leituras = row_count;

    -- `device_tokens` sai junto, por `on delete cascade` (007).
    delete from public.devices where user_id = p_titular;
    get diagnostics v_devices = row_count;

    delete from public.profiles where id = p_titular;
    get diagnostics v_perfis = row_count;

    begin
        delete from auth.users where id = p_titular;
        v_conta := found;
    exception when insufficient_privilege or undefined_table then
        v_conta := false;
    end;

    return jsonb_build_object(
        'leituras_apagadas',          v_leituras,
        'dispositivos_apagados',      v_devices,
        'perfil_apagado',             v_perfis > 0,
        'conta_de_acesso_removida',   v_conta
    );
end;
$$;

comment on function public._eliminar_titular(uuid) is
    'LGPD-02. Os deletes de todo o dado pessoal de um titular. Uso INTERNO: '
    'chamada por apagar_minha_conta() e por expurgar_contas_inativas(). '
    'security invoker e sem EXECUTE para ninguem: chamada de fora nao roda.';

revoke all on function public._eliminar_titular(uuid) from public;
do $$
declare
    papel text;
begin
    foreach papel in array array['anon', 'authenticated', 'service_role', 'dormio_ingestao'] loop
        if exists (select 1 from pg_roles where rolname = papel) then
            execute format('revoke all on function public._eliminar_titular(uuid) from %I', papel);
        end if;
    end loop;
end $$;

-- ---------------------------------------------------------------------
-- 2. A exclusão pelo titular passa a usar a função de cima
--    `create or replace` preserva o ACL da 006/009 (EXECUTE para
--    `authenticated`, e só) — `test_rls_eliminacao.py` confere.
-- ---------------------------------------------------------------------
create or replace function public.apagar_minha_conta()
returns jsonb
language plpgsql
volatile
security definer
set search_path = ''
as $$
begin
    if auth.uid() is null then
        return null;
    end if;
    return public._eliminar_titular(auth.uid());
end;
$$;

-- ---------------------------------------------------------------------
-- 3. O expurgo por inatividade
-- ---------------------------------------------------------------------
create or replace function public.expurgar_contas_inativas()
returns jsonb
language plpgsql
volatile
security invoker
set search_path = ''
as $$
declare
    -- O prazo da seção 7 da política de privacidade. Mudar é migração.
    c_prazo     constant interval := interval '12 months';
    v_corte     timestamptz := now() - c_prazo;
    r           record;
    v_recibo    jsonb;
    v_contas    bigint := 0;
    v_leituras  bigint := 0;
    v_devices   bigint := 0;
    v_acessos   bigint := 0;
begin
    for r in
        select u.id
          from auth.users u
         where greatest(
                   u.created_at,
                   u.last_sign_in_at,
                   -- A sessão: criação, `updated_at` e `refreshed_at`. A
                   -- renovação grava a `refreshed_at` (e não a `updated_at`),
                   -- num `timestamp` SEM fuso, em UTC: o `extract(epoch ...)`
                   -- lê os dois tipos do mesmo jeito. Ver o cabeçalho.
                   (select max(greatest(se.created_at, se.updated_at,
                                        to_timestamp(extract(epoch from se.refreshed_at))))
                      from auth.sessions se
                     where se.user_id = u.id),
                   (select max(s.created_at)
                      from public.sleep_data s
                     where s.user_id = u.id)
               ) < v_corte
    loop
        v_recibo := public._eliminar_titular(r.id);
        v_contas   := v_contas + 1;
        v_leituras := v_leituras + (v_recibo ->> 'leituras_apagadas')::bigint;
        v_devices  := v_devices + (v_recibo ->> 'dispositivos_apagados')::bigint;
        if (v_recibo ->> 'conta_de_acesso_removida')::boolean then
            v_acessos := v_acessos + 1;
        end if;
    end loop;

    return jsonb_build_object(
        'prazo',                       c_prazo::text,
        'contas_expurgadas',           v_contas,
        'leituras_apagadas',           v_leituras,
        'dispositivos_apagados',       v_devices,
        'contas_de_acesso_removidas',  v_acessos
    );
end;
$$;

comment on function public.expurgar_contas_inativas() is
    'LGPD-02. Elimina por inteiro as contas sem criacao, login nem leitura nos '
    'ultimos 12 meses (secao 7 da politica de privacidade). Sem parametro de '
    'proposito. Devolve so contagens. Rodada pelo agendamento diario.';

revoke all on function public.expurgar_contas_inativas() from public;
do $$
declare
    papel text;
begin
    foreach papel in array array['anon', 'authenticated', 'service_role', 'dormio_ingestao'] loop
        if exists (select 1 from pg_roles where rolname = papel) then
            execute format('revoke all on function public.expurgar_contas_inativas() from %I', papel);
        end if;
    end loop;
end $$;

-- ---------------------------------------------------------------------
-- 4. O agendamento diário, se houver `pg_cron`
--    `cron.schedule` com nome substitui o job de mesmo nome: idempotente.
--    04:17 UTC — fora do horário de captação no Brasil.
-- ---------------------------------------------------------------------
do $$
begin
    if exists (select 1 from pg_extension where extname = 'pg_cron') then
        perform cron.schedule(
            'dormio-expurgo-por-inatividade',
            '17 4 * * *',
            'select public.expurgar_contas_inativas()'
        );
        raise notice 'LGPD-02: expurgo por inatividade agendado (diario, 04:17 UTC).';
    else
        raise notice
            'LGPD-02: a extensao pg_cron NAO esta ligada; as funcoes foram criadas, '
            'mas o expurgo NAO foi agendado. Ligue-a em Database -> Extensions e '
            'rode este arquivo de novo.';
    end if;
end $$;

commit;
