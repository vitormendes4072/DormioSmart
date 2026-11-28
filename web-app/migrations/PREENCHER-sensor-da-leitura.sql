-- DATA-18. Executar manualmente depois da 028.
-- Confirme os três UUIDs em public.devices. A prévia mostra nome e contagem.
-- Rode inteiro com aplicar = false primeiro. Após conferir a saída, troque
-- para true e rode inteiro de novo. Valores de sensor já gravados são preservados.
begin;

create temporary table preenchimento_sensor (
    referencia text not null,
    device_id uuid primary key,
    sensor text not null
) on commit drop;

insert into preenchimento_sensor values
    ('travesseiro', null, 'MPU6050'),
    ('bancada a434', null, 'MPU6500'),
    ('bancada 68c0', null, 'MPU6500');

do $$
begin
    if exists (
        select 1 from preenchimento_sensor p
          left join public.devices d on d.id = p.device_id
         where d.tipo is distinct from 'travesseiro'
    ) then
        raise exception 'Os três UUIDs precisam identificar dispositivos do tipo travesseiro';
    end if;
end;
$$;

-- Prévia por aparelho. Já classificados e classificações divergentes são
-- contados para conferência e ficam fora da atualização.
select p.referencia, p.device_id, d.nome, p.sensor as chip_confirmado,
       count(s.id) filter (where s.sensor is null) as a_preencher,
       count(s.id) filter (where s.sensor = p.sensor) as ja_com_o_chip,
       count(s.id) filter (where s.sensor <> p.sensor) as outros_valores
  from preenchimento_sensor p join public.devices d on d.id = p.device_id
  left join public.sleep_data s on s.device_id = p.device_id
 group by p.referencia, p.device_id, d.nome, p.sensor order by p.referencia;

-- Troque false por true só depois de conferir os UUIDs e as contagens.
with modo as (select false as aplicar), atualizadas as (
    update public.sleep_data s set sensor = p.sensor
      from preenchimento_sensor p cross join modo m
     where m.aplicar and s.device_id = p.device_id and s.sensor is null
    returning s.device_id
)
select p.referencia, count(a.device_id) as preenchidas
  from preenchimento_sensor p left join atualizadas a on a.device_id = p.device_id
 group by p.referencia order by p.referencia;

-- Conferência depois da atualização. Com aplicar = true, o esperado é
-- que a contagem sem chip dos três aparelhos chegue a zero.
select p.referencia, p.device_id, p.sensor as chip_confirmado,
       count(s.id) filter (where s.sensor = p.sensor) as com_o_chip,
       count(s.id) filter (where s.sensor is null) as sem_chip,
       count(s.id) filter (where s.sensor <> p.sensor) as outros_valores
  from preenchimento_sensor p left join public.sleep_data s on s.device_id = p.device_id
 group by p.referencia, p.device_id, p.sensor order by p.referencia;

commit;
