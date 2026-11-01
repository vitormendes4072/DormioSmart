-- =====================================================================
-- 011_leitura_idempotente.sql — DATA-08
-- =====================================================================
-- O QUE FALTAVA
--
-- `sleep_data` não tinha restrição de unicidade, e as duas funções de gravação
-- faziam `insert` simples. O firmware reenvia toda leitura que não teve
-- confirmação; se o servidor gravou e a resposta se perdeu (timeout, cold
-- start da Vercel), a mesma época virava duas linhas. Em `features_noite`, a
-- duplicata produz `d_angulo = 0` artificial e puxa o `g_ref` — dado de
-- pesquisa contaminado em silêncio. Achado A2 da auditoria de 31/10
-- (`docs/AUDITORIA-2026-10-31.md`); o contrato já registrava o risco como
-- "duplicata, não resolvida".
--
-- O QUE ESTA MIGRAÇÃO FAZ
--
-- 1. Um índice único parcial em (device_id, captured_at, epoca_segundos),
--    só onde há `captured_at`: é o instante da medição que identifica a
--    época. Antes de criá-lo, CONFERE se já há duplicatas e, se houver, PARA
--    com a contagem — não apaga dado para conseguir criar o índice. Rode
--    antes `CONFERIR-duplicatas-antes-da-011.sql`.
-- 2. As duas funções de gravação recriadas com `on conflict ... do nothing`.
--    No conflito, devolvem o id da linha que JÁ EXISTE: o backend trata "veio
--    id" como gravado, então o reenvio é aceito e a época sai da fila. Se
--    devolvessem nulo, o backend responderia 503 e o firmware reenviaria
--    para sempre.
--
-- O QUE ELA NÃO DEDUPLICA, E É DECLARADO
--
-- Leitura sem `ts` (`captured_at` nulo): sem o instante da medição não há
-- como saber que é a mesma. E leitura sem `epoca_segundos`: nulo nunca conflita
-- num índice. As duas continuam gravando sempre.
--
-- O backend NÃO muda: não precisa de release. `create or replace` preserva os
-- privilégios das funções (os da 009). Idempotente: pode rodar duas vezes.
-- =====================================================================

begin;

-- ---------------------------------------------------------------------
-- 1. O índice, depois de conferir que ele pode existir.
-- ---------------------------------------------------------------------
do $$
declare
    v_grupos bigint;
begin
    select count(*) into v_grupos
      from (select 1
              from public.sleep_data
             where captured_at is not null
             group by device_id, captured_at, epoca_segundos
            having count(*) > 1) d;
    if v_grupos > 0 then
        raise exception
            'DATA-08: % grupo(s) de leituras duplicadas em sleep_data. A 011 nao apaga dado; rode CONFERIR-duplicatas-antes-da-011.sql e decida o que fazer com elas antes.',
            v_grupos;
    end if;
end $$;

create unique index if not exists sleep_data_epoca_unica
    on public.sleep_data (device_id, captured_at, epoca_segundos)
    where captured_at is not null;

-- ---------------------------------------------------------------------
-- 2. registrar_leitura() — o caminho do token. Igual à da 010, com o `on conflict`.
-- ---------------------------------------------------------------------
create or replace function public.registrar_leitura(
    p_token_hash text,
    p_leitura    jsonb
)
returns bigint
language plpgsql
volatile
security definer
set search_path = ''
as $$
declare
    v_device uuid;
    v_dono   uuid;
    v_id     bigint;
begin
    select d.id, d.user_id into v_device, v_dono
      from public.device_tokens t
      join public.devices d on d.id = t.device_id
     where t.token_hash = p_token_hash
       and d.revoked_at is null
     limit 1;

    if v_device is null then
        return null;
    end if;

    insert into public.sleep_data (
        accel_x, accel_y, accel_z,
        gyro_x,  gyro_y,  gyro_z,
        temp, movimento_total, status,
        captured_at, epoca_segundos, metodo_agregacao, amostras,
        enmo_media, enmo_desvio, enmo_max, mag_din_media, zcr, p_frac,
        g_x, g_y, g_z, fs_features,
        user_id, device_id
    ) values (
        (p_leitura ->> 'accel_x')::double precision,
        (p_leitura ->> 'accel_y')::double precision,
        (p_leitura ->> 'accel_z')::double precision,
        (p_leitura ->> 'gyro_x')::double precision,
        (p_leitura ->> 'gyro_y')::double precision,
        (p_leitura ->> 'gyro_z')::double precision,
        (p_leitura ->> 'temp')::double precision,
        (p_leitura ->> 'movimento_total')::double precision,
        (p_leitura ->> 'status')::text,
        (p_leitura ->> 'captured_at')::timestamptz,
        (p_leitura ->> 'epoca_segundos')::integer,
        (p_leitura ->> 'metodo_agregacao')::text,
        (p_leitura ->> 'amostras')::integer,
        (p_leitura ->> 'enmo_media')::double precision,
        (p_leitura ->> 'enmo_desvio')::double precision,
        (p_leitura ->> 'enmo_max')::double precision,
        (p_leitura ->> 'mag_din_media')::double precision,
        (p_leitura ->> 'zcr')::double precision,
        (p_leitura ->> 'p_frac')::double precision,
        (p_leitura ->> 'g_x')::double precision,
        (p_leitura ->> 'g_y')::double precision,
        (p_leitura ->> 'g_z')::double precision,
        (p_leitura ->> 'fs_features')::double precision,
        v_dono,
        v_device
    )
    on conflict (device_id, captured_at, epoca_segundos)
        where captured_at is not null
        do nothing
    returning id into v_id;

    -- Reenvio da mesma época: o `on conflict` não grava e não devolve nada.
    -- Devolver nulo faria o backend responder 503 ("não persistiu") e o
    -- firmware reenviar para sempre. Devolve o id da linha que já existe: o
    -- reenvio conta como aceito, e a época sai da fila do dispositivo.
    if v_id is null then
        select s.id into v_id
          from public.sleep_data s
         where s.device_id = v_device
           and s.captured_at = (p_leitura ->> 'captured_at')::timestamptz
           and s.epoca_segundos = (p_leitura ->> 'epoca_segundos')::integer
         limit 1;
    end if;

    begin
        update public.devices set last_seen_at = now() where id = v_device;
    exception when others then
        null;
    end;

    return v_id;
end;
$$;

-- ---------------------------------------------------------------------
-- 3. registrar_leitura_da_sessao() — o caminho do celular. Igual à da 010,
--    com o `on conflict`.
-- ---------------------------------------------------------------------
create or replace function public.registrar_leitura_da_sessao(
    p_device_id uuid,
    p_leitura   jsonb
)
returns bigint
language plpgsql
volatile
security definer
set search_path = ''
as $$
declare
    v_dono uuid := auth.uid();
    v_id   bigint;
begin
    if v_dono is null then
        return null;
    end if;

    if not exists (
        select 1 from public.devices d
         where d.id = p_device_id
           and d.user_id = v_dono
           and d.revoked_at is null
    ) then
        return null;
    end if;

    insert into public.sleep_data (
        accel_x, accel_y, accel_z,
        gyro_x,  gyro_y,  gyro_z,
        temp, movimento_total, status,
        captured_at, epoca_segundos, metodo_agregacao, amostras,
        enmo_media, enmo_desvio, enmo_max, mag_din_media, zcr, p_frac,
        g_x, g_y, g_z, fs_features,
        user_id, device_id
    ) values (
        (p_leitura ->> 'accel_x')::double precision,
        (p_leitura ->> 'accel_y')::double precision,
        (p_leitura ->> 'accel_z')::double precision,
        (p_leitura ->> 'gyro_x')::double precision,
        (p_leitura ->> 'gyro_y')::double precision,
        (p_leitura ->> 'gyro_z')::double precision,
        (p_leitura ->> 'temp')::double precision,
        (p_leitura ->> 'movimento_total')::double precision,
        (p_leitura ->> 'status')::text,
        (p_leitura ->> 'captured_at')::timestamptz,
        (p_leitura ->> 'epoca_segundos')::integer,
        (p_leitura ->> 'metodo_agregacao')::text,
        (p_leitura ->> 'amostras')::integer,
        (p_leitura ->> 'enmo_media')::double precision,
        (p_leitura ->> 'enmo_desvio')::double precision,
        (p_leitura ->> 'enmo_max')::double precision,
        (p_leitura ->> 'mag_din_media')::double precision,
        (p_leitura ->> 'zcr')::double precision,
        (p_leitura ->> 'p_frac')::double precision,
        (p_leitura ->> 'g_x')::double precision,
        (p_leitura ->> 'g_y')::double precision,
        (p_leitura ->> 'g_z')::double precision,
        (p_leitura ->> 'fs_features')::double precision,
        v_dono,
        p_device_id
    )
    on conflict (device_id, captured_at, epoca_segundos)
        where captured_at is not null
        do nothing
    returning id into v_id;

    -- Reenvio da mesma época: o `on conflict` não grava e não devolve nada.
    -- Devolver nulo faria o backend responder 503 ("não persistiu") e o
    -- firmware reenviar para sempre. Devolve o id da linha que já existe: o
    -- reenvio conta como aceito, e a época sai da fila do dispositivo.
    if v_id is null then
        select s.id into v_id
          from public.sleep_data s
         where s.device_id = p_device_id
           and s.captured_at = (p_leitura ->> 'captured_at')::timestamptz
           and s.epoca_segundos = (p_leitura ->> 'epoca_segundos')::integer
         limit 1;
    end if;

    begin
        update public.devices
           set last_seen_at = now()
         where id = p_device_id;
    exception when others then
        null;
    end;

    return v_id;
end;
$$;

commit;

-- VERIFICAÇÃO (esperado: o índice; as duas funções com `on conflict`; anon sem
-- EXECUTE nas duas, como na 009)
--
-- select indexname from pg_indexes where indexname = 'sleep_data_epoca_unica';
-- select proname, pg_get_functiondef(oid) like '%on conflict%' as idempotente,
--        has_function_privilege('anon', oid, 'execute') as anon
--   from pg_proc where proname in ('registrar_leitura','registrar_leitura_da_sessao');
