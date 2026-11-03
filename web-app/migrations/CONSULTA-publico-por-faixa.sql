-- =====================================================================
-- CONSULTA-publico-por-faixa.sql — LGPD-06 (03/11/2026)
-- =====================================================================
-- SÓ LEITURA. Para rodar no SQL Editor do Supabase.
--
-- É a forma DECLARADA de usar a segunda finalidade da idade (seção 3, item 5,
-- e seção 5.3 da política de privacidade): conhecer o perfil etário de quem
-- usa o sistema, apenas por contagem agregada.
--
--   * Conta contas por faixa: 18 a 24, 25 a 34, 35 a 44, 45 a 54, 55 a 64,
--     65 ou mais, e "não informada".
--   * Faixa com MENOS DE 5 contas aparece como "menos de 5", e não com o
--     número: com poucas pessoas numa faixa, a contagem identificaria alguém.
--   * NÃO há linha de total, de propósito: com o total, uma faixa suprimida
--     seria recuperável por subtração.
--   * Não cruza com medições nem com nenhum outro dado.
--
-- O QUE ELA NÃO GARANTE, E É DECLARADO: o administrador tem acesso técnico ao
-- banco e poderia ler a coluna diretamente. A proteção é de procedimento — esta
-- é a consulta que a política autoriza —, não de permissão.
-- =====================================================================

with faixas(faixa, ordem, minimo, maximo) as (
    values ('18 a 24', 1, 18, 24),
           ('25 a 34', 2, 25, 34),
           ('35 a 44', 3, 35, 44),
           ('45 a 54', 4, 45, 54),
           ('55 a 64', 5, 55, 64),
           ('65 ou mais', 6, 65, 149)
),
contagem as (
    select f.faixa, f.ordem, count(p.id) as contas
      from faixas f
      left join public.profiles p on p.idade between f.minimo and f.maximo
     group by f.faixa, f.ordem
    union all
    select 'não informada', 7, count(*) from public.profiles where idade is null
)
select faixa,
       case when contas < 5 then 'menos de 5' else contas::text end as contas
  from contagem
 order by ordem;
