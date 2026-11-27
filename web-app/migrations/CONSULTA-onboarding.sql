-- LGPD-16, finalidade 9. Somente leitura, fuso America/Sao_Paulo.
-- Duração declarada da época, sem estimar duração ausente. Intervalos
-- sobrepostos de aparelhos da mesma conta contam uma vez. O dia é civil.
with contas as (
    select id, created_at,
           date_trunc('week', created_at at time zone 'America/Sao_Paulo')::date as semana
      from auth.users
), semanas as (
    select semana from contas group by semana having count(*) >= 5
), registros as (
    select c.id, c.created_at, coalesce(d.captured_at, d.created_at) as inicio, d.epoca_segundos
      from contas c join semanas s using (semana)
      join public.sleep_data d on d.user_id = c.id
     where d.bancada is not true
       and coalesce(d.captured_at, d.created_at) >= c.created_at
), primeiro as (
    select id, min(inicio) as instante from registros group by id
), cobertura as (
    select id, range_agg(tstzrange(inicio, inicio + epoca_segundos * interval '1 second')) as trechos
      from registros where epoca_segundos > 0 group by id
), dias as (
    select id, dia::date as data,
           sum(least(upper(trecho), (dia + interval '1 day') at time zone 'America/Sao_Paulo')
                - greatest(lower(trecho), dia at time zone 'America/Sao_Paulo')) as duracao
      from cobertura
      cross join lateral unnest(trechos) as trecho
      cross join lateral generate_series(
           date_trunc('day', lower(trecho) at time zone 'America/Sao_Paulo'),
           date_trunc('day', (upper(trecho) - interval '1 microsecond') at time zone 'America/Sao_Paulo'),
           interval '1 day') as dia
     group by id, dia::date
), mais_de_quatro as (
    select distinct id from dias where duracao > interval '4 hours'
)
select c.semana, count(*) as contas_criadas,
       count(*) filter (where p.instante <= c.created_at + interval '168 hours') as primeiro_registro_em_7_dias,
       count(q.id) as contas_com_dia_acima_de_4h
  from contas c join semanas s using (semana)
  left join primeiro p on p.id = c.id
  left join mais_de_quatro q on q.id = c.id
 group by c.semana order by c.semana;
