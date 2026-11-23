-- LGPD-15 (22/11/2026): a versão nova do texto do consentimento.
--
-- O texto da tela (`frontend/src/lib/consentimento.ts`) passou a dizer
-- "O Smart Dormio", a grafia do manual da marca, e a citar a exclusão de uma
-- sessão pelo Histórico (DATA-16). Mudar o texto é mudar a versão nos três
-- lugares (017, item 2): esta migração troca só a do banco. Quem aceitou a
-- versão `2026-11-10` passa a não ter consentimento vigente e vê a tela de
-- novo; até aceitar, a gravação pela sessão e o pareamento recusam, como
-- sempre (017, item 5).
--
-- ⚠️ ORDEM: aplicar DEPOIS do deploy do backend e do frontend com
-- `2026-11-22`. Antes dele, o site em produção ainda manda `2026-11-10`, e o
-- aceite seria recusado. O app Android leva a tela dentro do APK: quem estiver
-- num APK anterior ao 1.1.2 não consegue aceitar a versão nova até atualizar.
--
-- Idempotente: reaplicar não muda nada.

begin;

create or replace function public.versao_do_consentimento()
returns text
language sql
immutable
set search_path = ''
as $$ select '2026-11-22'::text $$;

revoke all on function public.versao_do_consentimento() from public;
grant execute on function public.versao_do_consentimento() to authenticated;

commit;
