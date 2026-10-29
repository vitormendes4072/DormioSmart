-- =====================================================================
-- grants_pos_migracao.sql — GRANTs do Supabase nas tabelas criadas pela 001
--
-- No Supabase, `anon` e `authenticated` recebem privilégio de tabela em
-- `public` automaticamente (default privileges do papel `postgres`). Aqui isso
-- é explícito e roda DEPOIS das migrações, porque GRANT não alcança tabela que
-- ainda não existe.
--
-- ISTO NÃO É CONVENIÊNCIA DE TESTE, É FIDELIDADE. Se o teste rodasse sem
-- GRANT, todo acesso indevido seria bloqueado por falta de permissão e a
-- suíte passaria sem nunca exercitar uma policy — o falso-positivo que esta
-- suíte existe para não cometer. Com o GRANT no lugar, a única coisa entre o
-- usuário A e o dado do usuário B é o RLS. Que é a afirmação sob teste.
-- =====================================================================

grant select, insert, update, delete on public.profiles   to anon, authenticated, service_role;
grant select, insert, update, delete on public.devices    to anon, authenticated, service_role;
grant select, insert, update, delete on public.sleep_data to anon, authenticated, service_role;

grant usage, select on all sequences in schema public to anon, authenticated, service_role;

-- `device_tokens` (SEC-08) NAO recebe GRANT, e a ausencia e a protecao: sem
-- privilegio, o PostgREST nao expoe a tabela como endpoint. Este comentario
-- existe para que ninguem acrescente a linha "por simetria" com as de cima.
-- Ver tests/rls/test_rls_credencial.py.
