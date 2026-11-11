-- =====================================================================
-- 017_consentimento_destacado.sql — LGPD-12
--
-- O QUE MUDA
--
-- Desde 10/11/2026 a política de privacidade trata a série de movimento e a
-- estimativa de sono como dado de saúde (seção 2.5), com a base legal do
-- art. 11, I da LGPD: consentimento ESPECÍFICO e DESTACADO, para finalidades
-- específicas. Até aqui o consentimento era só o do cadastro e o de tocar em
-- "Iniciar a noite" — a lacuna estava declarada na seção 4.
--
-- Esta migração dá ao consentimento um registro que o banco conhece e que o
-- titular não forja, e faz o banco recusar o tratamento sem ele:
--
--   1. `profiles` ganha `consentimento_saude_em` (quando) e
--      `consentimento_saude_versao` (qual texto foi aceito).
--   2. `versao_do_consentimento()` diz qual é o texto vigente. Mudar o texto da
--      tela é mudar esta função, e quem aceitou a versão anterior passa a não
--      ter consentimento vigente: a tela aparece de novo.
--   3. `consentir_dado_de_saude(versão)` grava a data com o relógio do BANCO, e
--      só aceita a versão vigente.
--   4. Um gatilho impede o titular de escrever essas duas colunas direto (o
--      `authenticated` tem UPDATE em `profiles`, e a chave anon é pública): a
--      data não é inventável pelo cliente.
--   5. A trava: sem consentimento vigente, `registrar_leitura_da_sessao` (o
--      celular e o navegador) e `parear_dispositivo` recusam. O caminho do
--      TOKEN do dispositivo (`registrar_leitura`) fica sem a trava, de
--      propósito (decisão do autor, 10/11): o firmware descartaria a leitura
--      recusada e a noite se perderia; e como o pareamento exige o
--      consentimento, todo dispositivo novo nasce de uma conta que consentiu.
--
-- Os corpos de `registrar_leitura_da_sessao` e `parear_dispositivo` são os da
-- 016, com o bloco "LGPD-12" acrescentado. `create or replace` preserva os
-- grants.
--
-- ORDEM COM O RELEASE
--
-- Aplicada antes do release que leva a tela, o app instalado recebe a recusa
-- ao enviar, e as épocas esperam no celular (nada se perde: o envio só marca o
-- que o servidor confirmou). Aplicar junto com o release.
--
-- Conferir depois: `DIAGNOSTICO-migracoes-aplicadas.sql`, linha da 017.
-- =====================================================================

begin;

-- ---------------------------------------------------------------------
-- 1. As colunas
-- ---------------------------------------------------------------------
alter table public.profiles
    add column if not exists consentimento_saude_em     timestamptz,
    add column if not exists consentimento_saude_versao text;

comment on column public.profiles.consentimento_saude_em is
    'LGPD-12. Quando o titular deu o consentimento especifico e destacado para o '
    'tratamento da serie de movimento e da estimativa de sono (dado de saude, '
    'art. 11, I). Gravada so por consentir_dado_de_saude(), com o relogio do banco.';
comment on column public.profiles.consentimento_saude_versao is
    'LGPD-12. Qual versao do texto da tela foi aceita. Vigente = '
    'versao_do_consentimento().';

-- ---------------------------------------------------------------------
-- 2. A versão vigente do texto
--    O frontend (`lib/consentimento.ts`) e o backend (`consentimento.py`) têm
--    a mesma constante; um teste confere que as três são iguais.
-- ---------------------------------------------------------------------
create or replace function public.versao_do_consentimento()
returns text
language sql
immutable
set search_path = ''
as $$ select '2026-11-10'::text $$;

revoke all on function public.versao_do_consentimento() from public;
grant execute on function public.versao_do_consentimento() to authenticated;

-- ---------------------------------------------------------------------
-- 3. Consentir
-- ---------------------------------------------------------------------
create or replace function public.consentir_dado_de_saude(p_versao text)
returns jsonb
language plpgsql
volatile
security definer
set search_path = ''
as $$
declare
    v_dono uuid := auth.uid();
    v_em   timestamptz := now();
begin
    if v_dono is null then
        return null;
    end if;
    if p_versao is distinct from public.versao_do_consentimento() then
        raise exception using errcode = 'check_violation',
            message = 'LGPD-12: versao do texto do consentimento desatualizada';
    end if;

    insert into public.profiles (id, consentimento_saude_em, consentimento_saude_versao)
    values (v_dono, v_em, p_versao)
    on conflict (id) do update
        set consentimento_saude_em     = excluded.consentimento_saude_em,
            consentimento_saude_versao = excluded.consentimento_saude_versao;

    return jsonb_build_object('consentimento_saude_em', v_em,
                              'consentimento_saude_versao', p_versao);
end;
$$;

revoke all on function public.consentir_dado_de_saude(text) from public;
revoke all on function public.consentir_dado_de_saude(text) from anon;
grant execute on function public.consentir_dado_de_saude(text) to authenticated;

-- ---------------------------------------------------------------------
-- 4. O titular não escreve as colunas do consentimento direto
-- ---------------------------------------------------------------------
create or replace function public.impedir_consentimento_direto()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
    if current_user in ('authenticated', 'anon') then
        if tg_op = 'INSERT' and (new.consentimento_saude_em is not null
                                 or new.consentimento_saude_versao is not null) then
            raise exception using errcode = 'insufficient_privilege',
                message = 'LGPD-12: o consentimento so e gravado por consentir_dado_de_saude()';
        end if;
        if tg_op = 'UPDATE' and (new.consentimento_saude_em is distinct from old.consentimento_saude_em
                                 or new.consentimento_saude_versao is distinct from old.consentimento_saude_versao) then
            raise exception using errcode = 'insufficient_privilege',
                message = 'LGPD-12: o consentimento so e gravado por consentir_dado_de_saude()';
        end if;
    end if;
    return new;
end;
$$;

revoke all on function public.impedir_consentimento_direto() from public;
do $$
declare
    papel text;
begin
    foreach papel in array array['anon', 'authenticated', 'service_role', 'dormio_ingestao'] loop
        if exists (select 1 from pg_roles where rolname = papel) then
            execute format('revoke all on function public.impedir_consentimento_direto() from %I', papel);
        end if;
    end loop;
end $$;

drop trigger if exists profiles_consentimento_so_pela_funcao on public.profiles;
create trigger profiles_consentimento_so_pela_funcao
    before insert or update on public.profiles
    for each row execute function public.impedir_consentimento_direto();

-- ---------------------------------------------------------------------
-- 5. A trava na gravação pela sessão e no pareamento
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

    -- LGPD-12: sem consentimento vigente para dado de saude, nada e tratado.
    if not exists (select 1 from public.profiles p
                    where p.id = v_dono
                      and p.consentimento_saude_versao = public.versao_do_consentimento()) then
        raise exception using errcode = 'insufficient_privilege',
            message = 'LGPD-12: consentimento para dado de saude pendente';
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

commit;
