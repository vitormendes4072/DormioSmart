"""Infraestrutura dos testes de RLS (SEC-05 / INFRA-01).

── POR QUE ESTA PASTA EXISTE ────────────────────────────────────────────

O resto da suíte (`web-app/tests/`) mocka o Supabase. Isso é correto para o que
esses testes afirmam — eles verificam a lógica do Flask, e um mock é a forma
honesta de isolá-la. Mas tem uma consequência que ficou implícita por tempo
demais: **o RLS nunca foi exercitado**. Nenhum teste da suíte toca uma policy.
O isolamento entre usuários, que é a garantia central do sistema, era uma
afirmação escrita em SQL e em comentário, verificada a olho uma vez no SQL
Editor do Supabase.

Os testes desta pasta não mockam nada. Eles falam com um Postgres real, com as
migrações reais do repositório aplicadas, e tentam de fato ler e escrever dado
de outro usuário. Um mock aqui seria pior que nenhum teste: daria a sensação de
cobertura sem verificar a única coisa que importa.

── COMO RODAR ───────────────────────────────────────────────────────────

Estes testes são AUTOMATICAMENTE PULADOS sem um banco de teste. Eles não caem
para mock, e não tentam se conectar na instância de produção. Ver README.md.

    export DORMIO_RLS_DATABASE_URL="postgresql://postgres@/postgres?host=/tmp&port=5433"
    pytest tests/rls -v

── SALVAGUARDAS ─────────────────────────────────────────────────────────

O `setup` DESTRÓI o schema apontado pela URL (drop schema cascade) para partir
de um estado conhecido. Por isso o módulo se recusa a rodar contra host que
não seja local, e se recusa incondicionalmente contra `*.supabase.co` —
inclusive se alguém exportar a URL de produção por engano. Ver
`_conferir_destino`.
"""
import os
import pathlib
import urllib.parse

import pytest

psycopg2 = pytest.importorskip(
    "psycopg2",
    reason="psycopg2 nao instalado; `pip install psycopg2-binary` para rodar os testes de RLS",
)

# --- localização dos SQLs -------------------------------------------------

AQUI = pathlib.Path(__file__).resolve().parent
MIGRACOES = AQUI.parent.parent / "migrations"

# A 002 é deliberadamente omitida: ela exige edição manual (o e-mail de
# destino) e atribui posse de dado. Não é idempotente por natureza e não cria
# nem altera policy nenhuma — não há RLS nela para testar.
MIGRACOES_APLICADAS = (
    "001_multiusuario.sql",
    "003_padroniza_nome_do_dispositivo.sql",
    "004_tipo_de_dispositivo_e_agregacao.sql",
    "005_papel_de_ingestao_minimo.sql",
    "006_direito_de_eliminacao.sql",
    "007_credencial_fora_da_tabela_exposta.sql",
)

VARIAVEL = "DORMIO_RLS_DATABASE_URL"

MOTIVO_PULO = (
    f"{VARIAVEL} nao definida. Estes testes exigem um Postgres real com as "
    "migracoes aplicadas — eles NAO caem para mock, porque um mock nao "
    "exercita policy nenhuma. Ver web-app/tests/rls/README.md."
)

# --- IDs fixos: legíveis na saída do pytest ------------------------------

ANA = "aaaaaaaa-0000-4000-8000-aaaaaaaaaaaa"    # usuário A — o atacante
BRUNO = "bbbbbbbb-0000-4000-8000-bbbbbbbbbbbb"  # usuário B — a vítima

DEVICE_ANA = "a1a1a1a1-0000-4000-8000-a1a1a1a1a1a1"
DEVICE_BRUNO = "b1b1b1b1-0000-4000-8000-b1b1b1b1b1b1"


def _conferir_destino(url):
    """Recusa qualquer destino que não seja um banco de teste local.

    O setup roda `drop schema cascade`. Um erro de variável de ambiente aqui
    apagaria o banco do trabalho — então a checagem é explícita e não tem
    como ser contornada por engano.
    """
    partes = urllib.parse.urlsplit(url)
    host = (partes.hostname or "").lower()
    consulta = urllib.parse.parse_qs(partes.query)
    # Conexão por socket unix vem como ?host=/tmp e hostname vazio.
    host_socket = (consulta.get("host") or [""])[0]

    if "supabase.co" in host or "supabase.com" in host or "supabase" in host_socket.lower():
        pytest.fail(
            f"{VARIAVEL} aponta para o Supabase ({host or host_socket}). Estes testes "
            "DESTROEM o schema de destino. Use um Postgres local descartavel.",
            pytrace=False,
        )

    local = host in ("", "localhost", "127.0.0.1", "::1") or host_socket.startswith("/")
    if not local and os.environ.get("DORMIO_RLS_PERMITIR_REMOTO") != "1":
        pytest.fail(
            f"{VARIAVEL} aponta para o host remoto '{host}'. Estes testes DESTROEM o "
            "schema de destino. Use um Postgres local, ou exporte "
            "DORMIO_RLS_PERMITIR_REMOTO=1 se souber exatamente o que esta fazendo.",
            pytrace=False,
        )


@pytest.fixture(scope="session")
def url_do_banco():
    url = os.environ.get(VARIAVEL, "").strip()
    if not url:
        pytest.skip(MOTIVO_PULO, allow_module_level=True)
    _conferir_destino(url)
    return url


@pytest.fixture(scope="session")
def _conexao_dona(url_do_banco):
    """Conexão do dono do banco. Aplica o esquema; nunca usada nos testes.

    Os testes NÃO usam esta conexão para exercitar policy: o dono da tabela
    ignora RLS por definição no Postgres, e um teste que passasse por aqui não
    provaria nada. Ela existe para montar o cenário e para ler o catálogo.
    """
    conexao = psycopg2.connect(url_do_banco)
    conexao.autocommit = True
    yield conexao
    conexao.close()


def _rodar_sql(cursor, caminho):
    cursor.execute(pathlib.Path(caminho).read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def esquema(_conexao_dona):
    """Recria o schema do zero e aplica as migrações REAIS do repositório.

    As policies sob teste são as de `web-app/migrations/`, lidas do disco. Não
    há cópia das policies neste arquivo de propósito: uma cópia envelheceria em
    silêncio e a suíte passaria a testar a si mesma.
    """
    with _conexao_dona.cursor() as cursor:
        cursor.execute("drop schema if exists public cascade")
        cursor.execute("drop schema if exists auth cascade")

        # OS PAPÉIS TAMBÉM, e este detalhe custou um teste falhando sem motivo
        # aparente. Papel é objeto de CLUSTER, não de schema: `drop schema
        # cascade` não o alcança. Então um `alter role dormio_ingestao
        # bypassrls` — que é uma das sabotagens de `verificar_por_mutacao.py` —
        # sobrevivia ao setup e contaminava TODA execução seguinte, inclusive a
        # limpa. O sintoma foi `test_o_papel_existe_e_nao_ignora_o_rls` falhando
        # numa árvore sem nenhuma sabotagem aplicada.
        #
        # Neste ponto os papéis não possuem objeto nenhum (os schemas acabaram
        # de cair), então o drop é seguro. `drop owned by` cobre privilégio
        # residual em outros bancos do cluster.
        for papel in ("dormio_ingestao", "anon", "authenticated", "service_role", "authenticator"):
            cursor.execute(
                "select 1 from pg_roles where rolname = %s", (papel,)
            )
            if cursor.fetchone():
                cursor.execute(f'drop owned by "{papel}" cascade')
                cursor.execute(f'drop role "{papel}"')

        cursor.execute("create schema public")

        _rodar_sql(cursor, AQUI / "esquema_base.sql")

        for nome in MIGRACOES_APLICADAS:
            caminho = MIGRACOES / nome
            if not caminho.exists():
                pytest.fail(f"migracao ausente: {caminho}", pytrace=False)
            _rodar_sql(cursor, caminho)

        _rodar_sql(cursor, AQUI / "grants_pos_migracao.sql")
    return True


@pytest.fixture(scope="session")
def cenario(_conexao_dona, esquema):
    """Duas contas com dado de cada uma, mais uma linha órfã.

    Semeado pelo dono do banco (equivalente ao `service_role`), que é como o
    dado nasce em produção: a ingestão escreve com service_role. Os IDs das
    linhas de sono voltam no dicionário porque os testes adversariais precisam
    tentar alcançar uma linha ESPECÍFICA do outro usuário — não basta pedir
    "tudo" e conferir a contagem, porque um filtro mal escrito no lado do
    cliente esconderia o vazamento.
    """
    with _conexao_dona.cursor() as cursor:
        cursor.execute(
            """
            insert into auth.users (id, email, raw_user_meta_data) values
                (%s, 'ana@exemplo.test',   '{"nome": "Ana"}'),
                (%s, 'bruno@exemplo.test', '{"nome": "Bruno"}')
            """,
            (ANA, BRUNO),
        )

        # O trigger `on_auth_user_created` da 001 deve ter criado os profiles.
        cursor.execute(
            """
            insert into public.devices (id, user_id, nome, tipo) values
                (%s, %s, 'Travesseiro da Ana',   'travesseiro'),
                (%s, %s, 'Travesseiro do Bruno', 'travesseiro')
            """,
            (DEVICE_ANA, ANA, DEVICE_BRUNO, BRUNO),
        )

        # A credencial vive em `device_tokens` desde a 007 (SEC-08): `devices`
        # e exposta ao PostgREST, e GRANT de tabela alcanca toda coluna dela.
        cursor.execute(
            """
            insert into public.device_tokens (device_id, token_hash) values
                (%s, 'hash-ana-1'), (%s, 'hash-bruno-1')
            """,
            (DEVICE_ANA, DEVICE_BRUNO),
        )

        linhas = {}
        for rotulo, usuario, device, movimento in (
            ("ana", ANA, DEVICE_ANA, 1.5),
            ("bruno", BRUNO, DEVICE_BRUNO, 9.75),
        ):
            cursor.execute(
                """
                insert into public.sleep_data
                    (user_id, device_id, movimento_total, temp, status)
                values (%s, %s, %s, 31.0, 'Dormindo')
                returning id
                """,
                (usuario, device, movimento),
            )
            linhas[rotulo] = cursor.fetchone()[0]

        # Linha sem dono: as leituras anteriores à 001 são assim. Com o RLS
        # por dono ativo, ninguém deve enxergá-la (o conserto é a 002/DATA-03).
        cursor.execute(
            """
            insert into public.sleep_data (movimento_total, temp, status)
            values (42.0, 30.0, 'Orfa') returning id
            """
        )
        linhas["orfa"] = cursor.fetchone()[0]

    return {
        "ana": ANA,
        "bruno": BRUNO,
        "device_ana": DEVICE_ANA,
        "device_bruno": DEVICE_BRUNO,
        "leitura_ana": linhas["ana"],
        "leitura_bruno": linhas["bruno"],
        "leitura_orfa": linhas["orfa"],
    }


class Sessao:
    """Uma requisição autenticada, como o PostgREST a monta.

    `SET LOCAL ROLE authenticated` + a claim `sub` no GUC é literalmente o que
    o PostgREST faz por requisição. Então o que estes testes alcançam é a mesma
    superfície que o NAVEGADOR alcança com a chave anon (que é pública por
    design) e um JWT válido — não apenas o que as rotas Flask expõem.

    Tudo roda em transação com rollback no fim: nenhuma escrita de um teste
    sobrevive para o próximo, e o caminho feliz pode inserir sem sujar o
    cenário.
    """

    def __init__(self, conexao, cursor):
        self._conexao = conexao
        self.cursor = cursor

    def executar(self, sql, parametros=None):
        """Roda e devolve as linhas (lista vazia quando não há resultado)."""
        self.cursor.execute(sql, parametros)
        if self.cursor.description is None:
            return []
        return self.cursor.fetchall()

    def contar_afetadas(self, sql, parametros=None):
        """Roda um UPDATE/DELETE e devolve quantas linhas foram afetadas.

        Sem policy para o comando, o Postgres não levanta erro: simplesmente
        nenhuma linha é visível para alterar, e o comando afeta zero. Zero é,
        portanto, o resultado que prova a negativa — e é por isso que estes
        testes checam contagem e não exceção.
        """
        self.cursor.execute(sql, parametros)
        return self.cursor.rowcount

    def negado(self, sql, parametros=None):
        """Roda esperando recusa do banco. Devolve o erro.

        Usado onde a negativa vira ERRO e não zero-linhas: violação de
        `with check` num INSERT, por exemplo. Falha o teste se o comando passar.
        """
        try:
            self.cursor.execute(sql, parametros)
        except psycopg2.Error as erro:
            self._conexao.rollback()
            self._reaplicar()
            return erro
        raise AssertionError(
            "o banco ACEITOU um comando que deveria recusar:\n" + str(sql).strip()
        )

    # Depois de um rollback por erro, o papel e a claim voltam ao padrão.
    # Reaplicá-los mantém a sessão utilizável para as asserções seguintes.
    def _reaplicar(self):
        pass  # sobrescrito em `_abrir`


def _abrir(url, usuario_id=None, papel="authenticated"):
    conexao = psycopg2.connect(url)
    cursor = conexao.cursor()

    def aplicar():
        if usuario_id is not None:
            cursor.execute(
                "select set_config('request.jwt.claims', %s, true)",
                ('{"sub": "%s", "role": "%s"}' % (usuario_id, papel),),
            )
        cursor.execute("set local role %s" % papel)

    aplicar()
    sessao = Sessao(conexao, cursor)
    sessao._reaplicar = aplicar
    return conexao, sessao


@pytest.fixture
def como(url_do_banco, cenario):
    """Abre uma sessão autenticada como o usuário informado.

        with como(cenario["ana"]) as ana:
            ana.executar("select ...")

    Cada `with` é uma transação própria, revertida no fim.
    """
    import contextlib

    abertas = []

    @contextlib.contextmanager
    def fabricar(usuario_id, papel="authenticated"):
        conexao, sessao = _abrir(url_do_banco, usuario_id, papel)
        abertas.append(conexao)
        try:
            yield sessao
        finally:
            conexao.rollback()

    yield fabricar

    for conexao in abertas:
        conexao.close()


@pytest.fixture
def como_anon(url_do_banco, cenario):
    """Sessão sem JWT nenhum — o visitante com a chave anon e nada mais."""
    import contextlib

    @contextlib.contextmanager
    def fabricar():
        conexao, sessao = _abrir(url_do_banco, usuario_id=None, papel="anon")
        try:
            yield sessao
        finally:
            conexao.rollback()
            conexao.close()

    return fabricar


@pytest.fixture
def catalogo(_conexao_dona, esquema):
    """Leitura do catálogo do Postgres (pg_policies, pg_tables).

    Usada pelos testes estruturais, que não tentam acessar dado: eles afirmam
    que o RLS está LIGADO e que as policies são as esperadas. É o que pega uma
    migração futura que desabilite RLS ou acrescente uma policy larga — coisa
    que os testes de acesso não pegariam, porque eles só provam que o que
    existe hoje se comporta bem.
    """

    def consultar(sql, parametros=None):
        with _conexao_dona.cursor() as cursor:
            cursor.execute(sql, parametros)
            return cursor.fetchall()

    return consultar
