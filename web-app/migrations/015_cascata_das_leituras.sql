-- =====================================================================
-- 015_cascata_das_leituras.sql — DATA-12
--
-- O DEFEITO
--
-- A 001 declara `sleep_data.user_id ... references auth.users(id) on delete
-- cascade`, mas por `add column if not exists`. Na produção a coluna já
-- existia, criada pelo painel do Supabase antes das migrações (com padrão
-- `auth.uid()` e chave estrangeira SEM cascata), e o comando foi pulado em
-- silêncio. Conferido em 09/11 por `CONSULTA-estrutura-do-esquema.sql`:
-- na produção, `FOREIGN KEY (user_id) REFERENCES auth.users(id)`, sem
-- `ON DELETE CASCADE`.
--
-- O QUE ISSO QUEBRA
--
-- `apagar_minha_conta()` e `_eliminar_titular()` apagam as leituras antes do
-- usuário, então a eliminação pelo app funciona. O que quebra é apagar o
-- usuário DIRETO em `auth.users` — o que o painel do Supabase faz em
-- Authentication → Delete user: com leituras, a exclusão é recusada por
-- violação de chave estrangeira.
--
-- POR QUE OS TESTES NÃO PEGAVAM
--
-- `tests/rls/esquema_base.sql` criava `sleep_data` sem `user_id`, e a 001
-- criava a coluna COM a cascata. O teste tinha a cascata; a produção, não.
-- Desde o DATA-12 o esquema de teste nasce como a produção, e
-- `test_rls_cascata.py` falha sem esta migração.
--
-- O QUE ESTA MIGRAÇÃO FAZ
--
-- Troca a chave estrangeira por uma com `on delete cascade`, que é o que a
-- 001 declara. Não mexe em dado. A recriação valida as linhas existentes
-- (todas já válidas, porque a chave antiga valia) e segura a tabela por
-- esse tempo. Idempotente.
--
-- Fora de escopo, de propósito: o padrão `auth.uid()` de `user_id` e o
-- `created_at` anulável, também herdados do painel. As funções de gravação
-- sempre passam o dono e nunca gravam `created_at`; mudá-los não muda
-- comportamento, e o `not null` exigiria conferir nulos antes.
--
-- Conferir depois: `DIAGNOSTICO-migracoes-aplicadas.sql`, linha da 015.
-- =====================================================================

begin;

alter table public.sleep_data
    drop constraint if exists sleep_data_user_id_fkey;

alter table public.sleep_data
    add constraint sleep_data_user_id_fkey
    foreign key (user_id) references auth.users(id) on delete cascade;

commit;
