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
--  4. `sleep_data` é criada aqui no estado PRÉ-001 (sem `user_id`, sem
--     `device_id`, com RLS ligado e sem nenhuma policy), porque é assim que
--     a 001 a encontra. Colunas conforme docs/DATA-CONTRACT.md §4.
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
end $$;

-- ---------------------------------------------------------------------
-- 2. Schema auth e auth.users
-- ---------------------------------------------------------------------
create schema if not exists auth;

create table if not exists auth.users (
    id                   uuid primary key default gen_random_uuid(),
    email                text unique,
    raw_user_meta_data   jsonb not null default '{}'::jsonb,
    created_at           timestamptz not null default now()
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
    id               bigserial primary key,
    accel_x          double precision,
    accel_y          double precision,
    accel_z          double precision,
    gyro_x           double precision,
    gyro_y           double precision,
    gyro_z           double precision,
    temp             double precision,
    movimento_total  double precision,
    status           text,
    created_at       timestamptz not null default now()
);

alter table public.sleep_data enable row level security;

-- ---------------------------------------------------------------------
-- 5. GRANTs do Supabase
--    Aplicados ANTES das migrações; o bloco equivalente para as tabelas
--    criadas pela 001 está em `grants_pos_migracao.sql`, porque GRANT não
--    alcança tabela que ainda não existe.
-- ---------------------------------------------------------------------
grant usage on schema public to anon, authenticated, service_role;
grant usage on schema auth   to anon, authenticated, service_role;

grant select, insert, update, delete on public.sleep_data to anon, authenticated, service_role;
grant usage, select on all sequences in schema public to anon, authenticated, service_role;
