-- =====================================================================
-- 005_papel_de_ingestao_minimo.sql — SEC-06
--
-- Reduz o privilégio do caminho de ingestão. Até aqui, `POST /api/data`
-- consultava o banco com a `service_role`, que tem `BYPASSRLS` e privilégio
-- total em `public`. O pior caso de um vazamento daquela chave era **ler e
-- reescrever o banco inteiro** — todo o dado de sono de todos os usuários,
-- todos os perfis, todos os dispositivos.
--
-- Depois desta migração, o pior caso passa a ser **inserir lixo em nome de um
-- dispositivo cujo token o atacante já tenha**. Não há leitura de dado de
-- usuário nenhum, não há enumeração de dispositivos, não há escrita em
-- `profiles`, não há delete em lugar algum.
--
-- ---------------------------------------------------------------------
-- O QUE A ROTA PRECISA DE FATO — o levantamento que motivou o desenho
-- ---------------------------------------------------------------------
--
-- Quatro consultas passavam pela `service_role` (`web-app/database.py`):
--
--   1. `verificar_conexao`      select created_at from sleep_data limit 1
--   2. `get_device_by_token_hash`  select id, user_id, revoked_at from devices
--                                   where token_hash = $1
--   3. `insert_sleep_data`      insert into sleep_data (...)
--   4. `touch_device`           update devices set last_seen_at where id = $1
--
-- A tentativa óbvia — criar um papel e dar GRANT de coluna nessas tabelas —
-- NÃO chega onde se quer, por três motivos concretos:
--
--   · (1) exige `select` em `sleep_data`. Privilégio de tabela não distingue
--     linha: conceder select para o health check concede **leitura de todo o
--     dado de sono de todos os usuários**. Exatamente o que se quer eliminar.
--
--   · (2) exige `select (token_hash, id, user_id, revoked_at)` em `devices`.
--     O Postgres exige privilégio nas colunas do WHERE, então `token_hash`
--     entra. Com isso o papel pode **listar o hash do token de todo
--     dispositivo de todo usuário** — o material que o SEC-02 existe para não
--     entregar nem num dump do banco.
--
--   · (3) o INSERT do PostgREST volta com `return=representation` por padrão,
--     e a rota depende do retorno para responder 201 só com gravação
--     confirmada (FIX-02). Retorno exige `select` em `sleep_data` — cai no
--     mesmo problema de (1).
--
-- Ou seja: o caminho por GRANT de tabela obrigaria a ampliar o papel bem além
-- do necessário, e o ganho seria quase nenhum. Então o acesso passa a ser por
-- FUNÇÃO: três funções `security definer` com superfície estreita, e o papel
-- de ingestão recebe **EXECUTE nelas e nada mais**. Zero privilégio de tabela.
--
-- A função resolve o dono a partir do token DENTRO do banco. O chamador não
-- informa `user_id` em nenhuma hipótese — nem podendo, nem por engano. Antes,
-- a garantia de que "o device não escolhe de quem é o dado" era uma linha de
-- Python em `routes.py`; agora é estrutural.
--
-- ---------------------------------------------------------------------
-- O RISCO QUE ISTO INTRODUZ, dito às claras
-- ---------------------------------------------------------------------
--
-- `security definer` roda com o privilégio do DONO da função, não do chamador.
-- É o que permite dar EXECUTE a um papel sem privilégio: a função faz, por
-- ele, exatamente o que está escrito nela. Em troca, **um defeito dentro de
-- uma dessas três funções é um desvio completo do RLS**. Foi por isso que:
--
--   · as três fixam `search_path = ''` e qualificam todo nome (sem isso,
--     quem controlasse o `search_path` escolheria qual função a definer
--     chama — escalada clássica);
--   · `registrar_leitura` extrai coluna por coluna do JSON em vez de usar
--     `jsonb_populate_record`, para que o chamador não consiga escrever numa
--     coluna que não esteja nesta lista;
--   · nenhuma delas devolve dado de sono, perfil, ou `token_hash`;
--   · `tests/rls/test_rls_ingestao.py` exercita cada uma sob o papel real.
--
-- ---------------------------------------------------------------------
-- COMO A CHAVE DESTE PAPEL É EMITIDA
-- ---------------------------------------------------------------------
--
-- O painel do Supabase emite chave para `anon` e `service_role`, e só. Para um
-- papel próprio é preciso um JWT assinado com o **JWT secret do projeto**,
-- carregando `{"role": "dormio_ingestao"}` — o PostgREST faz `SET ROLE` a
-- partir dessa claim. Para isso o papel tem de estar concedido ao
-- `authenticator`, que é quem o PostgREST usa para conectar; é o que o bloco 4
-- faz.
--
-- Ver `web-app/README.md`, seção "Rotação da chave de ingestão", para o
-- procedimento. O script `scripts/emitir_chave_de_ingestao.py` monta o JWT
-- localmente — o segredo do projeto nunca sai da máquina de quem roda.
--
-- Idempotente: pode rodar mais de uma vez sem efeito adicional.
-- =====================================================================

begin;

-- ---------------------------------------------------------------------
-- 1. O papel
--    NOLOGIN: ninguém se conecta como ele. O PostgREST chega por SET ROLE.
--    Sem BYPASSRLS, sem CREATEDB, sem CREATEROLE — e sem nenhum GRANT de
--    tabela em ponto algum desta migração. Confira com o bloco de
--    VERIFICAÇÃO no rodapé.
-- ---------------------------------------------------------------------
do $$
begin
    if not exists (select 1 from pg_roles where rolname = 'dormio_ingestao') then
        create role dormio_ingestao nologin noinherit;
    end if;
end $$;

comment on role dormio_ingestao is
    'Caminho de ingestao (POST /api/data). Apenas EXECUTE em sanidade(), '
    'resolver_dispositivo() e registrar_leitura(). Nenhum privilegio de tabela.';

-- USAGE no schema é o mínimo para alcançar uma função dentro dele. Não dá
-- acesso a tabela nenhuma: cada objeto ainda exige o seu próprio privilégio.
grant usage on schema public to dormio_ingestao;

-- ---------------------------------------------------------------------
-- 2. sanidade() — o health check (WEB-04)
--
--    Substitui o `select ... from sleep_data limit 1`. Confirma credencial,
--    alcance de rede e banco de pé sem tocar em dado nenhum — e por isso NÃO
--    é `security definer`: ela não precisa de privilégio algum. O catálogo do
--    Postgres é legível por qualquer papel.
--
--    Confere também que as três tabelas existem, o que o `select` antigo fazia
--    de carona e seria uma regressão perder: um banco de pé com o schema
--    faltando não é um banco saudável.
-- ---------------------------------------------------------------------
create or replace function public.sanidade()
returns text
language sql
stable
set search_path = ''
as $$
    select case
        when (
            select count(*) from pg_catalog.pg_tables
             where schemaname = 'public'
               and tablename in ('profiles', 'devices', 'sleep_data')
        ) = 3 then 'ok'
        else 'esquema incompleto'
    end
$$;

comment on function public.sanidade() is
    'Health check. Nao le dado de usuario e nao exige privilegio de tabela.';

-- ---------------------------------------------------------------------
-- 3. resolver_dispositivo() — troca token por (dispositivo, dono)
--
--    Substitui o `select ... from devices where token_hash = $1`.
--
--    O que ela devolve é o mínimo que a rota precisa: o id do dispositivo e o
--    id do dono. NÃO devolve `token_hash` (é a credencial), nem `nome`, nem
--    `revoked_at` — a revogação é aplicada aqui dentro, e um token revogado
--    simplesmente não devolve linha. A rota responde 401 igual para ausente,
--    desconhecido e revogado, como já fazia.
--
--    Note o que o papel de ingestão NÃO consegue com isto: listar
--    dispositivos, descobrir quantos existem, ou obter o hash de um token que
--    ele ainda não tenha. A função só responde a um hash exato.
-- ---------------------------------------------------------------------
create or replace function public.resolver_dispositivo(p_token_hash text)
returns table (id uuid, user_id uuid)
language sql
stable
security definer
set search_path = ''
as $$
    select d.id, d.user_id
      from public.devices d
     where d.token_hash = p_token_hash
       and d.revoked_at is null
     limit 1
$$;

comment on function public.resolver_dispositivo(text) is
    'Token -> (device, dono). Nao devolve token_hash. Token revogado nao '
    'devolve linha: a revogacao vale aqui dentro (SEC-02).';

-- ---------------------------------------------------------------------
-- 4. registrar_leitura() — a gravação, com o dono resolvido no banco
--
--    Substitui `insert_sleep_data` + `touch_device`, numa chamada só.
--
--    O TOKEN VOLTA COMO ARGUMENTO, de propósito: é o que faz o dono ser
--    derivado aqui dentro em vez de vir do chamador. Antes, `routes.py`
--    montava `"user_id": device["user_id"]` — correto, mas era uma linha de
--    Python entre o atacante e a posse do dado. Agora, quem tem a chave de
--    ingestão **não tem como escrever no nome de outro usuário**, porque não
--    existe parâmetro para isso.
--
--    Custo: uma segunda resolução do token por POST. É um lookup no índice
--    `devices_token_hash_idx`; ao lado do handshake TLS da requisição, não
--    aparece na conta.
--
--    Devolve o `id` da linha criada, e nulo quando o token não resolve. A rota
--    depende disso para responder 201 só com gravação confirmada (FIX-02).
--
--    A extração é campo a campo de propósito. `jsonb_populate_record` deixaria
--    o chamador escrever em QUALQUER coluna de `sleep_data`, presente ou
--    futura — inclusive `user_id`. A lista abaixo é a fronteira do que a
--    ingestão pode gravar, e acrescentar coluna a ela é um ato deliberado.
-- ---------------------------------------------------------------------
create or replace function public.registrar_leitura(
    p_token_hash text,
    p_leitura    jsonb
)
returns bigint
language plpgsql
volatile
security definer
set search_path = ''
as $$
declare
    v_device uuid;
    v_dono   uuid;
    v_id     bigint;
begin
    select d.id, d.user_id into v_device, v_dono
      from public.devices d
     where d.token_hash = p_token_hash
       and d.revoked_at is null
     limit 1;

    -- Token ausente, desconhecido ou revogado: nada é gravado e o chamador
    -- recebe nulo. Não levanta exceção — a rota já responde 401 nesse caso, e
    -- uma exceção aqui viraria 500 no caminho de ingestão (FIX-01).
    if v_device is null then
        return null;
    end if;

    insert into public.sleep_data (
        accel_x, accel_y, accel_z,
        gyro_x,  gyro_y,  gyro_z,
        temp, movimento_total, status,
        captured_at, epoca_segundos, metodo_agregacao, amostras,
        user_id, device_id
    ) values (
        (p_leitura ->> 'accel_x')::double precision,
        (p_leitura ->> 'accel_y')::double precision,
        (p_leitura ->> 'accel_z')::double precision,
        (p_leitura ->> 'gyro_x')::double precision,
        (p_leitura ->> 'gyro_y')::double precision,
        (p_leitura ->> 'gyro_z')::double precision,
        (p_leitura ->> 'temp')::double precision,
        (p_leitura ->> 'movimento_total')::double precision,
        (p_leitura ->> 'status')::text,
        (p_leitura ->> 'captured_at')::timestamptz,
        (p_leitura ->> 'epoca_segundos')::integer,
        (p_leitura ->> 'metodo_agregacao')::text,
        (p_leitura ->> 'amostras')::integer,
        -- Resolvidos acima, a partir do token. Nunca do JSON.
        v_dono,
        v_device
    )
    returning id into v_id;

    -- Último contato. Best-effort como antes: a leitura já foi gravada, e
    -- falhar aqui não pode desfazê-la — por isso o bloco próprio.
    begin
        update public.devices
           set last_seen_at = now()
         where id = v_device;
    exception when others then
        null;
    end;

    return v_id;
end;
$$;

comment on function public.registrar_leitura(text, jsonb) is
    'Gravacao da ingestao. O dono sai do token, dentro do banco: nao existe '
    'parametro para escrever no nome de outro usuario.';

-- ---------------------------------------------------------------------
-- 5. registrar_leitura_da_sessao() — o caminho do celular (APP-08)
--
--    O celular não tem token de device: ele se autentica com o JWT do usuário
--    e informa qual dos SEUS dispositivos está enviando. Até aqui essa gravação
--    também passava pela `service_role`, e é o segundo motivo pelo qual aquela
--    chave estava no caminho de ingestão.
--
--    Aqui ela sai de cena por completo: esta função é concedida a
--    `authenticated`, e o dono vem de `auth.uid()` — do JWT, validado pelo
--    Auth. Ou seja, **o caminho por sessão deixa de usar chave privilegiada**.
--
--    Ela é `security definer` porque `sleep_data` não tem (e não deve ter)
--    policy de insert para `authenticated`: cliente não fabrica leitura de
--    sensor por SQL direto. A única porta é esta função, que confere a posse do
--    dispositivo antes de gravar.
-- ---------------------------------------------------------------------
create or replace function public.registrar_leitura_da_sessao(
    p_device_id uuid,
    p_leitura   jsonb
)
returns bigint
language plpgsql
volatile
security definer
set search_path = ''
as $$
declare
    v_dono uuid := auth.uid();
    v_id   bigint;
begin
    if v_dono is null then
        return null;
    end if;

    -- A posse é conferida AQUI, não no Python. Inexistente, revogado e "de
    -- outra pessoa" caem no mesmo retorno nulo: distinguir permitiria
    -- descobrir ids de dispositivos alheios.
    if not exists (
        select 1 from public.devices d
         where d.id = p_device_id
           and d.user_id = v_dono
           and d.revoked_at is null
    ) then
        return null;
    end if;

    insert into public.sleep_data (
        accel_x, accel_y, accel_z,
        gyro_x,  gyro_y,  gyro_z,
        temp, movimento_total, status,
        captured_at, epoca_segundos, metodo_agregacao, amostras,
        user_id, device_id
    ) values (
        (p_leitura ->> 'accel_x')::double precision,
        (p_leitura ->> 'accel_y')::double precision,
        (p_leitura ->> 'accel_z')::double precision,
        (p_leitura ->> 'gyro_x')::double precision,
        (p_leitura ->> 'gyro_y')::double precision,
        (p_leitura ->> 'gyro_z')::double precision,
        (p_leitura ->> 'temp')::double precision,
        (p_leitura ->> 'movimento_total')::double precision,
        (p_leitura ->> 'status')::text,
        (p_leitura ->> 'captured_at')::timestamptz,
        (p_leitura ->> 'epoca_segundos')::integer,
        (p_leitura ->> 'metodo_agregacao')::text,
        (p_leitura ->> 'amostras')::integer,
        v_dono,
        p_device_id
    )
    returning id into v_id;

    begin
        update public.devices
           set last_seen_at = now()
         where id = p_device_id;
    exception when others then
        null;
    end;

    return v_id;
end;
$$;

comment on function public.registrar_leitura_da_sessao(uuid, jsonb) is
    'Gravacao do celular (APP-08). Dono vem de auth.uid(); a posse do '
    'dispositivo e conferida no banco. Nao usa chave privilegiada.';

-- ---------------------------------------------------------------------
-- 6. Privilégios de execução
--
--    Função nasce com EXECUTE para PUBLIC no Postgres. As revogações abaixo
--    não são cerimônia: sem elas, `anon` poderia chamar `resolver_dispositivo`
--    e `registrar_leitura` — e a chave anon está no bundle do frontend.
-- ---------------------------------------------------------------------
-- `handle_new_user` é da 001 e nasceu com EXECUTE para PUBLIC, como toda
-- função no Postgres. Não é explorável — o Postgres recusa chamada direta a
-- função `returns trigger` — mas é uma `security definer` alcançável por todo
-- papel, inclusive `anon`, sem nenhum motivo. Fechado aqui porque foi o teste
-- `test_o_papel_executa_exatamente_tres_funcoes` que a encontrou: o papel de
-- ingestão podia executá-la, e "podia executar" não deveria ter sobrado nada
-- além das três.
revoke all on function public.handle_new_user()                         from public;

revoke all on function public.sanidade()                                from public;
revoke all on function public.resolver_dispositivo(text)                from public;
revoke all on function public.registrar_leitura(text, jsonb)            from public;
revoke all on function public.registrar_leitura_da_sessao(uuid, jsonb)  from public;

-- O papel de ingestão: as três do caminho do dispositivo.
grant execute on function public.sanidade()                     to dormio_ingestao;
grant execute on function public.resolver_dispositivo(text)      to dormio_ingestao;
grant execute on function public.registrar_leitura(text, jsonb)  to dormio_ingestao;

-- O caminho por sessão pertence ao usuário autenticado, não à ingestão.
grant execute on function public.registrar_leitura_da_sessao(uuid, jsonb) to authenticated;

-- `/health` responde sem autenticação, então quem o serve precisa alcançar
-- `sanidade()`. `authenticated` também, para diagnóstico no app.
grant execute on function public.sanidade() to authenticated;

-- ---------------------------------------------------------------------
-- 7. Concessão ao `authenticator`
--
--    O PostgREST conecta como `authenticator` e faz SET ROLE para o papel da
--    claim. Sem esta concessão, um JWT com `role: dormio_ingestao` é recusado
--    com "unable to set role".
--
--    O bloco é condicional porque `authenticator` existe no Supabase e não num
--    Postgres puro — é o que permite aplicar esta mesma migração no banco de
--    teste (tests/rls) sem ramificação.
-- ---------------------------------------------------------------------
do $$
begin
    if exists (select 1 from pg_roles where rolname = 'authenticator') then
        execute 'grant dormio_ingestao to authenticator';
    end if;
end $$;

commit;

-- =====================================================================
-- VERIFICAÇÃO — rodar depois do commit
-- =====================================================================
--
-- 1. O papel NÃO tem privilégio de tabela nenhum (esperado: 0 linhas)
--
-- select table_name, privilege_type
--   from information_schema.table_privileges
--  where grantee = 'dormio_ingestao';
--
-- 2. O papel NÃO ignora RLS e não tem poder de administração
--    (esperado: rolbypassrls, rolsuper, rolcreatedb, rolcreaterole = false)
--
-- select rolname, rolsuper, rolbypassrls, rolcreatedb, rolcreaterole, rolcanlogin
--   from pg_roles where rolname = 'dormio_ingestao';
--
-- 3. O que ele PODE executar (esperado: as 3 funções, e só)
--
-- select p.proname
--   from pg_proc p join pg_namespace n on n.oid = p.pronamespace
--  where n.nspname = 'public'
--    and has_function_privilege('dormio_ingestao', p.oid, 'execute')
--  order by p.proname;
--
-- 4. `anon` NÃO alcança as funções de ingestão (esperado: 3x false)
--
-- select has_function_privilege('anon', 'public.resolver_dispositivo(text)', 'execute'),
--        has_function_privilege('anon', 'public.registrar_leitura(text,jsonb)', 'execute'),
--        has_function_privilege('anon', 'public.registrar_leitura_da_sessao(uuid,jsonb)', 'execute');
--
-- 5. As definer estão com search_path fixo (esperado: 3 linhas, todas com search_path=)
--
-- select p.proname, p.proconfig
--   from pg_proc p join pg_namespace n on n.oid = p.pronamespace
--  where n.nspname = 'public' and p.prosecdef
--  order by p.proname;
-- =====================================================================
