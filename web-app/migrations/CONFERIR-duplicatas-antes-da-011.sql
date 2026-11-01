-- =====================================================================
-- CONFERIR-duplicatas-antes-da-011.sql — DATA-08
-- =====================================================================
-- SÓ LEITURA. Rode no SQL Editor ANTES de aplicar a 011.
--
-- A 011 cria um índice único em (device_id, captured_at, epoca_segundos)
-- onde há `captured_at`. Se a produção já tiver leituras repetidas nessa
-- chave, a criação falharia — e a 011 para de propósito com a contagem, em
-- vez de apagar dado. Esta consulta mostra quantas são e quais.
--
-- Resultado esperado: as duas consultas vazias / zero. Se não forem, NÃO
-- aplique a 011: mande o resultado da primeira consulta, e decidimos o que
-- fazer com as repetidas.
-- =====================================================================

-- 1. Quantos grupos repetidos e quantas linhas a mais.
select count(*)                      as grupos_repetidos,
       coalesce(sum(n - 1), 0)       as linhas_a_mais
  from (select count(*) as n
          from public.sleep_data
         where captured_at is not null
         group by device_id, captured_at, epoca_segundos
        having count(*) > 1) d;

-- 2. Os primeiros 20 grupos, para ver de onde vêm (sem dado de usuário além
--    do id do dispositivo e do instante).
select device_id, captured_at, epoca_segundos, count(*) as vezes,
       min(created_at) as primeira, max(created_at) as ultima
  from public.sleep_data
 where captured_at is not null
 group by device_id, captured_at, epoca_segundos
having count(*) > 1
 order by vezes desc, captured_at
 limit 20;
