-- =====================================================================
-- 003_padroniza_nome_do_dispositivo.sql
--
-- O nome padrão de dispositivo nasceu como 'Dormio Smart'. O padrão oficial
-- do produto é **'Smart Dormio'** (com espaço, nessa ordem) — é o que está na
-- capa e no título do trabalho.
--
-- POR QUE UMA MIGRAÇÃO NOVA, E NÃO UMA EDIÇÃO NA 001:
-- a 001 já foi aplicada no banco. Editá-la faria o arquivo deixar de descrever
-- o que de fato existe lá — que é exatamente o problema que migrações versionadas
-- existem para evitar. Migração aplicada é imutável; correção vira arquivo novo.
--
-- Idempotente: pode rodar mais de uma vez sem efeito adicional.
-- =====================================================================

begin;

-- 1. Novo padrão para dispositivos criados daqui em diante
alter table public.devices
    alter column nome set default 'Smart Dormio';

-- 2. Dispositivos que ficaram com o nome antigo E nunca foram renomeados
--    pelo usuário. Quem deu um nome próprio não é afetado.
update public.devices
set nome = 'Smart Dormio'
where nome = 'Dormio Smart';

commit;

-- VERIFICAÇÃO — nenhuma linha deve sobrar com o nome antigo:
--   select count(*) as antigos from public.devices where nome = 'Dormio Smart';
--   select column_default from information_schema.columns
--    where table_name = 'devices' and column_name = 'nome';
