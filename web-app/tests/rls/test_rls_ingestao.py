"""O papel de ingestão é mínimo de fato (SEC-06).

── O QUE ESTES TESTES AFIRMAM ───────────────────────────────────────────

Que a credencial do caminho de ingestão **não consegue ler dado de usuário
nenhum**. Antes da migration 005 ela era a `service_role`, com `BYPASSRLS` e
privilégio total: o pior caso de um vazamento era o banco inteiro. O objetivo
declarado da mudança foi fazer o pior caso virar "insere lixo", e é isso que se
verifica aqui — linha por linha, sob o papel real, não por leitura da migração.

A parte que mais importa é a seção 3: a função de gravação recebe o token e
resolve o dono no banco, então **não existe parâmetro por onde escolher de quem
é o dado**. Os testes tentam mesmo assim, de três jeitos diferentes.

── E O QUE ELES NÃO AFIRMAM ─────────────────────────────────────────────

Que as funções `security definer` estão livres de defeito. Elas rodam com o
privilégio do dono, então um erro dentro de uma delas é desvio completo do RLS
— é o risco que a 005 assume em troca de tirar a `service_role` do caminho.
Estes testes cobrem a superfície (o que entra, o que sai, quem pode chamar),
não a ausência de bug.
"""
import pytest

PAPEL = "dormio_ingestao"

TABELAS = ("profiles", "devices", "sleep_data")

# Assinaturas como o Postgres as identifica, para `has_function_privilege`.
F_SANIDADE = "public.sanidade()"
F_RESOLVER = "public.resolver_dispositivo(text)"
F_REGISTRAR = "public.registrar_leitura(text,jsonb)"
F_REGISTRAR_SESSAO = "public.registrar_leitura_da_sessao(uuid,jsonb)"

HASH_ANA = "hash-ana-1"
HASH_BRUNO = "hash-bruno-1"


# =====================================================================
# 1. O papel não tem privilégio de tabela nenhum
# =====================================================================

def test_o_papel_existe_e_nao_ignora_o_rls(catalogo):
    linhas = catalogo(
        """
        select rolsuper, rolbypassrls, rolcreatedb, rolcreaterole, rolcanlogin
          from pg_roles where rolname = %s
        """,
        (PAPEL,),
    )
    assert linhas, f"papel {PAPEL} nao existe — migration 005 aplicada?"
    for poder, valor in zip(
        ("superuser", "bypassrls", "createdb", "createrole", "login"), linhas[0]
    ):
        assert valor is False, f"{PAPEL} tem {poder} — nao deveria"


def test_o_papel_nao_tem_privilegio_de_tabela(catalogo):
    """O coração da mudança: zero GRANT de tabela.

    Não basta checar as três tabelas conhecidas — uma tabela futura que receba
    GRANT para este papel por descuido apareceria aqui.
    """
    concedidos = catalogo(
        """
        select table_name, privilege_type
          from information_schema.table_privileges
         where grantee = %s and table_schema = 'public'
         order by table_name, privilege_type
        """,
        (PAPEL,),
    )
    assert concedidos == [], (
        f"{PAPEL} recebeu privilegio de tabela: "
        + "; ".join(f"{t}:{p}" for t, p in concedidos)
        + ". O ganho da 005 e justamente nao ter nenhum."
    )


def test_o_papel_nao_tem_privilegio_de_coluna(catalogo):
    """GRANT por coluna não aparece em `table_privileges`. Este pega."""
    concedidos = catalogo(
        """
        select table_name, column_name, privilege_type
          from information_schema.column_privileges
         where grantee = %s and table_schema = 'public'
        """,
        (PAPEL,),
    )
    assert concedidos == [], (
        f"{PAPEL} recebeu privilegio de coluna: "
        + "; ".join(f"{t}.{c}:{p}" for t, c, p in concedidos)
    )


@pytest.mark.parametrize("tabela", TABELAS)
def test_o_papel_nao_le_tabela_alguma(como, cenario, tabela):
    """O teste que corresponde ao "pior caso" antigo.

    Com a `service_role`, este select devolvia o banco inteiro. Agora é recusa
    por permissão — antes de o RLS sequer entrar em cena.
    """
    with como(cenario["ana"], papel=PAPEL) as ingestao:
        erro = ingestao.negado("select * from public.%s" % tabela)
    assert "permission denied" in str(erro).lower() or "permissão" in str(erro).lower()


@pytest.mark.parametrize("tabela", TABELAS)
def test_o_papel_nao_escreve_em_tabela_alguma(como, cenario, tabela):
    with como(cenario["ana"], papel=PAPEL) as ingestao:
        ingestao.negado("delete from public.%s" % tabela)


def test_o_papel_nao_insere_direto_em_sleep_data(como, cenario):
    """A única porta de gravação é a função. O INSERT direto morre."""
    with como(cenario["ana"], papel=PAPEL) as ingestao:
        ingestao.negado(
            """
            insert into public.sleep_data (user_id, movimento_total, status)
            values (%s, 1.0, 'Direto')
            """,
            (cenario["ana"],),
        )


def test_o_papel_nao_le_o_token_hash_de_ninguem(como, cenario):
    """O material que o SEC-02 existe para não entregar."""
    with como(cenario["ana"], papel=PAPEL) as ingestao:
        ingestao.negado("select token_hash from public.devices")


def test_o_papel_executa_exatamente_tres_funcoes(catalogo):
    """Enumera o que ele PODE, para que ampliar apareça no diff."""
    permitidas = catalogo(
        """
        select p.proname || '(' || pg_get_function_identity_arguments(p.oid) || ')'
          from pg_proc p join pg_namespace n on n.oid = p.pronamespace
         where n.nspname = 'public'
           and has_function_privilege(%s, p.oid, 'execute')
         order by 1
        """,
        (PAPEL,),
    )
    nomes = {linha[0] for linha in permitidas}
    esperado = {
        "sanidade()",
        "resolver_dispositivo(p_token_hash text)",
        "registrar_leitura(p_token_hash text, p_leitura jsonb)",
    }
    assert nomes == esperado, (
        f"o que {PAPEL} pode executar mudou.\nesperado: {sorted(esperado)}\n"
        f"encontrado: {sorted(nomes)}"
    )


def test_o_papel_nao_grava_pelo_caminho_da_sessao(catalogo):
    """`registrar_leitura_da_sessao` pertence ao usuário, não à ingestão.

    Se a ingestão pudesse chamá-la, poderia gravar sem token — e o dono viria
    de `auth.uid()`, que ela controla pela claim. Seria a brecha de volta.
    """
    assert catalogo(
        "select has_function_privilege(%s, %s, 'execute')",
        (PAPEL, F_REGISTRAR_SESSAO),
    )[0][0] is False


# =====================================================================
# 2. As funções fazem o que a rota precisa (caminho feliz)
# =====================================================================

def test_sanidade_responde_ok(como, cenario):
    """O health check funciona sem privilégio de tabela — era o ponto."""
    with como(cenario["ana"], papel=PAPEL) as ingestao:
        assert ingestao.executar("select public.sanidade()") == [("ok",)]


def test_resolver_dispositivo_devolve_o_dono_certo(como, cenario):
    with como(cenario["ana"], papel=PAPEL) as ingestao:
        linhas = ingestao.executar(
            "select id, user_id from public.resolver_dispositivo(%s)", (HASH_ANA,)
        )
    assert len(linhas) == 1
    assert str(linhas[0][0]) == cenario["device_ana"]
    assert str(linhas[0][1]) == cenario["ana"]


def test_resolver_dispositivo_nao_devolve_token_hash(catalogo):
    """A coluna de credencial não está no tipo de retorno. Estrutural."""
    retorno = catalogo(
        """
        select pg_get_function_result(p.oid)
          from pg_proc p join pg_namespace n on n.oid = p.pronamespace
         where n.nspname = 'public' and p.proname = 'resolver_dispositivo'
        """
    )[0][0]
    assert "token_hash" not in retorno, retorno
    assert retorno.count("uuid") == 2, f"retorno inesperado: {retorno}"


def test_resolver_dispositivo_nao_encontra_token_desconhecido(como, cenario):
    with como(cenario["ana"], papel=PAPEL) as ingestao:
        assert ingestao.executar(
            "select id from public.resolver_dispositivo(%s)", ("hash-que-nao-existe",)
        ) == []


def test_resolver_dispositivo_recusa_token_revogado(como, cenario, _conexao_dona):
    """A revogação tem de valer dentro da função, não no Python.

    Antes, `revoked_at` voltava na consulta e o Python decidia. Se a checagem
    saísse do banco, um token revogado voltaria a funcionar — e o SEC-02
    deixaria de fechar a porta que promete fechar.
    """
    with _conexao_dona.cursor() as cursor:
        cursor.execute(
            "update public.devices set revoked_at = now() where id = %s",
            (cenario["device_bruno"],),
        )
    try:
        with como(cenario["ana"], papel=PAPEL) as ingestao:
            assert ingestao.executar(
                "select id from public.resolver_dispositivo(%s)", (HASH_BRUNO,)
            ) == []
    finally:
        with _conexao_dona.cursor() as cursor:
            cursor.execute(
                "update public.devices set revoked_at = null where id = %s",
                (cenario["device_bruno"],),
            )


def test_registrar_leitura_grava_e_carimba_o_dono(como, cenario):
    with como(cenario["ana"], papel=PAPEL) as ingestao:
        novo = ingestao.executar(
            "select public.registrar_leitura(%s, %s::jsonb)",
            (HASH_ANA, '{"movimento_total": 7.5, "status": "Dormindo"}'),
        )[0][0]
        assert novo is not None, "a gravacao nao confirmou"

        # Conferido pelo dono do banco na mesma transação: o papel de ingestão
        # não pode ler `sleep_data`, o que é exatamente o desejado.
        ingestao.cursor.execute("set local role postgres")
        linha = ingestao.executar(
            "select user_id, device_id, movimento_total from public.sleep_data where id = %s",
            (novo,),
        )[0]

    assert str(linha[0]) == cenario["ana"]
    assert str(linha[1]) == cenario["device_ana"]
    assert linha[2] == 7.5


def test_registrar_leitura_atualiza_o_ultimo_contato(como, cenario):
    """`touch_device` virou parte da mesma chamada. Se parar de acontecer, o
    painel passa a mostrar dispositivo ativo como se estivesse mudo."""
    with como(cenario["ana"], papel=PAPEL) as ingestao:
        ingestao.executar(
            "select public.registrar_leitura(%s, %s::jsonb)", (HASH_ANA, "{}")
        )
        ingestao.cursor.execute("set local role postgres")
        visto = ingestao.executar(
            "select last_seen_at from public.devices where id = %s",
            (cenario["device_ana"],),
        )[0][0]
    assert visto is not None


def test_registrar_leitura_recusa_token_desconhecido_sem_gravar(como, cenario):
    with como(cenario["ana"], papel=PAPEL) as ingestao:
        resultado = ingestao.executar(
            "select public.registrar_leitura(%s, %s::jsonb)",
            ("hash-invencionice", '{"movimento_total": 1.0}'),
        )[0][0]
        assert resultado is None

        ingestao.cursor.execute("set local role postgres")
        assert ingestao.executar(
            "select count(*) from public.sleep_data where movimento_total = 1.0"
        )[0][0] == 0


# =====================================================================
# 3. A ingestão não escolhe o dono — as três tentativas
# =====================================================================

def test_a_ingestao_nao_escolhe_o_dono_pelo_json(como, cenario):
    """Tentativa 1: mandar `user_id` no JSON da leitura.

    A função extrai coluna por coluna e `user_id` não está na lista. O valor é
    simplesmente ignorado, e o dono continua sendo o do token.
    """
    with como(cenario["ana"], papel=PAPEL) as ingestao:
        novo = ingestao.executar(
            "select public.registrar_leitura(%s, %s::jsonb)",
            (
                HASH_ANA,
                '{"movimento_total": 3.3, "user_id": "%s", "device_id": "%s"}'
                % (cenario["bruno"], cenario["device_bruno"]),
            ),
        )[0][0]

        ingestao.cursor.execute("set local role postgres")
        dono, device = ingestao.executar(
            "select user_id, device_id from public.sleep_data where id = %s", (novo,)
        )[0]

    assert str(dono) == cenario["ana"], "o JSON conseguiu escolher o dono"
    assert str(device) == cenario["device_ana"]


def test_a_ingestao_nao_escolhe_o_dono_pela_claim_do_jwt(como, cenario):
    """Tentativa 2: forjar a claim `sub`.

    `registrar_leitura` não consulta `auth.uid()` — o dono vem do token. Uma
    claim escolhida pelo atacante não muda nada. (No caminho por sessão é o
    contrário, e é por isso que aquela função não é concedida a este papel.)
    """
    with como(cenario["bruno"], papel=PAPEL) as ingestao:
        novo = ingestao.executar(
            "select public.registrar_leitura(%s, %s::jsonb)",
            (HASH_ANA, '{"movimento_total": 4.4}'),
        )[0][0]
        ingestao.cursor.execute("set local role postgres")
        dono = ingestao.executar(
            "select user_id from public.sleep_data where id = %s", (novo,)
        )[0][0]

    assert str(dono) == cenario["ana"], (
        "a claim do JWT influenciou o dono no caminho por token"
    )


def test_a_ingestao_nao_escreve_em_coluna_fora_da_lista(como, cenario):
    """Tentativa 3: mandar coluna que existe na tabela mas não na função.

    `created_at` é a hora de RECEBIMENTO, gerada pelo banco. Se o chamador
    pudesse defini-la, poderia plantar leitura no passado — e o painel
    acreditaria. A extração campo a campo é o que impede.
    """
    with como(cenario["ana"], papel=PAPEL) as ingestao:
        novo = ingestao.executar(
            "select public.registrar_leitura(%s, %s::jsonb)",
            (HASH_ANA, '{"movimento_total": 5.5, "created_at": "1999-01-01T00:00:00Z"}'),
        )[0][0]
        ingestao.cursor.execute("set local role postgres")
        criado = ingestao.executar(
            "select created_at from public.sleep_data where id = %s", (novo,)
        )[0][0]

    assert criado.year > 2020, f"created_at foi escolhido pelo chamador: {criado}"


# =====================================================================
# 4. Quem mais pode chamar as funções
# =====================================================================

@pytest.mark.parametrize(
    "funcao", [F_RESOLVER, F_REGISTRAR, F_REGISTRAR_SESSAO]
)
def test_anon_nao_executa_funcao_de_ingestao(catalogo, funcao):
    """A chave anon está no bundle do frontend.

    Função no Postgres nasce com EXECUTE para PUBLIC — sem o `revoke` da 005,
    qualquer visitante chamaria `registrar_leitura`. Este teste é o que garante
    que aquele `revoke` não seja removido por engano.
    """
    assert catalogo(
        "select has_function_privilege('anon', %s, 'execute')", (funcao,)
    )[0][0] is False


@pytest.mark.parametrize("funcao", [F_RESOLVER, F_REGISTRAR])
def test_authenticated_nao_executa_o_caminho_por_token(catalogo, funcao):
    """Usuário logado não resolve token nem grava por token.

    Se pudesse, um usuário qualquer poderia testar hashes e gravar leitura em
    nome de quem o token pertencesse.
    """
    assert catalogo(
        "select has_function_privilege('authenticated', %s, 'execute')", (funcao,)
    )[0][0] is False


def test_ana_grava_pelo_caminho_da_sessao_no_proprio_dispositivo(como, cenario):
    """Caminho feliz do celular (APP-08), sem chave privilegiada nenhuma."""
    with como(cenario["ana"]) as ana:
        novo = ana.executar(
            "select public.registrar_leitura_da_sessao(%s::uuid, %s::jsonb)",
            (cenario["device_ana"], '{"movimento_total": 2.2, "epoca_segundos": 30}'),
        )[0][0]
        assert novo is not None, "a Ana nao conseguiu gravar no proprio dispositivo"

        ana.cursor.execute("set local role postgres")
        dono = ana.executar(
            "select user_id from public.sleep_data where id = %s", (novo,)
        )[0][0]
    assert str(dono) == cenario["ana"]


def test_ana_nao_grava_no_dispositivo_do_bruno(como, cenario):
    """O adversarial do caminho por sessão.

    A posse é conferida dentro da função. Se a checagem voltasse para o Python,
    um celular poderia gravar em qualquer `device_id` que adivinhasse.
    """
    with como(cenario["ana"]) as ana:
        resultado = ana.executar(
            "select public.registrar_leitura_da_sessao(%s::uuid, %s::jsonb)",
            (cenario["device_bruno"], '{"movimento_total": 6.6}'),
        )[0][0]
        assert resultado is None, "a Ana gravou no dispositivo do Bruno"

        ana.cursor.execute("set local role postgres")
        assert ana.executar(
            "select count(*) from public.sleep_data where movimento_total = 6.6"
        )[0][0] == 0


def test_a_sessao_nao_escolhe_o_dono_pelo_json(como, cenario):
    """Mesmo dentro do próprio dispositivo, o dono vem de `auth.uid()`."""
    with como(cenario["ana"]) as ana:
        novo = ana.executar(
            "select public.registrar_leitura_da_sessao(%s::uuid, %s::jsonb)",
            (
                cenario["device_ana"],
                '{"movimento_total": 8.8, "user_id": "%s"}' % cenario["bruno"],
            ),
        )[0][0]
        ana.cursor.execute("set local role postgres")
        dono = ana.executar(
            "select user_id from public.sleep_data where id = %s", (novo,)
        )[0][0]
    assert str(dono) == cenario["ana"]


def test_anon_nao_grava_pelo_caminho_da_sessao(como_anon, cenario):
    """Sem JWT, `auth.uid()` é nulo e a função recusa — além do revoke."""
    with como_anon() as visitante:
        visitante.negado(
            "select public.registrar_leitura_da_sessao(%s::uuid, %s::jsonb)",
            (cenario["device_ana"], "{}"),
        )


# =====================================================================
# 5. As definer estão blindadas
# =====================================================================

def test_toda_funcao_definer_tem_search_path_fixo(catalogo):
    """`security definer` sem `search_path` é escalada de privilégio.

    Quem controlasse o `search_path` escolheria qual função a definer chama —
    e a definer roda com o privilégio do dono. Vale para as quatro da 005 e
    para o `handle_new_user` da 001.
    """
    frouxas = catalogo(
        """
        select p.proname, coalesce(array_to_string(p.proconfig, ','), '(nenhum)')
          from pg_proc p join pg_namespace n on n.oid = p.pronamespace
         where n.nspname = 'public'
           and p.prosecdef
           and (p.proconfig is null
                or not exists (
                    select 1 from unnest(p.proconfig) c where c like 'search_path=%'
                ))
        """
    )
    assert frouxas == [], (
        "funcao SECURITY DEFINER sem search_path fixo: "
        + "; ".join(f"{n} -> {c}" for n, c in frouxas)
    )


def test_as_funcoes_de_gravacao_sao_definer(catalogo):
    """Se deixarem de ser, param de funcionar para o papel sem privilégio —
    e a tentação seria "consertar" devolvendo GRANT de tabela a ele."""
    for nome in ("resolver_dispositivo", "registrar_leitura", "registrar_leitura_da_sessao"):
        linhas = catalogo(
            """
            select p.prosecdef from pg_proc p join pg_namespace n on n.oid = p.pronamespace
             where n.nspname = 'public' and p.proname = %s
            """,
            (nome,),
        )
        assert linhas and linhas[0][0] is True, f"{nome} nao e SECURITY DEFINER"


def test_sanidade_nao_e_definer(catalogo):
    """Ela não precisa de privilégio. Ser definer seria superfície de graça."""
    linhas = catalogo(
        """
        select p.prosecdef from pg_proc p join pg_namespace n on n.oid = p.pronamespace
         where n.nspname = 'public' and p.proname = 'sanidade'
        """
    )
    assert linhas and linhas[0][0] is False
