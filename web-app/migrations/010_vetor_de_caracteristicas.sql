-- =====================================================================
-- 010_vetor_de_caracteristicas.sql — DATA-07b (d)
-- =====================================================================
-- O QUE FALTAVA
--
-- O modelo do `ML-01` não consome magnitude e rótulo: consome um vetor de
-- características por época de 30 s (contrato v2.5.0 §2.6). Até aqui o banco
-- não tinha onde guardá-lo, e as duas funções de gravação só extraíam do JSON
-- os campos que já conheciam — um `f` que chegasse seria descartado em
-- silêncio, com 201.
--
-- O QUE ESTA MIGRAÇÃO FAZ
--
-- 1. Dez colunas em `sleep_data`, uma por número, com o NOME de cada feature.
--    Não um array: um array na ordem errada passaria em toda faixa e produziria
--    um modelo errado em silêncio (trocar a ordem é mudança MAJOR do contrato).
--    Com nome, a ordem de `f` vira nome uma vez, no backend
--    (`validacao.colunas_de_features`), e daí em diante ninguém depende dela.
-- 2. Uma restrição "tudo ou nada": as dez preenchidas ou as dez nulas. Um vetor
--    pela metade não é um vetor — e é exatamente o que uma função de gravação
--    desatualizada, ou um script avulso, produziria.
-- 3. As duas funções de gravação recriadas para extrair os campos novos, campo
--    a campo, como a 005 decidiu (nada de `jsonb_populate_record`: o chamador
--    não escolhe coluna).
--
-- O QUE ELA NÃO FAZ
--
-- Não valida faixa: isso é do backend (`validacao._validar_features`), que é a
-- única porta de entrada. `inclinacao_rel` e `d_angulo` NÃO têm coluna: são
-- derivadas sobre a noite inteira, na leitura (`features_noite.py`, DATA-07b
-- (e)), porque dependem de épocas que ainda não existiam quando esta chegou.
--
-- ⚠️ ORDEM DE APLICAÇÃO: esta migração entra no banco ANTES do release que
-- leva o backend novo para `main`. Na ordem inversa, o backend validaria `f` e
-- a função antiga o jogaria fora, respondendo 201. O diagnóstico
-- (`DIAGNOSTICO-migracoes-aplicadas.sql`) confere as funções, não só as
-- colunas, justamente por isso.
--
-- `create or replace` preserva os privilégios das funções (os da 009).
-- Idempotente: pode rodar duas vezes.
-- =====================================================================

begin;

-- ---------------------------------------------------------------------
-- 1. As colunas. Unidades do contrato: as seis primeiras em g (NÃO m/s²,
--    ao contrário do resto da linha), `g_*` adimensional, `fs_features` em Hz.
-- ---------------------------------------------------------------------
alter table public.sleep_data
    add column if not exists enmo_media    double precision,
    add column if not exists enmo_desvio   double precision,
    add column if not exists enmo_max      double precision,
    add column if not exists mag_din_media double precision,
    add column if not exists zcr           double precision,
    add column if not exists p_frac        double precision,
    add column if not exists g_x           double precision,
    add column if not exists g_y           double precision,
    add column if not exists g_z           double precision,
    add column if not exists fs_features   double precision;

comment on column public.sleep_data.enmo_media is
    'Feature 0 do contrato 2.6, em g. Nula = leitura sem vetor (dispositivo antigo, epoca degradada).';
comment on column public.sleep_data.g_x is
    'Direcao unitaria da gravidade na epoca (contrato 2.6). Insumo de inclinacao_rel e d_angulo, derivadas na leitura.';
comment on column public.sleep_data.fs_features is
    'Taxa (Hz) da grade que produziu o vetor. Sem ela zcr e p_frac nao sao interpretaveis.';

-- ---------------------------------------------------------------------
-- 2. Tudo ou nada.
-- ---------------------------------------------------------------------
do $$
begin
    if not exists (select 1 from pg_constraint
                    where conname = 'sleep_data_features_tudo_ou_nada') then
        alter table public.sleep_data
            add constraint sleep_data_features_tudo_ou_nada check (
                num_nonnulls(enmo_media, enmo_desvio, enmo_max, mag_din_media,
                             zcr, p_frac, g_x, g_y, g_z, fs_features) in (0, 10)
            );
    end if;
end $$;

-- ---------------------------------------------------------------------
-- 3. registrar_leitura() — o caminho do token. Igual à da 007, mais as dez.
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
    returning id into v_id;

    begin
        update public.devices set last_seen_at = now() where id = v_device;
    exception when others then
        null;
    end;

    return v_id;
end;
$$;

-- ---------------------------------------------------------------------
-- 4. registrar_leitura_da_sessao() — o caminho do celular. Igual à da 005,
--    mais as dez.
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
    returning id into v_id;

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

-- VERIFICAÇÃO (esperado: 10 colunas; a restrição; as duas funções citando
-- `fs_features`; anon sem EXECUTE nas duas, como na 009)
--
-- select count(*) from information_schema.columns
--  where table_schema = 'public' and table_name = 'sleep_data'
--    and column_name in ('enmo_media','enmo_desvio','enmo_max','mag_din_media',
--                        'zcr','p_frac','g_x','g_y','g_z','fs_features');
-- select proname, pg_get_functiondef(oid) like '%fs_features%' as extrai_features,
--        has_function_privilege('anon', oid, 'execute') as anon
--   from pg_proc where proname in ('registrar_leitura','registrar_leitura_da_sessao');
