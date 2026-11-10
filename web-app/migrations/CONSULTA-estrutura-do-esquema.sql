-- =====================================================================
-- CONSULTA-estrutura-do-esquema.sql — DATA-12 (só leitura)
--
-- Lista a estrutura do schema `public` da produção: tabelas (RLS e
-- permissões), colunas (tipo, nulo, padrão), funções (argumentos, retorno,
-- definer, search_path, permissões), restrições e índices. Só catálogo,
-- nenhum dado de usuário.
--
-- PARA QUÊ: comparar com `tests/rls/esquema_base.sql` + as migrações, que
-- imitam a produção de memória. Em 09/11 essa comparação achou o id como
-- `bigserial` no teste e uuid na produção (DATA-10) e, depois, `user_id`
-- sem cascata na produção (DATA-12). Rodar de novo ao mexer em função que
-- grava ou lê coluna, e depois de cada migração aplicada.
--
-- COMO: SQL Editor, copiar o resultado como JSON e comparar com a mesma
-- consulta num Postgres de teste montado na ordem real das migrações.
-- =====================================================================
select tipo, objeto, detalhe from (
    -- tabelas
    select 1 as ordem, 'tabela' as tipo, c.relname::text as objeto,
           'rls=' || c.relrowsecurity || ' forcado=' || c.relforcerowsecurity
           || ' acl=' || coalesce(c.relacl::text, 'padrao') as detalhe
      from pg_class c join pg_namespace n on n.oid = c.relnamespace
     where n.nspname = 'public' and c.relkind in ('r', 'p', 'v', 'm')
    union all
    -- colunas
    select 2, 'coluna', c.relname || '.' || a.attname,
           format_type(a.atttypid, a.atttypmod)
           || case when a.attnotnull then ' not null' else '' end
           || coalesce(' default ' || pg_get_expr(d.adbin, d.adrelid), '')
      from pg_attribute a
      join pg_class c on c.oid = a.attrelid
      join pg_namespace n on n.oid = c.relnamespace
      left join pg_attrdef d on d.adrelid = a.attrelid and d.adnum = a.attnum
     where n.nspname = 'public' and c.relkind in ('r', 'p', 'v', 'm')
       and a.attnum > 0 and not a.attisdropped
    union all
    -- funções
    select 3, 'funcao', p.proname || '(' || pg_get_function_identity_arguments(p.oid) || ')',
           'retorna ' || pg_get_function_result(p.oid)
           || case when p.prosecdef then ' definer' else ' invoker' end
           || ' ' || p.provolatile::text
           || coalesce(' config=' || array_to_string(p.proconfig, ','), '')
           || ' acl=' || coalesce(p.proacl::text, 'padrao')
      from pg_proc p join pg_namespace n on n.oid = p.pronamespace
     where n.nspname = 'public'
    union all
    -- restrições
    select 4, 'restricao', c.relname || '.' || k.conname, pg_get_constraintdef(k.oid)
      from pg_constraint k
      join pg_class c on c.oid = k.conrelid
      join pg_namespace n on n.oid = c.relnamespace
     where n.nspname = 'public'
    union all
    -- índices
    select 5, 'indice', i.tablename || '.' || i.indexname, i.indexdef
      from pg_indexes i
     where i.schemaname = 'public'
) t
order by ordem, objeto;
