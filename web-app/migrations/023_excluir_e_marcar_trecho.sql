-- DATA-16 (21/11/2026): excluir uma sessão e marcá-la como bancada/teste.
--
-- O servidor guarda épocas, e não sessões: a "sessão de captação" é deduzida
-- no cliente pelas pausas no envio (`agruparEmSessoes`). Até aqui, tirar uma
-- bancada da conta era SQL à mão (12/11, 16/11 e 21/11), e a placa não tinha
-- como dizer "isto foi teste". Esta migração dá ao titular duas operações
-- sobre um TRECHO — um aparelho, um início e um fim, os mesmos que o cliente
-- usa para desenhar a sessão:
--
--  1. `sleep_data.bancada`: a época marcada continua guardada, mas sai do
--     Histórico, do painel, do CSV, das features e da inferência. Coluna, e
--     não tabela de trechos, para que cada consulta filtre sem junção e para
--     funcionar no Postgres 14 do CI (visão com `security_invoker` é do 15).
--  2. `apagar_trecho(device, desde, ate)` e
--     `marcar_trecho(device, desde, ate, bancada)`: `security definer`, como a
--     `apagar_minha_conta()` (006), e pelo mesmo motivo — o dono vem SEMPRE de
--     `auth.uid()`, nunca de parâmetro. Um aparelho de outra conta na chamada
--     não alcança nada. Devolvem quantas épocas foram afetadas, que é o que a
--     tela mostra ao confirmar.
--
-- O instante da época é `coalesce(captured_at, created_at)`: o mesmo
-- `instanteDaLeitura` do cliente (`types/sleep.ts`), para que o trecho que o
-- usuário vê seja o trecho que o banco apaga.
--
-- Teto de 48 h por chamada: um início ou fim errado não leva a conta inteira.
-- Para isso existe a `apagar_minha_conta()`.
--
-- Idempotente: reaplicar não quebra.

begin;

-- ---------------------------------------------------------------------
-- 1. A marca de bancada
-- ---------------------------------------------------------------------
alter table public.sleep_data
    add column if not exists bancada boolean not null default false;

comment on column public.sleep_data.bancada is
    'DATA-16. Marcada pelo titular como bancada/teste: continua guardada, mas '
    'sai do Historico, do painel, do CSV, das features e da inferencia. So muda '
    'por marcar_trecho(); nasce false.';

-- ---------------------------------------------------------------------
-- 2. A janela aceita
-- ---------------------------------------------------------------------
create or replace function public._conferir_trecho(
    p_device uuid,
    p_desde  timestamptz,
    p_ate    timestamptz
)
returns void
language plpgsql
immutable
set search_path = ''
as $$
begin
    if p_device is null or p_desde is null or p_ate is null then
        raise exception using errcode = 'invalid_parameter_value',
            message = 'trecho_incompleto';
    end if;
    if p_ate < p_desde then
        raise exception using errcode = 'invalid_parameter_value',
            message = 'trecho_invertido';
    end if;
    if p_ate - p_desde > interval '48 hours' then
        raise exception using errcode = 'invalid_parameter_value',
            message = 'trecho_acima_de_48h';
    end if;
end;
$$;

-- ---------------------------------------------------------------------
-- 3. Excluir um trecho
-- ---------------------------------------------------------------------
create or replace function public.apagar_trecho(
    p_device uuid,
    p_desde  timestamptz,
    p_ate    timestamptz
)
returns bigint
language plpgsql
volatile
security definer
set search_path = ''
as $$
declare
    v_dono uuid := auth.uid();
    v_n    bigint;
begin
    if v_dono is null then
        return null;
    end if;
    perform public._conferir_trecho(p_device, p_desde, p_ate);

    delete from public.sleep_data
     where user_id = v_dono
       and device_id = p_device
       and coalesce(captured_at, created_at) between p_desde and p_ate;
    get diagnostics v_n = row_count;
    return v_n;
end;
$$;

comment on function public.apagar_trecho(uuid, timestamptz, timestamptz) is
    'DATA-16. Apaga as epocas do titular (auth.uid()) num aparelho, entre dois '
    'instantes (coalesce(captured_at, created_at)), ate 48 h. Devolve quantas.';

-- ---------------------------------------------------------------------
-- 4. Marcar e desmarcar um trecho
-- ---------------------------------------------------------------------
create or replace function public.marcar_trecho(
    p_device  uuid,
    p_desde   timestamptz,
    p_ate     timestamptz,
    p_bancada boolean
)
returns bigint
language plpgsql
volatile
security definer
set search_path = ''
as $$
declare
    v_dono uuid := auth.uid();
    v_n    bigint;
begin
    if v_dono is null then
        return null;
    end if;
    perform public._conferir_trecho(p_device, p_desde, p_ate);
    if p_bancada is null then
        raise exception using errcode = 'invalid_parameter_value',
            message = 'marca_ausente';
    end if;

    update public.sleep_data
       set bancada = p_bancada
     where user_id = v_dono
       and device_id = p_device
       and coalesce(captured_at, created_at) between p_desde and p_ate;
    get diagnostics v_n = row_count;
    return v_n;
end;
$$;

comment on function public.marcar_trecho(uuid, timestamptz, timestamptz, boolean) is
    'DATA-16. Marca (true) ou desmarca (false) como bancada as epocas do '
    'titular num aparelho, entre dois instantes, ate 48 h. Devolve quantas.';

-- ---------------------------------------------------------------------
-- 5. Quem executa o quê
--    Os privilégios padrão do Supabase dão EXECUTE a todos em função nova.
--    Tudo sai; as duas operações voltam só para `authenticated`.
-- ---------------------------------------------------------------------
revoke all on function public._conferir_trecho(uuid, timestamptz, timestamptz) from public;
revoke all on function public.apagar_trecho(uuid, timestamptz, timestamptz) from public;
revoke all on function public.marcar_trecho(uuid, timestamptz, timestamptz, boolean) from public;
do $$
declare
    papel text;
begin
    foreach papel in array array['anon', 'authenticated', 'service_role', 'dormio_ingestao'] loop
        if exists (select 1 from pg_roles where rolname = papel) then
            execute format('revoke all on function public._conferir_trecho(uuid, timestamptz, timestamptz) from %I', papel);
            execute format('revoke all on function public.apagar_trecho(uuid, timestamptz, timestamptz) from %I', papel);
            execute format('revoke all on function public.marcar_trecho(uuid, timestamptz, timestamptz, boolean) from %I', papel);
        end if;
    end loop;
    if exists (select 1 from pg_roles where rolname = 'authenticated') then
        grant execute on function public.apagar_trecho(uuid, timestamptz, timestamptz) to authenticated;
        grant execute on function public.marcar_trecho(uuid, timestamptz, timestamptz, boolean) to authenticated;
    end if;
end $$;

commit;
