-- =====================================================================
-- 014_id_da_leitura_uuid.sql — DATA-10
-- =====================================================================
-- O QUE ESTAVA QUEBRADO
--
-- `sleep_data.id` é **uuid** na produção. As duas funções de gravação —
-- `registrar_leitura` (placa, pelo token) e `registrar_leitura_da_sessao`
-- (celular, pela sessão) — declaravam `returns bigint` e `v_id bigint` desde a
-- 005, e a 007, a 010 e a 011 copiaram a declaração. O `insert ... returning
-- id into v_id` falha com
--
--     invalid input syntax for type bigint: "<uuid>"   (22P02)
--
-- e NENHUMA leitura é gravada: o backend recebe erro, responde 503, e o
-- dispositivo guarda a época para reenviar. Achado em 09/11, no primeiro envio
-- real à produção (APP-02, o app Android num Moto E7): os logs da Vercel
-- mostraram o erro em cada época.
--
-- POR QUE OS TESTES NÃO PEGARAM
--
-- `tests/rls/esquema_base.sql` criava `sleep_data.id` como `bigserial`, e não
-- como na produção. Com o tipo do teste igual ao da função, a divergência não
-- tinha como aparecer. O esquema de teste passou a usar uuid junto com esta
-- migração; sem ela, 17 testes de RLS falham com o mesmo erro da produção.
--
-- O QUE ESTA MIGRAÇÃO FAZ
--
-- Recria as duas funções devolvendo `uuid`, com o corpo da 011 (o `on
-- conflict` e o id da linha já existente no reenvio). Trocar o tipo de retorno
-- exige `drop` + `create`: o `create or replace` recusa. Por isso os
-- privilégios são refeitos aqui, os mesmos da 007 e da 009 — nenhum para
-- `public` e `anon`; a do token só para `dormio_ingestao`; a da sessão só para
-- `authenticated`.
--
-- O backend NÃO muda: ele só confere se veio um id. Não precisa de release.
-- Idempotente: pode rodar duas vezes.
-- =====================================================================

begin;

-- 1. As funções antigas saem (o tipo de retorno não se troca no lugar).
drop function if exists public.registrar_leitura(text, jsonb);
drop function if exists public.registrar_leitura_da_sessao(uuid, jsonb);

-- ---------------------------------------------------------------------
create function public.registrar_leitura(
    p_token_hash text,
    p_leitura    jsonb
)
returns uuid
language plpgsql
volatile
security definer
set search_path = ''
as $$
declare
    v_device uuid;
    v_dono   uuid;
    v_id     uuid;
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
-- 3. registrar_leitura_da_sessao() — o caminho do celular. O corpo da 011,
--    devolvendo uuid.
-- ---------------------------------------------------------------------
create function public.registrar_leitura_da_sessao(
    p_device_id uuid,
    p_leitura   jsonb
)
returns uuid
language plpgsql
volatile
security definer
set search_path = ''
as $$
declare
    v_dono uuid := auth.uid();
    v_id   uuid;
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

-- 4. Os privilégios, como na 007 e na 009: refeitos porque o `drop` os levou.
revoke all on function public.registrar_leitura(text, jsonb)           from public, anon, authenticated;
revoke all on function public.registrar_leitura_da_sessao(uuid, jsonb) from public, anon, authenticated;
grant execute on function public.registrar_leitura(text, jsonb)           to dormio_ingestao;
grant execute on function public.registrar_leitura_da_sessao(uuid, jsonb) to authenticated;

commit;

-- VERIFICAÇÃO (esperado: as duas com `uuid`; anon sem EXECUTE nas duas;
-- dormio_ingestao só na do token; authenticated só na da sessão)
--
-- select p.proname, pg_get_function_result(p.oid) as devolve,
--        has_function_privilege('anon', p.oid, 'execute')            as anon,
--        has_function_privilege('dormio_ingestao', p.oid, 'execute') as ingestao,
--        has_function_privilege('authenticated', p.oid, 'execute')   as autenticado
--   from pg_proc p
--  where p.proname in ('registrar_leitura', 'registrar_leitura_da_sessao');
