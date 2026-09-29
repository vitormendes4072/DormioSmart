-- =====================================================================
-- 006_direito_de_eliminacao.sql — SEC-07 (LGPD art. 18, VI)
--
-- Até aqui o titular não tinha caminho nenhum para apagar o próprio dado.
-- `sleep_data` e `profiles` têm RLS com policies de select/insert/update, mas
-- NENHUMA de delete — e, com o RLS ativo, ausência de policy é negativa. O
-- efeito era que nem o dono conseguia eliminar o que era dele, por rota, por
-- SQL, por caminho algum.
--
-- Isso protegia o histórico contra apagamento acidental, e foi assim que
-- passou despercebido: o comportamento parecia uma decisão de integridade. Mas
-- a Lei 13.709/2018, art. 18, VI, dá ao titular o direito de eliminação do dado
-- pessoal tratado com base no consentimento — que é exatamente a base deste
-- trabalho. Um sistema de dado de sono sem esse caminho está incompleto.
--
-- ---------------------------------------------------------------------
-- ELIMINAÇÃO DE FATO, NÃO ANONIMIZAÇÃO
-- ---------------------------------------------------------------------
--
-- Optou-se por DELETE, e não por desvincular a linha do dono (`user_id` a
-- nulo). Anonimizar seria mais conveniente para a pesquisa — o dado
-- permaneceria no conjunto — mas dado de acelerometria noturna de uma pessoa
-- específica, com carimbo de tempo, não é razoavelmente anonimizável: a série
-- temporal é ela mesma um identificador quando cruzada com qualquer outra
-- fonte. Chamar isso de anonimização seria impreciso, e a LGPD trata dado
-- pseudonimizado como dado pessoal (art. 13, §4º). Então apaga.
--
-- Efeito colateral aceito de propósito: a linha órfã que o desvínculo criaria
-- é justamente o problema que o DATA-03 existe para consertar. Não faria
-- sentido introduzir mais delas pela porta da frente.
--
-- ---------------------------------------------------------------------
-- TRÊS GRANULARIDADES, TRÊS MECANISMOS
-- ---------------------------------------------------------------------
--
--   1. Uma leitura, ou um recorte delas -> policy `sleep_data_delete_own`
--   2. Um dispositivo                   -> já existia (`devices_delete_own`)
--   3. A conta inteira                  -> função `apagar_minha_conta()`
--
-- O (3) não pode ser policy: apagar a conta significa apagar a linha de
-- `auth.users`, que é gerenciada pelo Supabase e não aceita policy nossa. E
-- precisa ser uma operação só, atômica, na ordem certa das chaves estrangeiras.
--
-- ORDEM DAS EXCLUSÕES, e por que ela importa:
--
--   sleep_data -> devices -> profiles -> auth.users
--
-- `sleep_data.device_id` referencia `devices(id) on delete set null`. Apagar
-- `devices` primeiro faria o banco percorrer todas as leituras zerando
-- `device_id` — trabalho jogado fora, já que elas serão apagadas em seguida.
-- Mais relevante: se a exclusão fosse interrompida no meio, o estado
-- intermediário seria leitura sem dispositivo, que é pior que leitura nenhuma.
--
-- ---------------------------------------------------------------------
-- A PARTE QUE PODE NÃO FUNCIONAR NO SEU PROJETO — leia antes de aplicar
-- ---------------------------------------------------------------------
--
-- `auth.users` pertence a `supabase_auth_admin`, não a `postgres`. Se o
-- `postgres` do seu projeto não tiver DELETE nela, a função apaga TODO o dado
-- pessoal em `public` e devolve `conta_de_acesso_removida: false` — sem
-- levantar erro e sem fingir sucesso.
--
-- O que sobra nesse caso é a linha de `auth.users`: e-mail e data de criação.
-- É dado pessoal, então a eliminação fica INCOMPLETA, e a rota diz isso ao
-- usuário em vez de esconder. Conserto, em ordem de preferência:
--
--   a) rodar o bloco 4 abaixo, que tenta conceder o DELETE ao `postgres`;
--   b) se (a) não passar, apagar o usuário pelo painel
--      (Authentication > Users > ... > Delete user) ou pela Admin API
--      (`DELETE /auth/v1/admin/users/{id}` com a service_role). É manual, e o
--      procedimento está em `web-app/README.md`.
--
-- Não se tentou contornar isso chamando a Admin API do backend: seria
-- reintroduzir a service_role num caminho de usuário, exatamente o que a
-- SEC-06 acabou de remover.
--
-- Idempotente: pode rodar mais de uma vez sem efeito adicional.
-- =====================================================================

begin;

-- ---------------------------------------------------------------------
-- 1. sleep_data — o titular apaga a própria leitura
--
--    NOTE O QUE *NÃO* FOI ACRESCENTADO: policy de update. Eliminar e reescrever
--    são coisas diferentes. O titular tem direito a tirar o dado da base; não
--    existe direito a alterar uma medição para que ela diga outra coisa, e
--    permitir isso destruiria o valor probatório de todo o conjunto. Apagar é
--    visível (a linha sai); editar é invisível.
-- ---------------------------------------------------------------------
drop policy if exists sleep_data_delete_own on public.sleep_data;
create policy sleep_data_delete_own on public.sleep_data
    for delete to authenticated using (user_id = (select auth.uid()));

-- ---------------------------------------------------------------------
-- 2. profiles — o titular apaga o próprio perfil
--
--    Atenção ao estado que isto permite: perfil apagado com `auth.users` ainda
--    de pé significa conta que loga e não tem nome nem idade. O trigger
--    `on_auth_user_created` é `after insert`, então ele não recria nada.
--    Por isso a rota `DELETE /api/me` usa a função do bloco 3, que apaga os
--    dois — esta policy existe para o caso granular e para que
--    `apagar_minha_conta` não precise ser a única porta.
-- ---------------------------------------------------------------------
drop policy if exists profiles_delete_own on public.profiles;
create policy profiles_delete_own on public.profiles
    for delete to authenticated using (id = (select auth.uid()));

-- ---------------------------------------------------------------------
-- 3. apagar_minha_conta() — a eliminação completa, numa transação
--
--    `security definer` por um motivo só: `auth.users`. Todo o resto ela faria
--    com o privilégio do próprio usuário, via as policies acima.
--
--    O dono vem de `auth.uid()` e de nenhum outro lugar. NÃO HÁ PARÂMETRO:
--    é a diferença entre "apagar minha conta" e "apagar uma conta". Um
--    `p_user_id` aqui transformaria um JWT válido qualquer numa arma contra
--    qualquer outra conta — e seria trivial de escrever por engano.
--
--    Devolve o que foi apagado, em jsonb, para que a rota possa confirmar e
--    para que o usuário receba um recibo do que deixou de existir.
-- ---------------------------------------------------------------------
create or replace function public.apagar_minha_conta()
returns jsonb
language plpgsql
volatile
security definer
set search_path = ''
as $$
declare
    v_dono      uuid := auth.uid();
    v_leituras  bigint;
    v_devices   bigint;
    v_perfis    bigint;
    v_conta     boolean := false;
begin
    -- Sem sessão não há conta a apagar. Retorno nulo, não exceção: a rota
    -- traduz para 401 e uma exceção aqui viraria 500.
    if v_dono is null then
        return null;
    end if;

    -- Ordem ditada pelas chaves estrangeiras — ver o cabeçalho.
    delete from public.sleep_data where user_id = v_dono;
    get diagnostics v_leituras = row_count;

    delete from public.devices where user_id = v_dono;
    get diagnostics v_devices = row_count;

    delete from public.profiles where id = v_dono;
    get diagnostics v_perfis = row_count;

    -- A linha de `auth.users` carrega o e-mail, que também é dado pessoal.
    -- Pode falhar por privilégio (ver o cabeçalho); nesse caso a eliminação
    -- do que está em `public` JÁ ACONTECEU e não é desfeita — o titular fica
    -- melhor com a maior parte apagada do que com nada, e a rota informa o
    -- que sobrou em vez de mentir sucesso completo.
    begin
        delete from auth.users where id = v_dono;
        v_conta := true;
    exception when insufficient_privilege or undefined_table then
        v_conta := false;
    end;

    return jsonb_build_object(
        'leituras_apagadas',          v_leituras,
        'dispositivos_apagados',      v_devices,
        'perfil_apagado',             v_perfis > 0,
        'conta_de_acesso_removida',   v_conta
    );
end;
$$;

comment on function public.apagar_minha_conta() is
    'LGPD art. 18, VI. Apaga todo o dado pessoal do titular de auth.uid(). '
    'SEM PARAMETRO de proposito: apaga a propria conta, nunca a de outro.';

revoke all on function public.apagar_minha_conta() from public;
grant execute on function public.apagar_minha_conta() to authenticated;

-- ---------------------------------------------------------------------
-- 4. Tentativa de conceder DELETE em auth.users ao dono da função
--
--    Condicional e tolerante a falha de propósito: em muitos projetos o
--    `postgres` não pode conceder privilégio numa tabela de
--    `supabase_auth_admin`. Se não der, a migração NÃO falha — a função já
--    trata o caso e reporta. Ver o cabeçalho para o conserto manual.
-- ---------------------------------------------------------------------
do $$
begin
    execute format(
        'grant delete on auth.users to %I', current_user
    );
    raise notice 'DELETE em auth.users concedido a %. Eliminacao completa.', current_user;
exception when others then
    raise notice
        'Nao foi possivel conceder DELETE em auth.users a % (%). A funcao '
        'apagara o dado de public e devolvera conta_de_acesso_removida=false; '
        'a linha de auth.users precisara ser removida pelo painel. Ver o '
        'cabecalho desta migracao.',
        current_user, sqlerrm;
end $$;

commit;

-- =====================================================================
-- VERIFICAÇÃO — rodar depois do commit
-- =====================================================================
--
-- 1. As policies de delete existem (esperado: 3 -- profiles, devices, sleep_data)
--
-- select tablename, policyname from pg_policies
--  where schemaname = 'public' and cmd = 'DELETE' order by tablename;
--
-- 2. A função existe, é definer e não tem parâmetro (esperado: 1 linha, f, vazio)
--
-- select p.proname, p.prosecdef, pg_get_function_identity_arguments(p.oid)
--   from pg_proc p join pg_namespace n on n.oid = p.pronamespace
--  where n.nspname = 'public' and p.proname = 'apagar_minha_conta';
--
-- 3. `anon` NAO alcanca a funcao (esperado: false)
--
-- select has_function_privilege('anon', 'public.apagar_minha_conta()', 'execute');
--
-- 4. O dono da funcao consegue apagar de auth.users? (esperado: true; se false,
--    a eliminacao fica incompleta -- ver o cabecalho)
--
-- select has_table_privilege(
--     (select pg_get_userbyid(proowner) from pg_proc p
--       join pg_namespace n on n.oid = p.pronamespace
--      where n.nspname = 'public' and p.proname = 'apagar_minha_conta'),
--     'auth.users', 'delete');
-- =====================================================================
