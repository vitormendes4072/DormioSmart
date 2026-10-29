-- =====================================================================
-- 009_privilegios_padrao_do_supabase.sql — SEC-12
-- =====================================================================
-- O QUE ESTAVA ERRADO (medido na produção em 2026-10-28)
--
-- No Supabase, todo objeto que o `postgres` cria em `public` nasce com
-- privilégio NOMINAL para `anon` e `authenticated` (pg_default_acl: ALL em
-- tabela, EXECUTE em função). As migrações 005–008 faziam
-- `revoke all on function ... from public` — que NÃO alcança um grant nominal.
-- Resultado: `anon` (a chave pública, que está no bundle do frontend)
-- executava as sete funções, inclusive as de ingestão, ao contrário do que a
-- 005 afirma. Medido localmente, nenhuma chamada de `anon` produzia efeito
-- (guardas de `auth.uid()`, hash impossível de adivinhar) — mas a camada de
-- proteção declarada não existia.
--
-- Esta migração revoga NOMINALMENTE, devolve só o que cada papel deve ter, e
-- muda o padrão para que função nova não nasça executável por `anon`.
-- Pode rodar antes ou depois da 007; idempotente.
-- =====================================================================

begin;

-- 1. Funções: ninguém de fora executa nada por padrão.
do $$
declare
    f text;
begin
    foreach f in array array[
        'public.sanidade()',
        'public.resolver_dispositivo(text)',
        'public.registrar_leitura(text,jsonb)',
        'public.registrar_leitura_da_sessao(uuid,jsonb)',
        'public.apagar_minha_conta()',
        'public.parear_dispositivo(text,text,text)',
        'public.handle_new_user()',
        'public.tocar_updated_at()'
    ] loop
        if to_regprocedure(f) is not null then
            execute format('revoke execute on function %s from anon, authenticated', f);
        end if;
    end loop;
end $$;

-- 2. O que `authenticated` deve executar: só o caminho do próprio usuário.
do $$
declare
    f text;
begin
    foreach f in array array[
        'public.sanidade()',
        'public.registrar_leitura_da_sessao(uuid,jsonb)',
        'public.apagar_minha_conta()',
        'public.parear_dispositivo(text,text,text)'
    ] loop
        if to_regprocedure(f) is not null then
            execute format('grant execute on function %s to authenticated', f);
        end if;
    end loop;
end $$;

-- 3. A tabela da credencial (007), se já existir: nenhum privilégio de cliente.
do $$
begin
    if to_regclass('public.device_tokens') is not null then
        revoke all on public.device_tokens from anon, authenticated;
    end if;
end $$;

-- 4. Função nova deixa de nascer executável por `anon` e `authenticated`.
--    Tabelas ficam com o padrão do Supabase (o RLS é a proteção delas).
alter default privileges in schema public
    revoke execute on functions from anon, authenticated;

commit;

-- VERIFICAÇÃO (esperado: anon = false em todas; authenticated = true só em
-- sanidade, registrar_leitura_da_sessao, apagar_minha_conta, parear_dispositivo)
--
-- select p.proname,
--        has_function_privilege('anon', p.oid, 'execute') as anon,
--        has_function_privilege('authenticated', p.oid, 'execute') as authenticated
--   from pg_proc p join pg_namespace n on n.oid = p.pronamespace
--  where n.nspname = 'public' order by 1;
