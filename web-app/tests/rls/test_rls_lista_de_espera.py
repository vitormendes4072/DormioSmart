"""A lista de espera do lançamento (UI-14, migração 022).

── O QUE ESTÁ SOB TESTE ─────────────────────────────────────────────────────

A lista guarda e-mail de quem não tem conta. A 022 faz o BANCO garantir:

  1. ninguém do cliente lê, escreve, altera ou apaga a tabela — nem `anon` (a chave pública),
     nem `authenticated` (qualquer conta), nem a ingestão;
  2. o único caminho de escrita é `inscrever_na_lista_de_espera`, e só a ingestão o executa;
  3. a função normaliza e valida, recusa versão errada do texto, não revela se o e-mail já
     estava na lista e recusa acima de 100 inscrições na última hora;
  4. o expurgo dos 12 meses apaga só o que passou do prazo, e ninguém do cliente o executa.

Tudo roda em transação revertida no fim (conftest): as inscrições de um teste não vazam para
o próximo.
"""
import pytest

SEM_PRIVILEGIO = "42501"
CHECK = "23514"
LISTA_CHEIA = "PT429"
PAPEL_INGESTAO = "dormio_ingestao"
F_INSCREVER = "public.inscrever_na_lista_de_espera(text, text, text)"
F_EXPURGAR = "public.expurgar_lista_de_espera()"


def _versao(sessao):
    sessao.cursor.execute("set local role postgres")
    versao = sessao.executar("select public.versao_da_lista_de_espera()")[0][0]
    sessao._reaplicar()
    return versao


def _como_dono(sessao, sql, parametros=None):
    """Roda como dono do banco, na mesma transação, e volta ao papel da sessão."""
    sessao.cursor.execute("set local role postgres")
    linhas = sessao.executar(sql, parametros)
    sessao._reaplicar()
    return linhas


def _inscrever(sessao, email, nome=None, versao=None):
    return sessao.executar(
        "select public.inscrever_na_lista_de_espera(%s, %s, %s)",
        (email, nome, versao if versao is not None else _versao(sessao)),
    )


# ── 1. A estrutura ──────────────────────────────────────────────────────────

def test_rls_ligado_e_nenhuma_policy(catalogo):
    rls = catalogo("select relrowsecurity from pg_class where oid = 'public.lista_de_espera'::regclass")
    assert rls == [(True,)], "RLS desligado na lista de espera"
    policies = catalogo("select policyname from pg_policies where schemaname = 'public' "
                        "and tablename = 'lista_de_espera'")
    assert policies == [], f"a lista nao deve ter policy nenhuma: {policies}"


@pytest.mark.parametrize("papel", ["anon", "authenticated", PAPEL_INGESTAO])
def test_nenhum_papel_do_cliente_tem_privilegio_de_tabela(catalogo, papel):
    # Sem a tabela, a consulta abaixo volta vazia e o teste passaria sem ver nada
    # (medido em 18/11, contra o develop sem a 022: os três passavam).
    assert catalogo("select to_regclass('public.lista_de_espera') is not null")[0][0], "a lista nao existe"
    privilegios = catalogo(
        "select privilege_type from information_schema.table_privileges "
        "where table_schema = 'public' and table_name = 'lista_de_espera' and grantee = %s",
        (papel,),
    )
    assert privilegios == [], f"{papel} tem {privilegios} na lista de espera"


def test_as_funcoes_sao_definer_com_search_path_fixo(catalogo):
    linhas = catalogo(
        """
        select p.proname, p.prosecdef, coalesce(array_to_string(p.proconfig, ','), '')
          from pg_proc p join pg_namespace n on n.oid = p.pronamespace
         where n.nspname = 'public'
           and p.proname in ('inscrever_na_lista_de_espera', 'expurgar_lista_de_espera')
        """
    )
    assert len(linhas) == 2
    for nome, definer, config in linhas:
        assert definer is True, nome
        assert "search_path=" in config.replace(" ", ""), f"{nome} sem search_path fixo"


# ── 2. Quem alcança o quê ───────────────────────────────────────────────────

def test_anon_nao_le_a_lista(como_anon):
    with como_anon() as visitante:
        erro = visitante.negado("select email from public.lista_de_espera")
        assert erro.pgcode == SEM_PRIVILEGIO, erro


def test_anon_nao_insere_direto(como_anon):
    with como_anon() as visitante:
        erro = visitante.negado(
            "insert into public.lista_de_espera (email, consentimento_versao) "
            "values ('direto@exemplo.test', '2026-11-18')")
        assert erro.pgcode == SEM_PRIVILEGIO, erro


def test_anon_nao_chama_a_inscricao(como_anon):
    with como_anon() as visitante:
        erro = visitante.negado("select public.inscrever_na_lista_de_espera('x@exemplo.test', null, '2026-11-18')")
        assert erro.pgcode == SEM_PRIVILEGIO, erro


@pytest.mark.parametrize("comando", [
    "select email from public.lista_de_espera",
    "insert into public.lista_de_espera (email, consentimento_versao) values ('a@exemplo.test', 'x')",
    "update public.lista_de_espera set nome = 'x'",
    "delete from public.lista_de_espera",
    "select public.inscrever_na_lista_de_espera('a@exemplo.test', null, '2026-11-18')",
    "select public.expurgar_lista_de_espera()",
])
def test_uma_conta_qualquer_nao_alcanca_a_lista(como, cenario, comando):
    with como(cenario["ana"]) as ana:
        erro = ana.negado(comando)
        assert erro.pgcode == SEM_PRIVILEGIO, erro


def test_a_ingestao_inscreve_mas_nao_le(como, cenario):
    with como(cenario["ana"], papel=PAPEL_INGESTAO) as ingestao:
        _inscrever(ingestao, "nova@exemplo.test")
        erro = ingestao.negado("select email from public.lista_de_espera")
        assert erro.pgcode == SEM_PRIVILEGIO, erro


def test_ninguem_do_cliente_executa_o_expurgo(catalogo):
    for papel in ("anon", "authenticated", PAPEL_INGESTAO):
        assert catalogo("select has_function_privilege(%s, %s, 'execute')", (papel, F_EXPURGAR))[0][0] is False, papel


def test_so_a_ingestao_executa_a_inscricao(catalogo):
    executa = {papel: catalogo("select has_function_privilege(%s, %s, 'execute')", (papel, F_INSCREVER))[0][0]
               for papel in ("anon", "authenticated", PAPEL_INGESTAO)}
    assert executa == {"anon": False, "authenticated": False, PAPEL_INGESTAO: True}


# ── 3. O que a inscrição grava ─────────────────────────────────────────────

def test_a_inscricao_grava_normalizado_com_a_versao_e_o_relogio_do_banco(como, cenario):
    with como(cenario["ana"], papel=PAPEL_INGESTAO) as ingestao:
        _inscrever(ingestao, "  Maria.Silva@Exemplo.TEST ", "  Maria  ")
        agora = ingestao.executar("select now()")[0][0]
        linhas = _como_dono(ingestao, "select email, nome, consentimento_versao, inscrito_em "
                                      "from public.lista_de_espera")
        assert linhas == [("maria.silva@exemplo.test", "Maria", _versao(ingestao), agora)]


def test_nome_em_branco_vira_nulo(como, cenario):
    with como(cenario["ana"], papel=PAPEL_INGESTAO) as ingestao:
        _inscrever(ingestao, "semnome@exemplo.test", "   ")
        assert _como_dono(ingestao, "select nome from public.lista_de_espera") == [(None,)]


def test_email_repetido_nao_muda_nada_e_nao_e_revelado(como, cenario):
    with como(cenario["ana"], papel=PAPEL_INGESTAO) as ingestao:
        primeira = _inscrever(ingestao, "repetido@exemplo.test", "Primeiro")
        segunda = _inscrever(ingestao, "REPETIDO@exemplo.test", "Outro")
        assert primeira == segunda, "a resposta muda quando o e-mail ja estava na lista"
        assert _como_dono(ingestao, "select email, nome from public.lista_de_espera") == [
            ("repetido@exemplo.test", "Primeiro")]


def test_versao_errada_do_texto_e_recusada(como, cenario):
    with como(cenario["ana"], papel=PAPEL_INGESTAO) as ingestao:
        erro = ingestao.negado("select public.inscrever_na_lista_de_espera('v@exemplo.test', null, '2000-01-01')")
        assert erro.pgcode == CHECK, erro


@pytest.mark.parametrize("email", [
    "", "sem-arroba.exemplo.test", "a@b", "dois@@exemplo.test", "com espaco@exemplo.test",
    "a@exemplo.c", "x" * 250 + "@exemplo.test",
])
def test_email_invalido_e_recusado_pelo_banco(como, cenario, email):
    with como(cenario["ana"], papel=PAPEL_INGESTAO) as ingestao:
        versao = _versao(ingestao)
        erro = ingestao.negado("select public.inscrever_na_lista_de_espera(%s, null, %s)", (email, versao))
        assert erro.pgcode == CHECK, erro


def test_nome_longo_e_recusado(como, cenario):
    with como(cenario["ana"], papel=PAPEL_INGESTAO) as ingestao:
        versao = _versao(ingestao)
        erro = ingestao.negado("select public.inscrever_na_lista_de_espera('n@exemplo.test', %s, %s)",
                               ("n" * 81, versao))
        assert erro.pgcode == CHECK, erro


# ── 4. O teto por hora ──────────────────────────────────────────────────────

def _semear(sessao, quantas, ha):
    _como_dono(
        sessao,
        "insert into public.lista_de_espera (email, consentimento_versao, inscrito_em) "
        "select 'semente' || g || '@exemplo.test', public.versao_da_lista_de_espera(), now() - %s::interval "
        "from generate_series(1, %s) g",
        (ha, quantas),
    )


def test_a_centesima_primeira_inscricao_da_hora_e_recusada(como, cenario):
    with como(cenario["ana"], papel=PAPEL_INGESTAO) as ingestao:
        _semear(ingestao, 99, "5 minutes")
        _inscrever(ingestao, "centesima@exemplo.test")
        versao = _versao(ingestao)
        erro = ingestao.negado("select public.inscrever_na_lista_de_espera('mais@exemplo.test', null, %s)",
                               (versao,))
        assert erro.pgcode == LISTA_CHEIA, erro


def test_inscricoes_de_mais_de_uma_hora_nao_contam_para_o_teto(como, cenario):
    with como(cenario["ana"], papel=PAPEL_INGESTAO) as ingestao:
        _semear(ingestao, 150, "2 hours")
        _inscrever(ingestao, "depois@exemplo.test")
        assert _como_dono(ingestao, "select count(*) from public.lista_de_espera "
                                    "where email = 'depois@exemplo.test'") == [(1,)]


# ── 5. O expurgo dos 12 meses ───────────────────────────────────────────────

def test_o_expurgo_apaga_so_o_que_passou_de_12_meses(como, cenario):
    with como(cenario["ana"], papel=PAPEL_INGESTAO) as ingestao:
        _como_dono(ingestao,
                   "insert into public.lista_de_espera (email, consentimento_versao, inscrito_em) values "
                   "('antiga@exemplo.test', 'v', now() - interval '12 months 1 day'), "
                   "('quase@exemplo.test', 'v', now() - interval '11 months 29 days')")
        apagadas = _como_dono(ingestao, "select public.expurgar_lista_de_espera()")[0][0]
        assert apagadas == 1
        assert _como_dono(ingestao, "select email from public.lista_de_espera") == [("quase@exemplo.test",)]
