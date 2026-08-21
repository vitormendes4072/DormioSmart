-- =====================================================================
-- 001_multiusuario.sql — Fundação multiusuário (SEC-04)
--
-- Cria profiles e devices, associa sleep_data a um dono e substitui o
-- "RLS ligado sem políticas" (que só funcionava porque o backend usa
-- service_role) por políticas reais por dono.
--
-- Contrato de dados: docs/DATA-CONTRACT.md v1.0.0
-- Aplicar em: Supabase > SQL Editor. Idempotente.
-- =====================================================================

begin;

-- ---------------------------------------------------------------------
-- 1. profiles — dados de perfil do usuário
--    auth.users é gerenciada pelo Supabase e não deve ser alterada.
-- ---------------------------------------------------------------------
create table if not exists public.profiles (
    id          uuid primary key references auth.users(id) on delete cascade,
    nome        text,
    idade       integer check (idade is null or (idade >= 0 and idade < 150)),
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

comment on table public.profiles is
    'Perfil do usuário. 1:1 com auth.users. Criado automaticamente no signup.';

-- ---------------------------------------------------------------------
-- 2. devices — dispositivos físicos pareados a um usuário (SEC-02)
--    Guarda apenas o SHA-256 do token; o valor puro é exibido uma única
--    vez ao usuário no momento do pareamento e nunca mais recuperável.
-- ---------------------------------------------------------------------
create table if not exists public.devices (
    id            uuid primary key default gen_random_uuid(),
    user_id       uuid not null references auth.users(id) on delete cascade,
    nome          text not null default 'Dormio Smart',
    token_hash    text not null unique,
    revoked_at    timestamptz,
    last_seen_at  timestamptz,
    created_at    timestamptz not null default now()
);

comment on column public.devices.token_hash is
    'SHA-256 hex do token. NUNCA guardar o token em claro.';
comment on column public.devices.revoked_at is
    'Se preenchido, o token é rejeitado com 401. Revogação é soft delete.';

-- Resolução token -> device a cada POST /api/data: precisa ser indexada.
create index if not exists devices_token_hash_idx on public.devices (token_hash);
create index if not exists devices_user_id_idx    on public.devices (user_id);

-- ---------------------------------------------------------------------
-- 3. sleep_data — associar ao dono
--    Colunas anuláveis de propósito: as linhas já coletadas não têm dono.
--    O backfill é o item DATA-03.
-- ---------------------------------------------------------------------
alter table public.sleep_data
    add column if not exists user_id   uuid references auth.users(id)    on delete cascade,
    add column if not exists device_id uuid references public.devices(id) on delete set null;

-- O dashboard consulta sempre "do usuário X, mais recentes primeiro".
create index if not exists sleep_data_user_created_idx
    on public.sleep_data (user_id, created_at desc);

-- ---------------------------------------------------------------------
-- 4. Row Level Security
--    service_role ignora RLS por definição — o caminho de ingestão
--    (POST /api/data) continua funcionando sem política de insert.
--    As políticas abaixo protegem o caminho do usuário autenticado.
-- ---------------------------------------------------------------------
alter table public.profiles   enable row level security;
alter table public.devices    enable row level security;
alter table public.sleep_data enable row level security;

-- profiles: cada um enxerga e edita apenas o próprio
drop policy if exists profiles_select_own on public.profiles;
create policy profiles_select_own on public.profiles
    for select to authenticated using (id = (select auth.uid()));

drop policy if exists profiles_insert_own on public.profiles;
create policy profiles_insert_own on public.profiles
    for insert to authenticated with check (id = (select auth.uid()));

drop policy if exists profiles_update_own on public.profiles;
create policy profiles_update_own on public.profiles
    for update to authenticated
    using (id = (select auth.uid())) with check (id = (select auth.uid()));

-- devices: o usuário gerencia os próprios dispositivos
drop policy if exists devices_select_own on public.devices;
create policy devices_select_own on public.devices
    for select to authenticated using (user_id = (select auth.uid()));

drop policy if exists devices_insert_own on public.devices;
create policy devices_insert_own on public.devices
    for insert to authenticated with check (user_id = (select auth.uid()));

drop policy if exists devices_update_own on public.devices;
create policy devices_update_own on public.devices
    for update to authenticated
    using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));

drop policy if exists devices_delete_own on public.devices;
create policy devices_delete_own on public.devices
    for delete to authenticated using (user_id = (select auth.uid()));

-- sleep_data: leitura apenas do próprio dado.
-- SEM política de insert/update/delete para 'authenticated': a escrita é
-- exclusiva do device via service_role. Cliente não fabrica leitura de sensor.
drop policy if exists sleep_data_select_own on public.sleep_data;
create policy sleep_data_select_own on public.sleep_data
    for select to authenticated using (user_id = (select auth.uid()));

-- ---------------------------------------------------------------------
-- 5. Criação automática do profile no signup
-- ---------------------------------------------------------------------
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
    insert into public.profiles (id, nome)
    values (new.id, new.raw_user_meta_data ->> 'nome')
    on conflict (id) do nothing;
    return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
    after insert on auth.users
    for each row execute function public.handle_new_user();

commit;

-- =====================================================================
-- VERIFICAÇÃO (rodar após aplicar; nenhuma deve retornar linha indevida)
--
--   select tablename, rowsecurity from pg_tables
--    where schemaname = 'public'
--      and tablename in ('profiles','devices','sleep_data');
--   -- esperado: rowsecurity = true nas três
--
--   select tablename, policyname, cmd from pg_policies
--    where schemaname = 'public' order by tablename, policyname;
--   -- esperado: 3 em profiles, 4 em devices, 1 em sleep_data
-- =====================================================================
