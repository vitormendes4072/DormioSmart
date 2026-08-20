-- =====================================================================
-- 002_backfill_dono_dos_dados.sql — DATA-03
--
-- As leituras coletadas ANTES da migração 001 não têm `user_id`. Com o RLS
-- por dono ativo, elas ficam invisíveis para qualquer usuário autenticado —
-- e o dashboard nasce vazio depois do AUTH-03.
--
-- Este script associa essas linhas órfãs a uma conta existente.
--
-- ⚠️ NÃO É IDEMPOTENTE POR NATUREZA: ele atribui posse de dado. Só afeta
--    linhas com `user_id IS NULL`, então reexecutar não rouba linha de
--    ninguém — mas confira o e-mail antes de rodar.
--
-- ⚠️ PRÉ-REQUISITOS:
--    1. `001_multiusuario.sql` aplicado
--    2. Uma conta já criada (Supabase > Authentication > Users, ou pelo
--       cadastro do app depois do AUTH-02)
--
-- ⚠️ ORDEM: rodar ANTES do AUTH-03. Enquanto a leitura usa `service_role`,
--    o RLS é ignorado e o dashboard mostra tudo; no momento em que o AUTH-03
--    passar a ler com o JWT do usuário, o que não tiver dono some.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. ANTES: quantas linhas estão órfãs?
-- ---------------------------------------------------------------------
select
    count(*) filter (where user_id is null) as orfas,
    count(*) filter (where user_id is not null) as com_dono,
    count(*) as total
from public.sleep_data;

-- ---------------------------------------------------------------------
-- 2. Confirme que a conta de destino existe.
--    >>> TROQUE o e-mail abaixo. Deve retornar exatamente 1 linha. <<<
-- ---------------------------------------------------------------------
select id, email, created_at
from auth.users
where email = 'SEU-EMAIL-AQUI@exemplo.com';

-- ---------------------------------------------------------------------
-- 3. O backfill.
--    >>> TROQUE o e-mail nas DUAS ocorrências abaixo. <<<
-- ---------------------------------------------------------------------
begin;

update public.sleep_data
set user_id = (
    select id from auth.users
    where email = 'SEU-EMAIL-AQUI@exemplo.com'
)
where user_id is null
  and exists (
    -- Guarda de segurança: sem a conta, o update vira `user_id = NULL` e não
    -- muda nada de útil. Com o EXISTS, ele simplesmente não roda.
    select 1 from auth.users where email = 'SEU-EMAIL-AQUI@exemplo.com'
  );

-- ---------------------------------------------------------------------
-- 4. DEPOIS: confira o resultado ANTES de confirmar.
--    `orfas` deve ser 0. Se não for, dê ROLLBACK e investigue.
-- ---------------------------------------------------------------------
select
    count(*) filter (where user_id is null) as orfas,
    count(*) filter (where user_id is not null) as com_dono
from public.sleep_data;

commit;
-- rollback;   -- use este no lugar do commit se o resultado não bater

-- =====================================================================
-- APÊNDICE (opcional) — parear um dispositivo manualmente
--
-- Necessário para testar o fluxo do firmware ponta a ponta antes do AUTH-05,
-- que é quem constrói a tela de pareamento.
--
-- O banco guarda apenas o SHA-256 do token; `sha256()` é nativo do Postgres
-- (não precisa de extensão). Escolha um token longo e aleatório — ele é a
-- credencial do dispositivo.
--
--   insert into public.devices (user_id, nome, token_hash)
--   select id,
--          'ESP32 Wokwi',
--          encode(sha256('COLE-AQUI-UM-TOKEN-LONGO-E-ALEATORIO'::bytea), 'hex')
--   from auth.users
--   where email = 'SEU-EMAIL-AQUI@exemplo.com';
--
-- Depois ponha o MESMO token em claro no `firmware/secrets.h`, em
-- DEVICE_TOKEN — e não deixe essa aba aberta ao gravar tela.
-- =====================================================================
