-- =====================================================================
-- DIAGNÓSTICO: quais migrações estão aplicadas neste banco
-- =====================================================================
-- Só LÊ: catálogo do Postgres e contagens. Não altera nada — pode rodar no
-- SQL Editor do Supabase de produção sem risco.
--
-- Como usar: SQL Editor → colar tudo → Run. Uma linha por migração:
--   aplicada  = true  → todas as marcas que ela deixa estão no banco
--   aplicada  = false → falta pelo menos uma; `faltando` diz qual
--   aplicada  = null  → migração de DADOS, sem marca de esquema; ler `detalhe`
--
-- Por que por marca e não por tabela de controle: as migrações deste projeto
-- são aplicadas à mão no SQL Editor, e nada registra quais rodaram. A única
-- prova é o que cada uma deixou no banco.
--
-- Validado em Postgres local, aplicando 001→008 uma a uma: a cada passo, só
-- as aplicadas até ali saem `true` (ver o diário de 2026-10-28).
-- =====================================================================

with
col as (
    select table_name || '.' || column_name as nome, column_default
    from information_schema.columns where table_schema = 'public'
),
fn as (select p.proname as nome from pg_proc p
       join pg_namespace n on n.oid = p.pronamespace where n.nspname = 'public'),
pol as (select tablename || '.' || policyname as nome from pg_policies
        where schemaname = 'public'),
marcas (migracao, item, marca, presente) as (values
    -- 001: perfis, dispositivos, dono das leituras, RLS, gatilho de perfil
    ('001', 'SEC-04',   'tabela profiles',                 to_regclass('public.profiles') is not null),
    ('001', 'SEC-04',   'tabela devices',                  to_regclass('public.devices') is not null),
    ('001', 'SEC-04',   'coluna sleep_data.user_id',       exists (select 1 from col where nome = 'sleep_data.user_id')),
    ('001', 'SEC-04',   'RLS ligado em sleep_data',        coalesce((select relrowsecurity from pg_class where oid = to_regclass('public.sleep_data')), false)),
    ('001', 'SEC-04',   'policy sleep_data_select_own',    exists (select 1 from pol where nome = 'sleep_data.sleep_data_select_own')),
    ('001', 'SEC-04',   'gatilho on_auth_user_created',    exists (select 1 from pg_trigger where tgname = 'on_auth_user_created')),
    -- 003: nome padrão do dispositivo
    ('003', '—',        'default de devices.nome = Smart Dormio',
                                                           exists (select 1 from col where nome = 'devices.nome' and column_default like '%Smart Dormio%')),
    -- 004: tipo do dispositivo e campos de agregação
    ('004', 'DATA-05',  'coluna devices.tipo',             exists (select 1 from col where nome = 'devices.tipo')),
    ('004', 'DATA-05',  'restrição devices_tipo_valido',   exists (select 1 from pg_constraint where conname = 'devices_tipo_valido')),
    ('004', 'DATA-05',  'coluna sleep_data.captured_at',   exists (select 1 from col where nome = 'sleep_data.captured_at')),
    ('004', 'DATA-05',  'coluna sleep_data.epoca_segundos',exists (select 1 from col where nome = 'sleep_data.epoca_segundos')),
    ('004', 'DATA-05',  'índice sleep_data_device_created_idx',
                                                           to_regclass('public.sleep_data_device_created_idx') is not null),
    -- 005: papel de ingestão mínimo e as funções que ele executa
    ('005', 'SEC-06',   'papel dormio_ingestao',           exists (select 1 from pg_roles where rolname = 'dormio_ingestao')),
    ('005', 'SEC-06',   'função sanidade',                 exists (select 1 from fn where nome = 'sanidade')),
    ('005', 'SEC-06',   'função registrar_leitura',        exists (select 1 from fn where nome = 'registrar_leitura')),
    ('005', 'SEC-06',   'função registrar_leitura_da_sessao',
                                                           exists (select 1 from fn where nome = 'registrar_leitura_da_sessao')),
    ('005', 'SEC-06',   'função resolver_dispositivo',     exists (select 1 from fn where nome = 'resolver_dispositivo')),
    -- 006: direito de eliminação
    ('006', 'SEC-07',   'policy sleep_data_delete_own',    exists (select 1 from pol where nome = 'sleep_data.sleep_data_delete_own')),
    ('006', 'SEC-07',   'policy profiles_delete_own',      exists (select 1 from pol where nome = 'profiles.profiles_delete_own')),
    ('006', 'SEC-07',   'função apagar_minha_conta',       exists (select 1 from fn where nome = 'apagar_minha_conta')),
    -- 007: credencial fora da tabela exposta
    ('007', 'SEC-08',   'tabela device_tokens',            to_regclass('public.device_tokens') is not null),
    ('007', 'SEC-08',   'função parear_dispositivo',       exists (select 1 from fn where nome = 'parear_dispositivo')),
    ('007', 'SEC-08',   'coluna devices.token_hash REMOVIDA',
                                                           not exists (select 1 from col where nome = 'devices.token_hash')),
    ('007', 'SEC-08',   'policy devices_insert_own REMOVIDA',
                                                           not exists (select 1 from pol where nome = 'devices.devices_insert_own')),
    -- 008: profiles como fonte de verdade
    ('008', 'PERFIL-01','função tocar_updated_at',         exists (select 1 from fn where nome = 'tocar_updated_at')),
    ('008', 'PERFIL-01','gatilho profiles_tocar_updated_at',
                                                           exists (select 1 from pg_trigger where tgname = 'profiles_tocar_updated_at')),
    ('008', 'PERFIL-01','restrição profiles_nome_tamanho', exists (select 1 from pg_constraint where conname = 'profiles_nome_tamanho')),
    -- 009: o que os privilégios padrão do Supabase davam a anon/authenticated.
    -- `to_regprocedure` devolve nulo se a função não existe; aí a marca é false.
    ('009', 'SEC-12',   'anon não executa registrar_leitura',
        coalesce(not has_function_privilege('anon', to_regprocedure('public.registrar_leitura(text,jsonb)'), 'execute'), false)),
    ('009', 'SEC-12',   'anon não executa apagar_minha_conta',
        coalesce(not has_function_privilege('anon', to_regprocedure('public.apagar_minha_conta()'), 'execute'), false)),
    ('009', 'SEC-12',   'authenticated não executa resolver_dispositivo',
        coalesce(not has_function_privilege('authenticated', to_regprocedure('public.resolver_dispositivo(text)'), 'execute'), false)),
    ('009', 'SEC-12',   'função nova não nasce executável por anon',
        not exists (select 1 from pg_default_acl
                     where defaclnamespace = 'public'::regnamespace and defaclobjtype = 'f'
                       and pg_get_userbyid(defaclrole) = 'postgres'
                       and defaclacl::text like '%anon=%')),
    -- 010: o vetor de características (DATA-07b). As FUNÇÕES são conferidas, e
    -- não só as colunas: coluna criada com função antiga é o caso perigoso —
    -- o backend valida `f`, a função o ignora, e a resposta é 201. A marca é a
    -- EXTRAÇÃO (`->> 'fs_features'`), não a menção: uma função que listasse a
    -- coluna e gravasse nulo passaria por `like '%fs_features%'`.
    ('010', 'DATA-07b', 'coluna sleep_data.fs_features',   exists (select 1 from col where nome = 'sleep_data.fs_features')),
    ('010', 'DATA-07b', 'restrição sleep_data_features_tudo_ou_nada',
                                                           exists (select 1 from pg_constraint where conname = 'sleep_data_features_tudo_ou_nada')),
    ('010', 'DATA-07b', 'registrar_leitura extrai o vetor',
        coalesce((select pg_get_functiondef(to_regprocedure('public.registrar_leitura(text,jsonb)')) like '%->> ''fs_features''%'), false)),
    ('010', 'DATA-07b', 'registrar_leitura_da_sessao extrai o vetor',
        coalesce((select pg_get_functiondef(to_regprocedure('public.registrar_leitura_da_sessao(uuid,jsonb)')) like '%->> ''fs_features''%'), false))
),
esquema as (
    select migracao, min(item) as item,
           bool_and(presente) as aplicada,
           count(*) filter (where presente) || ' de ' || count(*) || ' marcas' as detalhe,
           string_agg(marca, '; ') filter (where not presente) as faltando
    from marcas group by migracao
),
dados as (
    -- 002 só mexe em dados: associa as leituras sem dono a uma conta. Não tem
    -- marca de esquema; o que se mede é quantas leituras continuam sem dono.
    select '002'::text as migracao, 'DATA-03'::text as item, null::boolean as aplicada,
           case when to_regclass('public.sleep_data') is null
                     or not exists (select 1 from col where nome = 'sleep_data.user_id')
                then 'sem sleep_data.user_id: aplique a 001 antes'
                -- Contagem montada em tempo de execução: citar `user_id` direto
                -- faria a consulta inteira falhar num banco sem a 001, porque o
                -- Postgres resolve as colunas antes de avaliar o CASE.
                else (xpath('/row/c/text()', query_to_xml(
                          'select count(*) as c from public.sleep_data where user_id is null',
                          false, true, '')))[1]::text
                     || ' leitura(s) sem dono — 0 significa backfill feito ou desnecessário'
           end as detalhe,
           null::text as faltando
)
select migracao, item, aplicada, detalhe, faltando from esquema
union all
select migracao, item, aplicada, detalhe, faltando from dados
order by migracao;
