-- =====================================================================
-- esquema_base.sql — o Supabase que as migrações assumem existir
--
-- SEC-05 / INFRA-01.
--
-- POR QUE ESTE ARQUIVO EXISTE
--
-- As migrações de `web-app/migrations/` são escritas para o Supabase e
-- dependem de coisas que o Postgres puro não tem: o schema `auth`, a tabela
-- `auth.users`, a função `auth.uid()`, os papéis `anon` / `authenticated` /
-- `service_role` e os GRANTs que o Supabase aplica em `public` por padrão.
-- Sem esses primitivos, as migrações nem rodam — e é por isso que o RLS nunca
-- teve teste: não havia onde aplicá-lo fora da instância real.
--
-- Este script recria apenas esses primitivos, com a MESMA semântica do
-- Supabase, para que as migrações reais (001, 003, 004) sejam aplicadas sem
-- nenhuma adaptação. As policies testadas são as do repositório, não cópias.
--
-- O QUE É FIEL AO SUPABASE, E POR QUE IMPORTA
--
--  1. `auth.uid()` lê a claim `sub` do JWT via GUC `request.jwt.claims`.
--     É exatamente o que o PostgREST preenche a cada requisição. Logo,
--     `set local role authenticated` + `set local request.jwt.claims` reproduz
--     fielmente uma chamada autenticada — inclusive a que o NAVEGADOR faz
--     direto no PostgREST com a chave anon, que é pública por design.
--
--  2. `service_role` tem BYPASSRLS, como no Supabase. É o papel do backend na
--     ingestão: o RLS é ignorado ali de propósito (SEC-02), e o teste precisa
--     poder demonstrar essa diferença em vez de supô-la.
--
--  3. Os GRANTs amplos para `anon` e `authenticated` são reproduzidos de
--     propósito. No Supabase, esses papéis TÊM privilégio de tabela em
--     `public`; o que impede o acesso é o RLS, não a falta de GRANT. Sem
--     reproduzir o GRANT, o teste passaria por falta de permissão e não
--     provaria nada sobre RLS — o falso-positivo clássico desse tipo de suíte.
--
--  4. `sleep_data` é criada aqui no estado em que a 001 a encontrou NA
--     PRODUÇÃO, e não no que a 001 supõe: com RLS ligado, sem policy, sem
--     `device_id` — e JÁ COM `user_id` (padrão `auth.uid()`, chave estrangeira
--     SEM cascata), `created_at` anulável e dois índices antigos, todos
--     criados pelo painel do Supabase antes das migrações. Como a coluna já
--     existe, o `add column if not exists user_id ... on delete cascade` da
--     001 é pulado, como foi na produção. Conferido contra a produção em
--     09/11 (`DATA-12`, `migrations/CONSULTA-estrutura-do-esquema.sql`): até
--     ali este arquivo criava o id como `bigserial` (`DATA-10`) e sem
--     `user_id`, e a suíte testava uma cascata que a produção não tinha.
--     Colunas conforme docs/DATA-CONTRACT.md §4.
--
-- O QUE NÃO É REPRODUZIDO
--
--  · O GoTrue (signup, e-mail, refresh). `auth.users` aqui é só a tabela, e
--    as contas de teste são inseridas direto. O que está sob teste é o RLS,
--    e para o RLS um usuário é um UUID na claim `sub` — nada mais.
--  · O PostgREST. Os testes falam SQL sob o papel `authenticated`, que é a
--    mesma superfície que o PostgREST alcança. Ver README.md desta pasta.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. Papéis
--    NOLOGIN: ninguém se conecta como eles, o acesso é via SET ROLE — que é
--    também como o PostgREST faz.
-- ---------------------------------------------------------------------
do $$
begin
    if not exists (select 1 from pg_roles where rolname = 'anon') then
        create role anon nologin noinherit;
    end if;
    if not exists (select 1 from pg_roles where rolname = 'authenticated') then
        create role authenticated nologin noinherit;
    end if;
    if not exists (select 1 from pg_roles where rolname = 'service_role') then
        -- BYPASSRLS é o ponto: é o que faz o caminho de ingestão funcionar
        -- sem policy de insert em sleep_data.
        create role service_role nologin noinherit bypassrls;
    end if;
    -- `authenticator` é o papel com que o PostgREST conecta; ele faz SET ROLE
    -- para o papel da claim `role` do JWT. Existe aqui para que a 005 possa
    -- conceder `dormio_ingestao` a ele sem ramificar entre teste e produção.
    if not exists (select 1 from pg_roles where rolname = 'authenticator') then
        create role authenticator nologin noinherit;
    end if;
end $$;

grant anon, authenticated, service_role to authenticator;

-- ---------------------------------------------------------------------
-- 1b. Os privilégios PADRÃO do Supabase (SEC-12, 28/10)
--
--     No Supabase, todo objeto que o `postgres` cria em `public` nasce com
--     privilégio para `anon` e `authenticated`: ALL em tabela, EXECUTE em
--     função, uso em sequência. Medido na produção em 2026-10-28
--     (`pg_default_acl`, dono `postgres`, tipos r, f e S).
--
--     Até 28/10 esta base NÃO reproduzia isso, e três testes passavam no vazio:
--     `test_anon_nao_executa_funcao_de_ingestao`,
--     `test_authenticated_nao_executa_o_caminho_por_token` e
--     `test_nem_anon_nem_authenticated_tem_privilegio_na_tabela`. As migrações
--     faziam `revoke ... from public`, que não alcança um GRANT nominal a
--     `anon` — e no banco de teste não havia grant nominal nenhum para revogar.
--     Na produção havia, e `anon` executava as funções de ingestão.
--
--     Toda tabela que uma migração cria herda estes padrões, como no
--     Supabase — inclusive as da 001. ✏️ SEC-13 (13/11): até ali um
--     `grants_pos_migracao.sql` reaplicava os GRANTs DEPOIS das migrações e
--     desfazia o `revoke` de qualquer uma; hoje o arquivo que roda no fim
--     (`pos_migracao.sql`) não concede nada.
-- ---------------------------------------------------------------------
alter default privileges in schema public
    grant all on tables to anon, authenticated, service_role;
alter default privileges in schema public
    grant execute on functions to anon, authenticated, service_role;
alter default privileges in schema public
    grant usage, select, update on sequences to anon, authenticated, service_role;

-- ---------------------------------------------------------------------
-- 2. Schema auth e auth.users
-- ---------------------------------------------------------------------
create schema if not exists auth;

create table if not exists auth.users (
    id                   uuid primary key default gen_random_uuid(),
    email                text unique,
    raw_user_meta_data   jsonb not null default '{}'::jsonb,
    created_at           timestamptz not null default now(),
    -- LGPD-02 (05/11): a do Supabase tem; o expurgo por inatividade a le.
    last_sign_in_at      timestamptz
);

-- LGPD-09 (10/11): as sessões do Supabase Auth. O expurgo por inatividade lê
-- a criação, a `updated_at` e a `refreshed_at` (a que a renovação grava): o
-- `last_sign_in_at` só muda num login, e o app mantém a sessão aberta (medido na produção em 10/11:
-- em 2 de 6 contas a sessão foi renovada até 1 dia e 16 h depois do último
-- login). Só as colunas que o projeto usa; a tabela do Supabase tem mais.
create table if not exists auth.sessions (
    id          uuid primary key default gen_random_uuid(),
    user_id     uuid not null references auth.users(id) on delete cascade,
    created_at  timestamptz default now(),
    updated_at  timestamptz default now(),
    -- Como no Supabase: SEM fuso, em UTC. É a que a renovação grava.
    refreshed_at timestamp
);

-- ---------------------------------------------------------------------
-- 3. auth.uid()
--    Cópia da definição do Supabase. As duas formas de GUC são aceitas
--    porque as duas existem em produção, dependendo da versão do PostgREST.
--    `stable`, não `immutable`: o valor muda entre requisições.
-- ---------------------------------------------------------------------
create or replace function auth.uid()
returns uuid
language sql
stable
as $$
    select coalesce(
        nullif(current_setting('request.jwt.claim.sub', true), ''),
        (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub')
    )::uuid
$$;

create or replace function auth.role()
returns text
language sql
stable
as $$
    select coalesce(
        nullif(current_setting('request.jwt.claim.role', true), ''),
        (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'role')
    )::text
$$;

-- ---------------------------------------------------------------------
-- 4. sleep_data no estado PRÉ-001
--    RLS ligado e sem policy nenhuma: o estado que a 001 descreve como
--    "só funcionava porque o backend usa service_role".
-- ---------------------------------------------------------------------
create table if not exists public.sleep_data (
    id               uuid primary key default gen_random_uuid(),
    accel_x          double precision,
    accel_y          double precision,
    accel_z          double precision,
    gyro_x           double precision,
    gyro_y           double precision,
    gyro_z           double precision,
    temp             double precision,
    movimento_total  double precision,
    status           text,
    created_at       timestamptz default now(),
    -- Do painel, como na produção: padrão auth.uid() e sem `on delete cascade`.
    user_id          uuid default auth.uid() references auth.users(id)
);
create index if not exists idx_sleep_data_created_at on public.sleep_data (created_at desc);
create index if not exists idx_sleep_data_user       on public.sleep_data (user_id);

alter table public.sleep_data enable row level security;

-- ---------------------------------------------------------------------
-- 5. GRANTs do Supabase
--    Aplicados ANTES das migrações, para o que já existe aqui (`sleep_data`
--    pré-001). As tabelas que as migrações criam recebem o GRANT pelos
--    privilégios padrão da seção anterior, e não por GRANT posterior (SEC-13).
-- ---------------------------------------------------------------------
grant usage on schema public to anon, authenticated, service_role;
grant usage on schema auth   to anon, authenticated, service_role;

grant select, insert, update, delete on public.sleep_data to anon, authenticated, service_role;
grant usage, select on all sequences in schema public to anon, authenticated, service_role;
