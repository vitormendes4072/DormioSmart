-- =====================================================================
-- 004_tipo_de_dispositivo_e_agregacao.sql
--
-- Itens: DATA-05 (esquema) · DATA-04 (contrato v2.0.0) · APP-01 (coleta
-- pelo celular) · DASH-05 (leitura por dispositivo)
--
-- POR QUE ESTA MIGRAÇÃO EXISTE
--
-- Até aqui só havia uma classe de dispositivo: o ESP32 no travesseiro. Com o
-- celular como segunda fonte, três coisas passam a faltar no esquema:
--
-- 1. NÃO HÁ COMO DISTINGUIR OS INSTRUMENTOS. `devices` guarda nome livre —
--    e nome é escolha do usuário, não classificação. Sem `tipo`, nem a UI nem
--    a análise conseguem separar travesseiro de celular, que medem o mesmo
--    fenômeno por acoplamentos mecânicos diferentes.
--
-- 2. NÃO HÁ HORA DE MEDIÇÃO. `created_at` é a hora do RECEBIMENTO. Serve
--    enquanto o dispositivo envia na hora — o caso do ESP32. Não serve para um
--    celular que agrega por época e envia em lote, nem para o buffer offline
--    do HW-05. `captured_at` é campo NOVO: `created_at` continua existindo e
--    continua significando o que sempre significou, então nenhuma linha antiga
--    muda de sentido.
--
-- 3. NÃO HÁ COMO SABER O QUE UMA LINHA RESUME. Um celular manda uma linha por
--    época; o ESP32, uma por evento. Sem `epoca_segundos` e
--    `metodo_agregacao`, as duas são indistinguíveis na tabela — e o histórico
--    ficaria ambíguo no dia em que o método mudasse (ver CALC-03).
--
-- Idempotente: pode rodar mais de uma vez sem efeito adicional.
-- =====================================================================

begin;

-- ---------------------------------------------------------------------
-- 1. devices.tipo
--    Default 'travesseiro': todo dispositivo que existe hoje é um ESP32 no
--    travesseiro, então o backfill das linhas existentes é o próprio default.
-- ---------------------------------------------------------------------
alter table public.devices
    add column if not exists tipo text not null default 'travesseiro';

do $$
begin
    if not exists (
        select 1 from pg_constraint where conname = 'devices_tipo_valido'
    ) then
        alter table public.devices
            add constraint devices_tipo_valido
            check (tipo in ('travesseiro', 'celular'));
    end if;
end $$;

comment on column public.devices.tipo is
    'Classe do instrumento. NAO e o nome (que e escolha do usuario): e o que '
    'permite separar acoplamentos diferentes na UI e na analise.';

-- ---------------------------------------------------------------------
-- 2. sleep_data — captação e agregação
--    Todas anuláveis: as linhas existentes vieram do ESP32, que envia amostra
--    instantânea e sem relógio. Nulo aqui significa exatamente isso, e não
--    "dado faltando".
-- ---------------------------------------------------------------------
alter table public.sleep_data
    add column if not exists captured_at      timestamptz,
    add column if not exists epoca_segundos   integer,
    add column if not exists metodo_agregacao text,
    add column if not exists amostras         integer;

comment on column public.sleep_data.captured_at is
    'Instante da MEDICAO, informado pelo dispositivo. Nulo = nao informado; '
    'nesse caso vale o created_at, que e a hora do RECEBIMENTO.';
comment on column public.sleep_data.epoca_segundos is
    'Janela que esta linha resume. Nulo = amostra instantanea (ESP32).';
comment on column public.sleep_data.metodo_agregacao is
    'Como a janela foi resumida. Viaja com o dado para que trocar de metodo '
    'depois nao torne o historico ambiguo. Ver docs/DATA-CONTRACT.md 2.5.';

-- ---------------------------------------------------------------------
-- 3. Índice para a consulta por dispositivo (DASH-05)
--    O índice existente é (user_id, created_at desc). A consulta recortada
--    por instrumento filtra também por device_id.
-- ---------------------------------------------------------------------
create index if not exists sleep_data_device_created_idx
    on public.sleep_data (device_id, created_at desc);

commit;

-- =====================================================================
-- VERIFICAÇÃO — rodar depois do commit
-- =====================================================================
--
-- 1. Colunas novas presentes (esperado: 4 linhas)
--
-- select column_name, data_type, is_nullable
--   from information_schema.columns
--  where table_name = 'sleep_data'
--    and column_name in ('captured_at','epoca_segundos','metodo_agregacao','amostras');
--
-- 2. Todo dispositivo existente ficou como 'travesseiro' (esperado: 0 linhas)
--
-- select id, nome, tipo from public.devices where tipo is distinct from 'travesseiro';
--
-- 3. A restrição rejeita tipo desconhecido (esperado: ERRO, e nao sucesso)
--
-- update public.devices set tipo = 'geladeira' where false;
--    -- ^ nao dispara com `where false`; para testar de verdade, num registro
--    --   descartavel: insert ... values (..., 'geladeira') deve falhar.
--
-- 4. Índice criado (esperado: 1 linha)
--
-- select indexname from pg_indexes where indexname = 'sleep_data_device_created_idx';
