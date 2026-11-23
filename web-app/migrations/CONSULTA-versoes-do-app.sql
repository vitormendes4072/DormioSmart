-- =====================================================================
-- CONSULTA-versoes-do-app.sql — APP-19 (23/11/2026)
-- =====================================================================
-- SÓ LEITURA. Para rodar no SQL Editor do Supabase, depois da migração 026.
--
-- É a forma DECLARADA de usar a finalidade 7 da política de privacidade
-- (seção 3): saber quantos celulares há com cada versão do app Android.
--
--   * Conta os celulares ativos (não revogados) por versão informada.
--   * "Ativo nos últimos 30 dias": a última vez que o aparelho informou a
--     versão ou, sem versão, a última leitura que ele enviou.
--   * "sem versão" junta o app até a 1.1.3, que não informa a versão, e o
--     celular usado só pelo site. As duas não se distinguem pelo banco.
--   * Não lista aparelhos nem contas, e não cruza com medições: só contagens.
--
-- Os downloads de cada APK ficam no GitHub, não aqui:
--   gh api repos/<dono>/<repositorio>/releases --jq '.[] | [.tag_name, .assets[0].download_count]'
-- =====================================================================

with celulares as (
    select d.versao_app,
           coalesce(d.versao_vista_em,
                    (select max(s.created_at) from public.sleep_data s where s.device_id = d.id))
               as ultima_atividade
    from public.devices d
    where d.tipo = 'celular' and d.revoked_at is null
)
select coalesce(versao_app, 'sem versão (1.1.3 ou anterior, ou o site)') as versao,
       count(*) filter (where ultima_atividade >= now() - interval '30 days') as ativos_30_dias,
       count(*) filter (where ultima_atividade < now() - interval '30 days'
                           or ultima_atividade is null)                   as mais_antigos,
       count(*)                                                           as total
from celulares
group by versao_app
order by versao_app is null,
         string_to_array(versao_app, '.')::int[] desc;
