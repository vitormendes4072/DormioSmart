"""A rota da lista de espera (UI-14).

A garantia é do banco (migração 022; `tests/rls/test_rls_lista_de_espera.py`). Aqui se trava o
que o backend faz antes e depois dele: validar e dizer qual campo está errado, descartar o pedido
do campo-isca sem avisar, exigir as duas confirmações e a versão vigente, responder igual para
e-mail novo e repetido, e transformar o teto do banco em 429 e a falha em 503. E as três
constantes de versão (banco, backend, frontend) iguais.
"""
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask
from postgrest.exceptions import APIError

import database
import lista_de_espera
from routes import init_routes

RAIZ = Path(__file__).resolve().parents[2]
ROTA = "/api/lista-de-espera"


def _client():
    app = Flask(__name__)
    init_routes(app)
    app.testing = True
    return app.test_client()


def _pedido(**mudancas):
    corpo = {"email": "Maria@Exemplo.com", "nome": "  Maria   Silva ", "consentimento": True,
             "maioridade": True, "versao": lista_de_espera.VERSAO, "site": ""}
    corpo.update(mudancas)
    return {k: v for k, v in corpo.items() if v is not ...}


def _banco(resultado="inscrito"):
    return patch.object(database.db, "inscrever_na_lista_de_espera", return_value=resultado)


# --- as três versões ----------------------------------------------------------

def test_a_versao_e_a_mesma_no_banco_no_backend_e_no_frontend():
    sql = (RAIZ / "web-app" / "migrations" / "022_lista_de_espera.sql").read_text(encoding="utf-8")
    banco = re.search(r"versao_da_lista_de_espera\(\).*?select '([^']+)'::text", sql, re.S).group(1)
    ts = (RAIZ / "frontend" / "src" / "lib" / "listaDeEspera.ts").read_text(encoding="utf-8")
    frontend = re.search(r'VERSAO_DA_LISTA\s*=\s*"([^"]+)"', ts).group(1)
    assert banco == lista_de_espera.VERSAO == frontend


def test_o_formato_de_email_do_flask_e_o_do_banco():
    """O Flask não pode aceitar o que a restrição do banco recusa (viraria 503 sem explicação)."""
    sql = (RAIZ / "web-app" / "migrations" / "022_lista_de_espera.sql").read_text(encoding="utf-8")
    banco = re.search(r"email ~ '([^']+)'", sql).group(1).replace("[:space:]", r"\s")
    assert banco == lista_de_espera._EMAIL.pattern


# --- o caminho feliz ------------------------------------------------------------

def test_inscricao_valida_grava_normalizado_e_responde_200():
    with _banco() as banco:
        resp = _client().post(ROTA, json=_pedido())
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "inscrito"}
    banco.assert_called_once_with("maria@exemplo.com", "Maria Silva", lista_de_espera.VERSAO)


def test_sem_nome_grava_nulo():
    with _banco() as banco:
        resp = _client().post(ROTA, json=_pedido(nome=...))
    assert resp.status_code == 200
    banco.assert_called_once_with("maria@exemplo.com", None, lista_de_espera.VERSAO)


def test_nome_so_com_espacos_grava_nulo():
    with _banco() as banco:
        _client().post(ROTA, json=_pedido(nome="   "))
    assert banco.call_args.args[1] is None


# --- o campo-isca -----------------------------------------------------------------

def test_campo_isca_preenchido_responde_igual_e_nao_grava():
    with _banco() as banco:
        resp = _client().post(ROTA, json=_pedido(site="http://spam.example"))
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "inscrito"}
    banco.assert_not_called()


def test_isca_vence_mesmo_com_o_resto_invalido():
    """O robô não pode aprender pela mensagem de erro que o campo-isca o denunciou."""
    with _banco() as banco:
        resp = _client().post(ROTA, json={"site": "x", "email": "nada"})
    assert resp.status_code == 200
    banco.assert_not_called()


# --- a validação ------------------------------------------------------------------

@pytest.mark.parametrize("email", ["", "sem-arroba", "a@b", "a@b.c", "com espaco@exemplo.com",
                                   "x" * 250 + "@exemplo.com", 42, None])
def test_email_invalido_e_400_com_o_campo(email):
    with _banco() as banco:
        resp = _client().post(ROTA, json=_pedido(email=email))
    assert resp.status_code == 400
    assert resp.get_json()["campo"] == "email"
    banco.assert_not_called()


def test_nome_longo_e_400():
    with _banco() as banco:
        resp = _client().post(ROTA, json=_pedido(nome="n" * 81))
    assert resp.status_code == 400 and resp.get_json()["campo"] == "nome"
    banco.assert_not_called()


@pytest.mark.parametrize("campo", ["consentimento", "maioridade"])
@pytest.mark.parametrize("valor", [False, "true", 1, None, ...])
def test_sem_as_duas_confirmacoes_marcadas_e_400(campo, valor):
    with _banco() as banco:
        resp = _client().post(ROTA, json=_pedido(**{campo: valor}))
    assert resp.status_code == 400 and resp.get_json()["campo"] == campo
    banco.assert_not_called()


def test_versao_antiga_do_texto_e_409_com_a_vigente():
    with _banco() as banco:
        resp = _client().post(ROTA, json=_pedido(versao="2000-01-01"))
    assert resp.status_code == 409
    assert resp.get_json()["versao_vigente"] == lista_de_espera.VERSAO
    banco.assert_not_called()


def test_campo_desconhecido_e_400():
    with _banco() as banco:
        resp = _client().post(ROTA, json=_pedido(user_id="outra-conta"))
    assert resp.status_code == 400
    banco.assert_not_called()


@pytest.mark.parametrize("corpo", [[], "texto", 3])
def test_corpo_que_nao_e_objeto_e_400(corpo):
    with _banco() as banco:
        resp = _client().post(ROTA, json=corpo)
    assert resp.status_code == 400
    banco.assert_not_called()


def test_sem_json_e_415():
    with _banco() as banco:
        resp = _client().post(ROTA, data="email=a@b.com", content_type="application/x-www-form-urlencoded")
    assert resp.status_code == 415
    banco.assert_not_called()


def test_corpo_grande_demais_e_413():
    with _banco() as banco:
        resp = _client().post(ROTA, json=_pedido(nome="n" * 3000))
    assert resp.status_code == 413
    banco.assert_not_called()


# --- o que volta do banco --------------------------------------------------------

def test_teto_do_banco_vira_429_com_retry_after():
    with _banco("lista_cheia"):
        resp = _client().post(ROTA, json=_pedido())
    assert resp.status_code == 429
    assert resp.headers["Retry-After"] == "600"


def test_banco_fora_do_ar_e_503():
    with _banco(None):
        resp = _client().post(ROTA, json=_pedido())
    assert resp.status_code == 503


def test_a_rota_nao_exige_sessao():
    """Quem se inscreve não tem conta: nenhum cabeçalho de autorização."""
    with _banco():
        resp = _client().post(ROTA, json=_pedido())
    assert resp.status_code == 200


# --- a camada do banco ------------------------------------------------------------

def _cliente_de_ingestao(efeito=None):
    c = MagicMock()
    if efeito is not None:
        c.rpc.return_value.execute.side_effect = efeito
    return patch.object(database.db, "cliente_de_ingestao", return_value=c), c


def test_o_banco_e_chamado_pela_funcao_com_os_tres_parametros():
    contexto, c = _cliente_de_ingestao()
    with contexto:
        assert database.db.inscrever_na_lista_de_espera("a@exemplo.com", None, "v") == "inscrito"
    c.rpc.assert_called_once_with("inscrever_na_lista_de_espera",
                                  {"p_email": "a@exemplo.com", "p_nome": None, "p_versao": "v"})
    c.table.assert_not_called()


def test_pt429_do_banco_vira_lista_cheia():
    contexto, _ = _cliente_de_ingestao(APIError({"code": "PT429", "message": "lista_cheia"}))
    with contexto:
        assert database.db.inscrever_na_lista_de_espera("a@exemplo.com", None, "v") == "lista_cheia"


@pytest.mark.parametrize("erro", [APIError({"code": "23514", "message": "check"}), RuntimeError("rede")])
def test_outra_falha_do_banco_vira_none(erro):
    contexto, _ = _cliente_de_ingestao(erro)
    with contexto:
        assert database.db.inscrever_na_lista_de_espera("a@exemplo.com", None, "v") is None


def test_sem_cliente_vira_none():
    with patch.object(database.db, "cliente_de_ingestao", return_value=None):
        assert database.db.inscrever_na_lista_de_espera("a@exemplo.com", None, "v") is None
