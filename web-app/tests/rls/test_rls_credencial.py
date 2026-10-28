"""A credencial do dispositivo é inalcançável pelo cliente (SEC-08).

── O QUE ISTO CONSERTA ──────────────────────────────────────────────────

`dispositivos.CAMPOS` omitia `token_hash` com um comentário dizendo que a
coluna era "material sensível". A omissão era correta e não protegia nada: o
GRANT do Supabase é de TABELA, e select de tabela alcança toda coluna dela.
`select=token_hash` via PostgREST devolvia — porque o navegador tem a chave
`anon` (pública por design) e um JWT, e não passa pela camada Python.

O estrago era pequeno: só o hash do PRÓPRIO dispositivo, e do hash não se volta
ao token. O que era grave é a distância entre o que o comentário prometia e o
que o esquema fazia — um comentário assim encerra a análise de quem revisa.

A 007 moveu o hash para `public.device_tokens`, sem GRANT para
`anon`/`authenticated`. Os testes daqui verificam que a coluna saiu de onde
estava, que a tabela nova não é alcançável, e que o pareamento continua
funcionando pelo caminho novo.
"""
import pytest

TABELA = "device_tokens"


# =====================================================================
# 1. A coluna saiu da tabela exposta
# =====================================================================

def test_devices_nao_tem_mais_token_hash(catalogo):
    """Estrutural, e o mais importante do arquivo.

    Enquanto a coluna existir em `devices`, qualquer GRANT de tabela naquela
    tabela a alcança — inclusive um que alguém recrie sem pensar. Tirá-la de lá
    é o que remove a classe de problema, em vez de um caso dela.
    """
    colunas = catalogo(
        """
        select column_name from information_schema.columns
         where table_schema = 'public' and table_name = 'devices'
           and column_name = 'token_hash'
        """
    )
    assert colunas == [], (
        "`devices.token_hash` voltou a existir. A tabela `devices` e exposta "
        "ao PostgREST e GRANT de tabela alcanca toda coluna dela — a "
        "credencial pertence a `device_tokens` (SEC-08)."
    )


def test_ana_nao_le_o_hash_pedindo_a_coluna_em_devices(como, cenario):
    """O ataque original, agora um erro de coluna inexistente."""
    with como(cenario["ana"]) as ana:
        ana.negado("select token_hash from public.devices")


def test_select_estrela_em_devices_continua_funcionando(como, cenario):
    """O motivo de não se ter usado permissão por coluna.

    `revoke select` + `grant select (colunas)` teria feito `select *` falhar por
    permissão — o default do PostgREST e de qualquer cliente novo, com uma
    mensagem que aponta para a tabela toda e não diz qual coluna é o problema.
    Com a coluna em outro lugar, `select *` funciona e simplesmente não traz
    credencial.
    """
    with como(cenario["ana"]) as ana:
        linhas = ana.executar("select * from public.devices")
    assert len(linhas) == 1, "a Ana deveria ver o proprio dispositivo"
    nomes = [descricao[0] for descricao in ana.cursor.description]
    assert "token_hash" not in nomes


# =====================================================================
# 2. A tabela nova não é alcançável pelo cliente
# =====================================================================

def test_nem_anon_nem_authenticated_tem_privilegio_na_tabela(catalogo):
    """É a ausência de GRANT que barra o PostgREST: sem privilégio, a tabela
    não é sequer exposta como endpoint."""
    concedidos = catalogo(
        """
        select grantee, privilege_type from information_schema.table_privileges
         where table_schema = 'public' and table_name = %s
           and grantee in ('anon', 'authenticated')
        """,
        (TABELA,),
    )
    assert concedidos == [], (
        f"public.{TABELA} recebeu GRANT para o cliente: "
        + "; ".join(f"{g}:{p}" for g, p in concedidos)
    )


def test_o_papel_de_ingestao_tambem_nao_alcanca_a_tabela(catalogo):
    """Ele resolve o token pela função, não pela tabela (SEC-06).

    Se tivesse select aqui, o pior caso de um vazamento daquela chave voltaria
    a incluir "lista o hash do token de todo mundo".
    """
    concedidos = catalogo(
        """
        select privilege_type from information_schema.table_privileges
         where table_schema = 'public' and table_name = %s
           and grantee = 'dormio_ingestao'
        """,
        (TABELA,),
    )
    assert concedidos == []


def test_ana_nao_le_a_tabela_de_credenciais(como, cenario):
    with como(cenario["ana"]) as ana:
        ana.negado("select * from public.%s" % TABELA)


def test_ana_nao_escreve_na_tabela_de_credenciais(como, cenario):
    """Escrever aqui seria trocar a credencial de um dispositivo."""
    with como(cenario["ana"]) as ana:
        ana.negado(
            "update public.%s set token_hash = 'escolhido' where true" % TABELA
        )


def test_anon_nao_alcanca_a_tabela_de_credenciais(como_anon):
    with como_anon() as visitante:
        visitante.negado("select * from public.%s" % TABELA)


def test_a_tabela_tem_rls_ligado_mesmo_sem_grant(catalogo):
    """Cinto e suspensório, e vale explicar por quê.

    O que barra o acesso é a ausência de GRANT. O RLS ligado sem policy é a
    segunda camada: se alguém der `grant select` aqui por engano — e é um
    engano fácil, porque o reflexo ao ver "permission denied" é conceder —
    o RLS ainda nega. As duas camadas falham por caminhos diferentes.
    """
    linhas = catalogo(
        "select rowsecurity from pg_tables where schemaname = 'public' and tablename = %s",
        (TABELA,),
    )
    assert linhas and linhas[0][0] is True


def test_a_tabela_nao_tem_policy_nenhuma(catalogo):
    """Policy aqui seria contradição: ninguém deve alcançar esta tabela por
    SQL direto, nem o dono. O acesso é só pelas funções definer."""
    policies = catalogo(
        "select policyname from pg_policies where schemaname = 'public' and tablename = %s",
        (TABELA,),
    )
    assert policies == [], (
        f"public.{TABELA} ganhou policy: {policies}. Policy aqui significa que "
        "alguem passou a alcancar a credencial por SQL direto."
    )


# =====================================================================
# 3. O caminho de ingestão continua funcionando
# =====================================================================

def test_resolver_dispositivo_ainda_resolve_pelo_hash(como, cenario):
    """A junção nova não pode ter quebrado o ESP32.

    O caminho de ingestão é o único que consulta a credencial, e ele o faz por
    função. Se esta asserção cair, o dispositivo em campo para de gravar.
    """
    with como(cenario["ana"], papel="dormio_ingestao") as ingestao:
        linhas = ingestao.executar(
            "select id, user_id from public.resolver_dispositivo(%s)", ("hash-ana-1",)
        )
    assert len(linhas) == 1
    assert str(linhas[0][0]) == cenario["device_ana"]
    assert str(linhas[0][1]) == cenario["ana"]


def test_registrar_leitura_ainda_grava_pelo_hash(como, cenario):
    with como(cenario["ana"], papel="dormio_ingestao") as ingestao:
        novo = ingestao.executar(
            "select public.registrar_leitura(%s, %s::jsonb)",
            ("hash-ana-1", '{"movimento_total": 1.25}'),
        )[0][0]
        assert novo is not None
        ingestao.cursor.execute("set local role postgres")
        dono = ingestao.executar(
            "select user_id from public.sleep_data where id = %s", (novo,)
        )[0][0]
    assert str(dono) == cenario["ana"]


def test_revogar_o_dispositivo_invalida_o_token(como, cenario, _conexao_dona):
    """A revogação continua em `devices.revoked_at`, e a junção a respeita.

    Este teste importa mais depois da 007: com credencial e dispositivo em
    tabelas diferentes, é possível escrever a junção esquecendo o
    `revoked_at` — e aí revogar deixaria de fechar a porta que promete fechar.
    """
    with _conexao_dona.cursor() as cursor:
        cursor.execute(
            "update public.devices set revoked_at = now() where id = %s",
            (cenario["device_ana"],),
        )
    try:
        with como(cenario["ana"], papel="dormio_ingestao") as ingestao:
            assert ingestao.executar(
                "select id from public.resolver_dispositivo(%s)", ("hash-ana-1",)
            ) == []
            assert ingestao.executar(
                "select public.registrar_leitura(%s, %s::jsonb)",
                ("hash-ana-1", "{}"),
            )[0][0] is None
    finally:
        with _conexao_dona.cursor() as cursor:
            cursor.execute(
                "update public.devices set revoked_at = null where id = %s",
                (cenario["device_ana"],),
            )


# =====================================================================
# 4. O pareamento pela função nova
# =====================================================================

def test_ana_pareia_um_dispositivo_novo(como, cenario):
    """Caminho feliz. Cria as duas linhas, e não devolve a credencial."""
    with como(cenario["ana"]) as ana:
        linhas = ana.executar(
            "select * from public.parear_dispositivo(%s, %s, %s)",
            ("Travesseiro novo", "travesseiro", "hash-novo-da-ana"),
        )
        assert len(linhas) == 1, "o pareamento nao devolveu o dispositivo"
        nomes = [d[0] for d in ana.cursor.description]
        assert "token_hash" not in nomes, "o pareamento devolveu a credencial"

        novo_id = linhas[0][0]
        ana.cursor.execute("set local role postgres")
        dono = ana.executar(
            "select user_id from public.devices where id = %s", (novo_id,)
        )[0][0]
        credencial = ana.executar(
            "select token_hash from public.device_tokens where device_id = %s",
            (novo_id,),
        )

    assert str(dono) == cenario["ana"], "o dono nao saiu de auth.uid()"
    assert credencial == [("hash-novo-da-ana",)], "a credencial nao foi gravada"


def test_o_pareamento_nao_aceita_escolher_o_dono(catalogo):
    """Estrutural: sem parâmetro de usuário, não há como parear para outro.

    A função é `security definer` e insere em `devices` ignorando o RLS. Se
    aceitasse um `p_user_id`, plantar um dispositivo na conta de outra pessoa
    seria uma chamada — e quem planta o dispositivo tem o token dele, ou seja,
    passa a escrever leitura carimbada como sendo da vítima.
    """
    assinaturas = catalogo(
        """
        select pg_get_function_identity_arguments(p.oid)
          from pg_proc p join pg_namespace n on n.oid = p.pronamespace
         where n.nspname = 'public' and p.proname = 'parear_dispositivo'
        """
    )
    assert assinaturas, "funcao parear_dispositivo ausente — migration 007 aplicada?"

    # TODAS as sobrecargas, e exatamente UMA.
    #
    # Este teste olhava so a primeira linha, e a verificacao por mutacao pegou o
    # furo: um sabotador que acrescentava `parear_dispositivo(text,text,text,uuid)`
    # SEM remover a versao de tres argumentos passava batido, porque a consulta
    # devolvia a antiga primeiro. Sobrecarga e exatamente como um parametro de
    # usuario entraria na pratica — ninguem apaga a funcao boa, acrescenta uma
    # "versao para o admin" ao lado.
    assert len(assinaturas) == 1, (
        "parear_dispositivo tem %d sobrecargas: %s. Deve haver uma so — "
        "sobrecarga e como um parametro de dono entra sem aparecer no diff da "
        "funcao original." % (len(assinaturas), [a[0] for a in assinaturas])
    )
    for (argumentos,) in assinaturas:
        assert "uuid" not in argumentos, (
            f"parear_dispositivo aceita uuid: {argumentos!r}. Sem parametro de "
            "usuario ela pareia para quem chamou; com um, para quem for indicado."
        )


def test_anon_nao_pareia_dispositivo(catalogo):
    assert catalogo(
        "select has_function_privilege('anon', "
        "'public.parear_dispositivo(text,text,text)', 'execute')"
    )[0][0] is False


def test_o_papel_de_ingestao_nao_pareia_dispositivo(catalogo):
    """A credencial do servidor não cria dispositivo.

    Se criasse, quem vazasse a chave poderia parear um dispositivo próprio e
    passar a gravar leitura legítima — com dono, aparecendo no painel de
    alguém. O pior caso voltaria a ser maior que "insere lixo".
    """
    assert catalogo(
        "select has_function_privilege('dormio_ingestao', "
        "'public.parear_dispositivo(text,text,text)', 'execute')"
    )[0][0] is False


def test_nao_da_para_criar_dispositivo_sem_credencial(como, cenario):
    """A policy de insert em `devices` foi removida pela 007.

    Um dispositivo sem linha em `device_tokens` é uma linha que o caminho por
    token nunca resolve, e que ninguém consegue explicar meses depois. O único
    caminho de criação é a função, que cria os dois.
    """
    with como(cenario["ana"]) as ana:
        ana.negado(
            "insert into public.devices (user_id, nome) values (%s, 'Sem credencial')",
            (cenario["ana"],),
        )


def test_apagar_o_dispositivo_apaga_a_credencial(como, cenario):
    """`on delete cascade`, e importa para a SEC-07.

    A exclusão de conta apaga `devices`. Uma credencial órfã sobrevivente seria
    dado remanescente de uma conta que não existe mais — e um hash que nenhuma
    junção alcança, logo invisível numa auditoria.
    """
    with como(cenario["ana"]) as ana:
        ana.contar_afetadas(
            "delete from public.devices where id = %s", (cenario["device_ana"],)
        )
        ana.cursor.execute("set local role postgres")
        restou = ana.executar(
            "select count(*) from public.device_tokens where device_id = %s",
            (cenario["device_ana"],),
        )[0][0]
    assert restou == 0


def test_apagar_a_conta_apaga_as_credenciais(como, cenario):
    with como(cenario["ana"]) as ana:
        ana.executar("select public.apagar_minha_conta()")
        ana.cursor.execute("set local role postgres")
        restou = ana.executar(
            """
            select count(*) from public.device_tokens t
             where t.device_id = %s
            """,
            (cenario["device_ana"],),
        )[0][0]
    assert restou == 0, "credencial sobreviveu a exclusao da conta"
