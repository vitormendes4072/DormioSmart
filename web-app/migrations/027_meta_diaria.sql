-- UI-61: meta de minutos registrados por dia escolhida pelo titular.
-- O UPDATE de tabela de authenticated já alcança a coluna. O RLS de
-- profiles continua limitando SELECT e UPDATE à linha da própria conta.
begin;

alter table public.profiles
    add column if not exists meta_diaria_min integer;

alter table public.profiles
    drop constraint if exists profiles_meta_diaria_faixa;
alter table public.profiles
    add constraint profiles_meta_diaria_faixa check (meta_diaria_min between 60 and 960);

comment on column public.profiles.meta_diaria_min is
    'Meta de tempo registrado por dia escolhida pelo titular, em minutos. Nulo significa sem meta.';

commit;
