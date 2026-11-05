-- =====================================================================
-- 012_idade_minima_18.sql — LGPD-05 e LGPD-06
-- =====================================================================
-- O QUE MUDA
--
-- 1. O serviço passou a ser destinado só a maiores de 18 anos (seção 2.1 da
--    política de privacidade, revisão de 03/11/2026). A restrição de
--    `profiles.idade`, que vinha da 001 (`idade >= 0 and idade < 150`), passa
--    a `idade >= 18 and idade < 150`. O frontend (`lib/perfil.ts`) e o backend
--    (`perfil.py`) já recusam abaixo de 18 com mensagem; esta é a última
--    camada, a que vale mesmo para quem escreve direto no banco.
-- 2. O comentário da coluna passa a declarar as DUAS finalidades da idade: a
--    frase de aplicabilidade (desde 17/10) e a contagem agregada por faixa
--    (`CONSULTA-publico-por-faixa.sql`, desde 03/11). A política foi
--    atualizada antes deste arquivo — a ordem que o LGPD-06 exige.
--
-- A TRAVA
--
-- Antes de trocar a restrição, CONFERE se há perfil com idade abaixo de 18.
-- Se houver, PARA com a contagem: não apaga nem altera dado para conseguir
-- aplicar. O que fazer com esses perfis é decisão de quem trata o dado, não
-- desta migração.
--
-- A restrição antiga não tem nome escrito na 001 (o Postgres a chamou de
-- `profiles_idade_check`), e um banco criado por outro caminho poderia tê-la
-- com outro nome. Por isso são removidas TODAS as restrições `check` de
-- `profiles` que citam `idade`, exceto a nova. Idempotente: pode rodar duas
-- vezes. O backend e o frontend mudam junto: precisa de release.
-- =====================================================================

begin;

do $$
declare
    n integer;
    r record;
begin
    select count(*) into n
      from public.profiles
     where idade is not null and idade < 18;
    if n > 0 then
        raise exception 'LGPD-05: % perfil(is) com idade abaixo de 18. A migracao nao altera nem apaga dado; decida o que fazer com eles antes de aplica-la.', n;
    end if;

    for r in
        select conname
          from pg_constraint
         where conrelid = 'public.profiles'::regclass
           and contype = 'c'
           and pg_get_constraintdef(oid) ilike '%idade%'
           and conname <> 'profiles_idade_maioridade'
    loop
        execute format('alter table public.profiles drop constraint %I', r.conname);
    end loop;
end $$;

alter table public.profiles drop constraint if exists profiles_idade_maioridade;
alter table public.profiles
    add constraint profiles_idade_maioridade
    check (idade is null or (idade >= 18 and idade < 150));

comment on column public.profiles.idade is
    'Idade autodeclarada, OPCIONAL, a partir de 18 anos (o servico e so para '
    'maiores de idade, LGPD-05). Duas finalidades declaradas na secao 3 da '
    'politica de privacidade: (1) dizer ao titular se a idade dele esta dentro '
    'ou fora da faixa das coortes de validacao citadas no trabalho (ver '
    'frontend/src/lib/aplicabilidade.ts); (2) desde 03/11/2026, conhecer o '
    'perfil etario do publico SO DE FORMA AGREGADA, por contagem por faixa com '
    'supressao de faixas pequenas (CONSULTA-publico-por-faixa.sql), nunca '
    'pessoa a pessoa. NAO entra em calculo nenhum: nao pondera metrica, nao '
    'altera limiar, nao estratifica serie, nao alimenta modelo.';

commit;
