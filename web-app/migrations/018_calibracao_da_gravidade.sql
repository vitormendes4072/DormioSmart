-- =====================================================================
-- 018_calibracao_da_gravidade.sql — CAL-03, etapa 1 (contrato 2.9.0)
-- =====================================================================
--
-- O QUE ENTRA
--
-- Duas colunas em `sleep_data`, que o payload do celular passa a trazer junto
-- do vetor da época (`f`, `g`, `fs`):
--
--   g_norma    a norma da gravidade média da época, em g. A direção já vinha
--              (`g_x`, `g_y`, `g_z`, unitário); a norma é o que diz o erro de
--              calibração: parada, a época deveria dar 1 g. No Moto E7, sem
--              calibração, ela vai de 0,991 a 1,020 g conforme a posição
--              (diário, 10/11 iv), e esse erro vira "movimento" no ENMO.
--   calibrada  se as amostras da época passaram por uma calibração aceita
--              (autocalibração pela gravidade, `firmware/nucleo/calibracao.h`).
--              É o que deixa o dado dizer qual época foi corrigida.
--
-- As duas são opcionais: o app antigo e o travesseiro não as mandam, e a
-- coluna fica nula. A mesma regra no Flask (`validacao.py`) e aqui
-- (`sleep_data_calibracao_valida`): `g_norma` em [0, 8] g (o fundo de escala
-- da C2) e as duas só com o vetor presente.
--
-- E as duas funções de gravação passam a inseri-las, na versão mais recente de
-- cada uma: a do token como a 016 a deixou, a da sessão como a 017 (com a trava
-- do consentimento). Nada mais muda nelas.
--
-- COMO ENTRA SEM RISCO
--
-- Colunas novas nascem nulas, e a restrição passa em todas as linhas antigas;
-- ela entra validada. Nenhum dado existente muda.
--
-- ORDEM
--
-- Antes do release que leva o backend 2.9.0. O backend antigo não manda as
-- chaves novas no `p_leitura`, e a função nova grava nulo nelas — não quebra.
-- O contrário (backend novo, banco sem a 018) quebraria: a função antiga
-- ignoraria as chaves, e o dado da calibração se perderia em silêncio.
-- =====================================================================

begin;

alter table public.sleep_data
    add column if not exists g_norma   double precision,
    add column if not exists calibrada boolean;

comment on column public.sleep_data.g_norma is
    'CAL-03. Norma da gravidade media da epoca, em g. Parada, deveria ser 1 g; '
    'o quanto se afasta e o erro de calibracao do acelerometro.';
comment on column public.sleep_data.calibrada is
    'CAL-03. Se as amostras da epoca passaram por uma autocalibracao aceita.';

alter table public.sleep_data drop constraint if exists sleep_data_calibracao_valida;
alter table public.sleep_data
    add constraint sleep_data_calibracao_valida check (
        (g_norma is null or (g_norma between 0 and 8 and enmo_media is not null))
        and (calibrada is null or enmo_media is not null)
    );

-- ---------------------------------------------------------------------
-- A gravação pelo token (dispositivo), como a 016, com as duas colunas.
-- ---------------------------------------------------------------------
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

    if not exists (
        select 1 from public.devices d
         where d.id = p_device_id
           and d.user_id = v_dono
           and d.revoked_at is null
    ) then
        return null;
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
