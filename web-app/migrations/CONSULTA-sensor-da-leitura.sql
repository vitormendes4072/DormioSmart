-- DATA-18. Rodar depois da 028. As quatro conferências devem ser true.
select
    exists (select 1 from information_schema.columns
             where table_schema = 'public' and table_name = 'sleep_data'
               and column_name = 'sensor' and data_type = 'text' and is_nullable = 'YES') as coluna_anulavel,
    coalesce((select convalidated and pg_get_constraintdef(oid) like all
                     (array['%MPU6050%', '%MPU6500%', '%desconhecido%'])
                from pg_constraint
               where conrelid = to_regclass('public.sleep_data')
                 and conname = 'sleep_data_sensor_valido'), false) as restricao_validada,
    coalesce(pg_get_functiondef(to_regprocedure('public.registrar_leitura(text,jsonb)'))
             like '%p_leitura ->> ''sensor''%', false) as token_le_o_chip,
    coalesce(pg_get_functiondef(to_regprocedure('public.registrar_leitura_da_sessao(uuid,jsonb)'))
             like ('%calibrada, sensor,%null,' || chr(10) || '        v_dono%'), false) as sessao_grava_nulo;
