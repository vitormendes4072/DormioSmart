-- =====================================================================
-- DIAGNÓSTICO — usuário criado mas `profiles` vazio
--
-- Sintoma: o cadastro funciona, o usuário entra no app, mas nenhuma linha
-- aparece em public.profiles.
--
-- Raciocínio: a migração 001 cria um gatilho em auth.users que insere o
-- perfil. Se ele tivesse executado e FALHADO, o cadastro teria devolvido
-- erro ("Database error saving new user") — o usuário não teria entrado.
-- Como entrou, a suspeita principal é que o gatilho não existe.
--
-- Rode os quatro blocos abaixo no SQL Editor e me diga o resultado.
-- =====================================================================

-- 1. O usuário realmente existe?
select id, email, created_at, email_confirmed_at
from auth.users
order by created_at desc
limit 5;

-- 2. A FUNÇÃO existe?
--    Esperado: 1 linha, com prosecdef = true (SECURITY DEFINER).
select p.proname,
       p.prosecdef as security_definer,
       pg_get_userbyid(p.proowner) as dono
from pg_proc p
join pg_namespace n on n.oid = p.pronamespace
where n.nspname = 'public'
  and p.proname = 'handle_new_user';

-- 3. O GATILHO existe em auth.users?
--    Esperado: 1 linha chamada on_auth_user_created.
--    ZERO LINHAS AQUI = causa confirmada.
select t.tgname,
       t.tgenabled as habilitado,
       c.relname as tabela
from pg_trigger t
join pg_class c on c.oid = t.tgrelid
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'auth'
  and c.relname = 'users'
  and not t.tgisinternal;

-- 4. As políticas RLS ficaram como esperado?
--    Esperado: 3 em profiles, 4 em devices, 1 em sleep_data.
select tablename, count(*) as politicas
from pg_policies
where schemaname = 'public'
  and tablename in ('profiles', 'devices', 'sleep_data')
group by tablename
order by tablename;


-- =====================================================================
-- REPARO — só rode se o bloco 3 voltar VAZIO
--
-- Recria função e gatilho de forma isolada (fora da transação grande do
-- 001, que é onde a aplicação pode ter sido interrompida).
-- =====================================================================
--
-- create or replace function public.handle_new_user()
-- returns trigger
-- language plpgsql
-- security definer
-- set search_path = ''
-- as $$
-- begin
--     insert into public.profiles (id, nome)
--     values (new.id, new.raw_user_meta_data ->> 'nome')
--     on conflict (id) do nothing;
--     return new;
-- end;
-- $$;
--
-- drop trigger if exists on_auth_user_created on auth.users;
-- create trigger on_auth_user_created
--     after insert on auth.users
--     for each row execute function public.handle_new_user();
--
-- -- Cria os perfis dos usuários que já existiam antes do reparo:
-- insert into public.profiles (id, nome)
-- select u.id, u.raw_user_meta_data ->> 'nome'
-- from auth.users u
-- left join public.profiles p on p.id = u.id
-- where p.id is null;
--
-- -- Confirmação: deve devolver o mesmo número das duas vezes.
-- select (select count(*) from auth.users) as usuarios,
--        (select count(*) from public.profiles) as perfis;
