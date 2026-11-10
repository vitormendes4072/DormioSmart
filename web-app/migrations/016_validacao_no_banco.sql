-- =====================================================================
-- 016_validacao_no_banco.sql — SEC-18
--
-- O DEFEITO
--
-- A validação da leitura (faixa física, estado, época, vetor de
-- características, instante futuro) vivia só no Flask (`web-app/validacao.py`).
-- `registrar_leitura_da_sessao` tem EXECUTE para `authenticated`, e o endereço
-- do Supabase e a chave anon são públicos por desenho: quem tem conta chama a
-- função direto e grava qualquer coisa NA PRÓPRIA CONTA. Medido na auditoria de
-- 10/11 (AUD-02), num Postgres 17 com as migrações da produção: gravou `NaN`,
-- `Infinity`, `1e300`, captura em 2099, época −5 e estado livre. O mesmo em
-- `devices` (AUD-03): nome de 100 000 caracteres, 500 dispositivos numa
-- chamada, `token_hash` escolhido pelo cliente, e a revogação desfeita por um
-- `update` direto. Nada disso cruza contas — o RLS segura —, mas contamina o
-- dado do próprio titular, e é exatamente o dado que o trabalho analisa.
--
-- O QUE ESTA MIGRAÇÃO FAZ
--
--   1. Restrições `CHECK` em `sleep_data` com AS MESMAS faixas da
--      `validacao.py`, nem mais largas nem mais estreitas. Mais estreita que o
--      Flask faria uma leitura que o backend aceitou falhar no banco: 503, e o
--      dispositivo reenviando para sempre. `test_rls_validacao_no_banco.py`
--      confere as bordas das duas, lado a lado. No Postgres, `NaN` é maior que
--      qualquer número e o infinito também, então a faixa já os recusa.
--      Coluna nula passa (o CHECK só reprova o que é falso): leitura sem o
--      vetor, ou do ESP32 sem giroscópio, continua válida.
--   2. As duas funções de gravação recusam `captured_at` mais de 5 minutos no
--      futuro, a mesma tolerância do Flask. Não é `CHECK` porque dependeria de
--      `now()`: a restrição mudaria de resultado com o tempo e quebraria a
--      restauração de uma cópia.
--   3. `devices.nome` com no máximo 60 caracteres (o `NOME_MAXIMO` do backend);
--      `parear_dispositivo` recusa `token_hash` que não tenha o formato do
--      SHA-256 (64 hexadecimais) e o 11º dispositivo ativo da conta; e um
--      gatilho impede que o titular desfaça a revogação. O dono do banco
--      (manutenção) continua podendo.
--
-- COMO ENTRA SEM RISCO
--
-- As restrições entram `NOT VALID` (valem para o que chegar depois) e a
-- migração confere o que já existe contra cada uma. Se alguma linha antiga
-- falhar, ela PARA com a contagem por restrição, sem apagar nada, e a
-- transação inteira volta — como a 011 fez com as duplicatas. Na produção, a
-- consulta 5.1 da auditoria deu zero em 10/11.
--
-- FORA DE ESCOPO, DE PROPÓSITO
--
-- O volume por chamada (2 000 leituras numa só): afeta só a própria conta, e
-- limitar ritmo não é coisa que o Postgres faça bem. A coerência de `total`
-- com (ax, ay, az) e o "sensor mudo" ficam no Flask: são regras sobre o
-- payload do dispositivo, não sobre o domínio da coluna.
--
-- Conferir depois: `DIAGNOSTICO-migracoes-aplicadas.sql`, linha da 016.
-- =====================================================================

begin;

-- ---------------------------------------------------------------------
-- 1. As faixas, as mesmas de `web-app/validacao.py`
-- ---------------------------------------------------------------------
alter table public.sleep_data
    add constraint sleep_data_faixa_aceleracao check (
            (accel_x is null or accel_x between -100 and 100)
        and (accel_y is null or accel_y between -100 and 100)
        and (accel_z is null or accel_z between -100 and 100)
        and (movimento_total is null or movimento_total between 0 and 175)
    ) not valid,
    add constraint sleep_data_faixa_giroscopio check (
            (gyro_x is null or gyro_x between -40 and 40)
        and (gyro_y is null or gyro_y between -40 and 40)
        and (gyro_z is null or gyro_z between -40 and 40)
    ) not valid,
    add constraint sleep_data_faixa_temperatura check (
        temp is null or temp between -40 and 85
    ) not valid,
    add constraint sleep_data_estado_valido check (
        status is null or status in ('Repouso', 'Movimento')
    ) not valid,
    add constraint sleep_data_agregacao_valida check (
            (epoca_segundos is null or epoca_segundos between 1 and 3600)
        and (metodo_agregacao is null or metodo_agregacao in ('pico-da-magnitude'))
        and (amostras is null or amostras >= 1)
    ) not valid,
    add constraint sleep_data_faixa_features check (
            (enmo_media is null or enmo_media between 0 and 1)
        and (enmo_desvio is null or enmo_desvio between 0 and 1)
        and (enmo_max is null or enmo_max between 0 and 16)
        and (mag_din_media is null or mag_din_media between 0 and 2)
        and (zcr is null or zcr between 0 and 1)
        and (p_frac is null or p_frac between 0 and 1)
        and (fs_features is null or (fs_features > 0 and fs_features <= 200))
    ) not valid,
    -- `g` unitário (|g| = 1 ± 1e-3), a mesma checagem de coerência do Flask.
    add constraint sleep_data_gravidade_unitaria check (
        g_x is null or (
                g_x between -1 and 1 and g_y between -1 and 1 and g_z between -1 and 1
            and abs(sqrt(g_x * g_x + g_y * g_y + g_z * g_z) - 1) <= 1e-3
        )
    ) not valid;

alter table public.devices
    add constraint devices_nome_tamanho check (char_length(nome) <= 60) not valid;

-- ---------------------------------------------------------------------
-- 2. O que já existe, conferido contra cada restrição. Se algo falhar, a
--    migração para aqui, com a contagem, e nada do que veio acima fica.
-- ---------------------------------------------------------------------
do $$
declare
    r        record;
    v_n      bigint;
    v_falhas text := '';
begin
    for r in
        select c.conname, c.conrelid::regclass as tabela,
               regexp_replace(pg_get_constraintdef(c.oid), '^CHECK \((.*)\) NOT VALID$', '\1') as cond
          from pg_constraint c
         where c.conname in ('sleep_data_faixa_aceleracao', 'sleep_data_faixa_giroscopio',
                             'sleep_data_faixa_temperatura', 'sleep_data_estado_valido',
                             'sleep_data_agregacao_valida', 'sleep_data_faixa_features',
                             'sleep_data_gravidade_unitaria', 'devices_nome_tamanho')
    loop
        -- `not (cond)` é nulo quando `cond` é nulo, e a linha não conta: é
        -- exatamente a regra do CHECK, que só reprova o que é falso.
        execute format('select count(*) from %s where not (%s)', r.tabela, r.cond) into v_n;
        if v_n > 0 then
            v_falhas := v_falhas || format('%s: %s linha(s); ', r.conname, v_n);
        end if;
    end loop;
    if v_falhas <> '' then
        raise exception 'SEC-18: ha dado existente fora das regras novas, e nada foi aplicado. %', v_falhas
            using hint = 'Nenhuma linha foi apagada. Decida o que fazer com elas e rode de novo.';
    end if;
end $$;

alter table public.sleep_data validate constraint sleep_data_faixa_aceleracao;
alter table public.sleep_data validate constraint sleep_data_faixa_giroscopio;
alter table public.sleep_data validate constraint sleep_data_faixa_temperatura;
alter table public.sleep_data validate constraint sleep_data_estado_valido;
alter table public.sleep_data validate constraint sleep_data_agregacao_valida;
alter table public.sleep_data validate constraint sleep_data_faixa_features;
alter table public.sleep_data validate constraint sleep_data_gravidade_unitaria;
alter table public.devices    validate constraint devices_nome_tamanho;

-- ---------------------------------------------------------------------
-- 3. As funções de gravação recusam o futuro
--    `create or replace` com a mesma assinatura e o mesmo retorno da 014:
--    preserva os grants (`dormio_ingestao` numa, `authenticated` na outra).
--    O corpo é o da 014, com o bloco "SEC-18" antes do insert.
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

-- ---------------------------------------------------------------------
-- 4. O pareamento: formato do hash e teto de dispositivos
--    Corpo da 007, com o bloco "SEC-18" no começo. `create or replace`
--    preserva o grant para `authenticated` e a revogação de `anon`.
-- ---------------------------------------------------------------------
create or replace function public.parear_dispositivo(
    p_nome       text,
    p_tipo       text,
    p_token_hash text
)
returns table (
    id           uuid,
    nome         text,
    tipo         text,
    created_at   timestamptz,
    last_seen_at timestamptz,
    revoked_at   timestamptz
)
language plpgsql
volatile
security definer
set search_path = ''
as $$
declare
    v_dono   uuid := auth.uid();
    v_device uuid;
begin
    if v_dono is null then
        return;
    end if;

    -- SEC-18: o backend manda o SHA-256 em hexadecimal do token que ele mesmo
    -- gerou (`device_auth.hash_token`). Um hash escolhido pelo cliente seria
    -- um token adivinhável para o próprio dispositivo.
    if p_token_hash is null or p_token_hash !~ '^[0-9a-f]{64}$' then
        raise exception using errcode = 'check_violation',
            message = 'SEC-18: token_hash fora do formato SHA-256 (64 hexadecimais)';
    end if;
    -- SEC-18: teto de dispositivos ATIVOS por conta. Em 10/11 a produção tinha
    -- no máximo 2 por conta; 10 é folga, não alvo.
    if (select count(*) from public.devices d
         where d.user_id = v_dono and d.revoked_at is null) >= 10 then
        raise exception using errcode = 'check_violation',
            message = 'SEC-18: limite de 10 dispositivos ativos por conta';
    end if;

    -- A validação de `tipo` também existe em Python (`dispositivos.validar_tipo`).
    -- Aqui é a `check constraint` da 004 que segura, e ela é a autoridade: a
    -- validação em Python melhora a mensagem de erro, não a garantia.
    insert into public.devices (user_id, nome, tipo)
    values (v_dono, p_nome, coalesce(p_tipo, 'travesseiro'))
    returning devices.id into v_device;

    insert into public.device_tokens (device_id, token_hash)
    values (v_device, p_token_hash);

    return query
        select d.id, d.nome, d.tipo, d.created_at, d.last_seen_at, d.revoked_at
          from public.devices d
         where d.id = v_device;
end;
$$;

-- ---------------------------------------------------------------------
-- 5. A revogação é definitiva para o titular
--    Revogar é o que corta um token vazado. Se o próprio titular (ou quem
--    tiver a sessão dele) pudesse desfazer, o token voltaria a valer. O dono
--    do banco continua podendo, para manutenção: o gatilho só barra os papéis
--    do cliente.
-- ---------------------------------------------------------------------
create or replace function public.impedir_desrevogacao()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
    if old.revoked_at is not null and new.revoked_at is null
       and current_user in ('authenticated', 'anon') then
        raise exception using errcode = 'check_violation',
            message = 'SEC-18: um dispositivo revogado nao volta a valer';
    end if;
    return new;
end;
$$;

revoke all on function public.impedir_desrevogacao() from public;
do $$
declare
    papel text;
begin
    foreach papel in array array['anon', 'authenticated', 'service_role', 'dormio_ingestao'] loop
        if exists (select 1 from pg_roles where rolname = papel) then
            execute format('revoke all on function public.impedir_desrevogacao() from %I', papel);
        end if;
    end loop;
end $$;

drop trigger if exists devices_revogacao_definitiva on public.devices;
create trigger devices_revogacao_definitiva
    before update of revoked_at on public.devices
    for each row execute function public.impedir_desrevogacao();

commit;
