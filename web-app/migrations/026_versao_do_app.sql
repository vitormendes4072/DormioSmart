-- APP-19: a versão do app Android que o celular informou, para contar quantas
-- pessoas têm cada versão instalada e avisar quem ficou para trás.
--
-- O app (desde a 1.1.4) manda a versão no `POST /api/devices/celular`, que já
-- é chamado a cada envio de noite. O servidor grava aqui, pelo cliente do
-- titular, sob o RLS de `devices` (só o dono altera a própria linha). O site
-- não manda versão, e a coluna fica nula; o app até a 1.1.3 também não.
--
-- Dado técnico do aparelho, sem nada sobre o sono (política, §2.2). A contagem
-- é agregada, por `web-app/migrations/CONSULTA-versoes-do-app.sql`.
begin;

alter table public.devices
    add column if not exists versao_app text,
    add column if not exists versao_vista_em timestamptz;

alter table public.devices drop constraint if exists devices_versao_app_formato;
alter table public.devices add constraint devices_versao_app_formato check (
    versao_app is null
    or (versao_app ~ '^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$' and versao_vista_em is not null)
);

comment on column public.devices.versao_app is
    'APP-19: versão do app Android informada pelo aparelho (MAJOR.MINOR.PATCH); nula no site e no app até a 1.1.3.';
comment on column public.devices.versao_vista_em is
    'APP-19: quando o aparelho informou a versão pela última vez.';

commit;
