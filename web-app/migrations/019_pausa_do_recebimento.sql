-- API-07: a pausa preserva a credencial e descarta leituras na ingestão.
-- Ambas as RPCs mantêm as assinaturas e os privilégios da 018.
-- O lock da linha serializa a decisão com pausa, retomada e revogação.

begin;

alter table public.devices
    add column receber_leituras boolean not null default true;

create or replace function public.registrar_leitura(
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
    v_receber boolean;
begin
    select d.id, d.user_id, d.receber_leituras into v_device, v_dono, v_receber
      from public.device_tokens t
      join public.devices d on d.id = t.device_id
     where t.token_hash = p_token_hash
       and d.revoked_at is null
     limit 1
       for update of d;

    if v_device is null then
        return null;
    end if;

    if not v_receber then
        raise exception using errcode = 'PT409', message = 'aparelho_pausado';
    end if;

    -- SEC-18: a mesma recusa de `validacao.validar_captacao` (5 min de folga).
    if (p_leitura ->> 'captured_at')::timestamptz > now() + interval '5 minutes' then
        raise exception using errcode = 'check_violation',
            message = 'SEC-18: captured_at no futuro';
    end if;

    insert into public.sleep_data (
        accel_x, accel_y, accel_z,
        gyro_x,  gyro_y,  gyro_z,
        temp, movimento_total, status,
        captured_at, epoca_segundos, metodo_agregacao, amostras,
        enmo_media, enmo_desvio, enmo_max, mag_din_media, zcr, p_frac,
        g_x, g_y, g_z, fs_features,
        g_norma, calibrada,
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
        (p_leitura ->> 'g_norma')::double precision,
        (p_leitura ->> 'calibrada')::boolean,
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
-- A gravação pela sessão (celular), como a 017, com as duas colunas.
-- ---------------------------------------------------------------------
create or replace function public.registrar_leitura_da_sessao(
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
    v_receber boolean;
begin
    if v_dono is null then
        return null;
    end if;

    -- LGPD-12: sem consentimento vigente para dado de saude, nada e tratado.
    if not exists (select 1 from public.profiles p
                    where p.id = v_dono
                      and p.consentimento_saude_versao = public.versao_do_consentimento()) then
        raise exception using errcode = 'insufficient_privilege',
            message = 'LGPD-12: consentimento para dado de saude pendente';
    end if;

    select d.receber_leituras into v_receber
      from public.devices d
     where d.id = p_device_id
       and d.user_id = v_dono
       and d.revoked_at is null
       for update of d;

    if not found then
        return null;
    end if;

    if not v_receber then
        raise exception using errcode = 'PT409', message = 'aparelho_pausado';
    end if;

    -- SEC-18: a mesma recusa de `validacao.validar_captacao` (5 min de folga).
    if (p_leitura ->> 'captured_at')::timestamptz > now() + interval '5 minutes' then
        raise exception using errcode = 'check_violation',
            message = 'SEC-18: captured_at no futuro';
    end if;

    insert into public.sleep_data (
        accel_x, accel_y, accel_z,
        gyro_x,  gyro_y,  gyro_z,
        temp, movimento_total, status,
        captured_at, epoca_segundos, metodo_agregacao, amostras,
        enmo_media, enmo_desvio, enmo_max, mag_din_media, zcr, p_frac,
        g_x, g_y, g_z, fs_features,
        g_norma, calibrada,
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
        (p_leitura ->> 'g_norma')::double precision,
        (p_leitura ->> 'calibrada')::boolean,
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
