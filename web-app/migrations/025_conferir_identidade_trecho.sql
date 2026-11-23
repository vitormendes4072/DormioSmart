-- DATA-17: a identidade da sessão é SHA-256 dos UUIDs canônicos em minúsculas,
-- ordenados como UUID, unidos por vírgula sem espaços nem vírgula final,
-- codificados em UTF-8 e representados por 64 dígitos hexadecimais minúsculos.
-- A mutação usa apenas os IDs travados: uma inserção posterior não é atingida.
begin;
drop function if exists public.apagar_trecho(uuid, timestamptz, timestamptz);
drop function if exists public.marcar_trecho(uuid, timestamptz, timestamptz, boolean);

create or replace function public._ids_trecho(
    p_device uuid, p_desde timestamptz, p_ate timestamptz,
    p_epocas_esperadas bigint, p_bancada_atual boolean, p_impressao_ids text
) returns uuid[] language plpgsql volatile set search_path = '' as $$
declare
    v_ids uuid[] := array[]::uuid[];
    v_linha record;
    v_diferentes bigint := 0;
begin
    perform public._conferir_trecho(p_device, p_desde, p_ate);
    if p_epocas_esperadas is null or p_epocas_esperadas < 0 or p_bancada_atual is null
       or p_impressao_ids is null or p_impressao_ids !~ '^[0-9a-f]{64}$' then
        raise exception using errcode = '22023', message = 'conferencia_invalida';
    end if;
    for v_linha in
        select id, bancada from public.sleep_data
        where user_id = auth.uid() and device_id = p_device
          and coalesce(captured_at, created_at) between p_desde and p_ate
        order by id for update
    loop
        v_ids := pg_catalog.array_append(v_ids, v_linha.id);
        if v_linha.bancada is distinct from p_bancada_atual then
            v_diferentes := v_diferentes + 1;
        end if;
    end loop;
    if pg_catalog.cardinality(v_ids) <> p_epocas_esperadas or v_diferentes <> 0
       or pg_catalog.encode(pg_catalog.sha256(pg_catalog.convert_to(pg_catalog.array_to_string(v_ids, ','), 'UTF8')), 'hex') <> p_impressao_ids then
        raise exception using errcode = 'P0001', message = 'trecho_divergente';
    end if;
    return v_ids;
end; $$;

create or replace function public.apagar_trecho(
    p_device uuid, p_desde timestamptz, p_ate timestamptz,
    p_epocas_esperadas bigint, p_bancada_atual boolean, p_impressao_ids text
) returns bigint language plpgsql volatile security definer set search_path = '' as $$
declare v_ids uuid[]; v_n bigint;
begin
    if auth.uid() is null then return null; end if;
    v_ids := public._ids_trecho(p_device, p_desde, p_ate, p_epocas_esperadas, p_bancada_atual, p_impressao_ids);
    delete from public.sleep_data where id = any(v_ids) and user_id = auth.uid();
    get diagnostics v_n = row_count; return v_n;
end; $$;

create or replace function public.marcar_trecho(
    p_device uuid, p_desde timestamptz, p_ate timestamptz, p_bancada boolean,
    p_epocas_esperadas bigint, p_bancada_atual boolean, p_impressao_ids text
) returns bigint language plpgsql volatile security definer set search_path = '' as $$
declare v_ids uuid[]; v_n bigint;
begin
    if auth.uid() is null then return null; end if;
    if p_bancada is null then raise exception using errcode = '22023', message = 'marca_ausente'; end if;
    v_ids := public._ids_trecho(p_device, p_desde, p_ate, p_epocas_esperadas, p_bancada_atual, p_impressao_ids);
    update public.sleep_data set bancada = p_bancada where id = any(v_ids) and user_id = auth.uid();
    get diagnostics v_n = row_count; return v_n;
end; $$;

revoke all on function public._ids_trecho(uuid,timestamptz,timestamptz,bigint,boolean,text) from public;
revoke all on function public.apagar_trecho(uuid,timestamptz,timestamptz,bigint,boolean,text) from public;
revoke all on function public.marcar_trecho(uuid,timestamptz,timestamptz,boolean,bigint,boolean,text) from public;
do $$ declare papel text; begin
    foreach papel in array array['anon','authenticated','service_role','dormio_ingestao'] loop
        if exists (select 1 from pg_catalog.pg_roles where rolname = papel) then
            execute pg_catalog.format('revoke all on function public._ids_trecho(uuid,timestamptz,timestamptz,bigint,boolean,text) from %I', papel);
            execute pg_catalog.format('revoke all on function public.apagar_trecho(uuid,timestamptz,timestamptz,bigint,boolean,text) from %I', papel);
            execute pg_catalog.format('revoke all on function public.marcar_trecho(uuid,timestamptz,timestamptz,boolean,bigint,boolean,text) from %I', papel);
        end if;
    end loop;
    if exists (select 1 from pg_catalog.pg_roles where rolname = 'authenticated') then
        grant execute on function public.apagar_trecho(uuid,timestamptz,timestamptz,bigint,boolean,text) to authenticated;
        grant execute on function public.marcar_trecho(uuid,timestamptz,timestamptz,boolean,bigint,boolean,text) to authenticated;
    end if;
end $$;
commit;
