"""DATA-16: as rotas de excluir e marcar uma sessão, e o filtro da bancada.

Como o resto de `tests/`, o banco é mockado: o que se verifica aqui é a rota —
a validação do trecho, a confirmação, o repasse do JWT, os códigos — e que as
consultas de features e do histórico levam o filtro e a coluna. A posse e o
alcance de verdade estão em `tests/rls/test_rls_trecho.py`, contra Postgres.
"""
import inspect
from unittest.mock import patch

import pytest
from flask import Flask

import database
import trecho
from routes import init_routes

JWT = "jwt-da-ana"
ID_ANA = "aaaaaaaa-0000-4000-8000-aaaaaaaaaaaa"
DEVICE = "dddddddd-0000-4000-8000-dddddddddddd"
DESDE, ATE = "2026-11-17T02:35:00-03:00", "2026-11-17T09:36:00-03:00"


def _client():
    app = Flask(__name__)
    init_routes(app)
    app.testing = True
    return app.test_client()


def _chamar(caminho, corpo, metodo, retorno=7):
    with patch.object(database.db, "validar_token_de_usuario", return_value=ID_ANA), \
         patch.object(database.db, metodo, return_value=retorno) as banco:
        resposta = _client().post(caminho, json=corpo, headers={"Authorization": f"Bearer {JWT}"})
    return resposta, banco


def _apagar(corpo=None, retorno=7):
    if corpo is None:
        corpo = {"device": DEVICE, "desde": DESDE, "ate": ATE, "confirmacao": trecho.CONFIRMACAO_APAGAR}
    return _chamar("/api/sessoes/apagar", corpo, "apagar_trecho", retorno)


def _marcar(corpo=None, retorno=7):
    if corpo is None:
        corpo = {"device": DEVICE, "desde": DESDE, "ate": ATE, "bancada": True}
    return _chamar("/api/sessoes/marcar", corpo, "marcar_trecho", retorno)


# --- a leitura do trecho ---------------------------------------------------

@pytest.mark.parametrize("corpo,motivo", [
    (None, "corpo JSON obrigatorio"),
    ({"desde": DESDE, "ate": ATE}, "device invalido"),
    ({"device": "nao-e-uuid", "desde": DESDE, "ate": ATE}, "device invalido"),
    ({"device": DEVICE, "ate": ATE}, "'desde' e 'ate' obrigatorios, em ISO 8601"),
    ({"device": DEVICE, "desde": "ontem", "ate": ATE}, "'desde' e 'ate' obrigatorios, em ISO 8601"),
    ({"device": DEVICE, "desde": "2026-11-17T02:35:00", "ate": ATE}, "'desde' e 'ate' precisam de fuso horario"),
    ({"device": DEVICE, "desde": ATE, "ate": DESDE}, "'ate' antes de 'desde'"),
    ({"device": DEVICE, "desde": "2026-11-15T00:00:00Z", "ate": "2026-11-17T00:00:01Z"}, "trecho acima de 48 h"),
])
def test_trecho_invalido_e_recusado_com_motivo(corpo, motivo):
    assert trecho.ler_trecho(corpo) == (None, motivo)


def test_trecho_valido_volta_normalizado():
    lido, erro = trecho.ler_trecho({"device": DEVICE.upper(), "desde": "2026-11-17T05:35:00Z",
                                    "ate": "2026-11-17T12:36:00Z"})
    assert erro is None
    assert lido == (DEVICE, "2026-11-17T05:35:00+00:00", "2026-11-17T12:36:00+00:00")


def test_48h_exatas_sao_aceitas():
    _, erro = trecho.ler_trecho({"device": DEVICE, "desde": "2026-11-15T00:00:00Z",
                                 "ate": "2026-11-17T00:00:00Z"})
    assert erro is None


# --- excluir ---------------------------------------------------------------

def test_apagar_repassa_o_jwt_e_o_trecho_e_devolve_a_contagem():
    resposta, banco = _apagar(retorno=812)
    assert resposta.status_code == 200
    assert resposta.get_json() == {"epocas_apagadas": 812}
    banco.assert_called_once_with(JWT, DEVICE, "2026-11-17T02:35:00-03:00", "2026-11-17T09:36:00-03:00")


@pytest.mark.parametrize("confirmacao", [None, "", "sim", "apagar esta sessao"])
def test_apagar_sem_a_frase_exata_responde_400_e_nao_chama_o_banco(confirmacao):
    corpo = {"device": DEVICE, "desde": DESDE, "ate": ATE}
    if confirmacao is not None:
        corpo["confirmacao"] = confirmacao
    resposta, banco = _apagar(corpo)
    assert resposta.status_code == 400
    assert resposta.get_json()["envie"] == {"confirmacao": trecho.CONFIRMACAO_APAGAR}
    banco.assert_not_called()


def test_apagar_com_trecho_invalido_responde_400_e_nao_chama_o_banco():
    resposta, banco = _apagar({"device": DEVICE, "desde": ATE, "ate": DESDE,
                               "confirmacao": trecho.CONFIRMACAO_APAGAR})
    assert resposta.status_code == 400
    assert resposta.get_json() == {"error": "'ate' antes de 'desde'"}
    banco.assert_not_called()


def test_apagar_com_banco_fora_responde_503():
    resposta, _ = _apagar(retorno=None)
    assert resposta.status_code == 503


def test_apagar_zero_epocas_e_200_com_zero():
    """Trecho sem época do titular (ou de outro aparelho): nada saiu, e isso é
    resposta, não erro."""
    resposta, _ = _apagar(retorno=0)
    assert resposta.status_code == 200
    assert resposta.get_json() == {"epocas_apagadas": 0}


# --- marcar ----------------------------------------------------------------

@pytest.mark.parametrize("bancada", [True, False])
def test_marcar_e_desmarcar_repassam_a_marca(bancada):
    resposta, banco = _marcar({"device": DEVICE, "desde": DESDE, "ate": ATE, "bancada": bancada}, retorno=3)
    assert resposta.status_code == 200
    assert resposta.get_json() == {"epocas_marcadas": 3, "bancada": bancada}
    banco.assert_called_once_with(JWT, DEVICE, "2026-11-17T02:35:00-03:00", "2026-11-17T09:36:00-03:00", bancada)


@pytest.mark.parametrize("bancada", [None, "true", 1, 0])
def test_marcar_sem_booleano_responde_400(bancada):
    corpo = {"device": DEVICE, "desde": DESDE, "ate": ATE}
    if bancada is not None:
        corpo["bancada"] = bancada
    resposta, banco = _marcar(corpo)
    assert resposta.status_code == 400
    banco.assert_not_called()


def test_marcar_com_banco_fora_responde_503():
    resposta, _ = _marcar(retorno=None)
    assert resposta.status_code == 503


@pytest.mark.parametrize("caminho", ["/api/sessoes/apagar", "/api/sessoes/marcar"])
def test_sem_jwt_e_401(caminho):
    resposta = _client().post(caminho, json={})
    assert resposta.status_code == 401


# --- as consultas ----------------------------------------------------------

def test_features_e_inferencia_ignoram_a_bancada():
    """`/api/features` e `/api/inferencia` usam a mesma consulta."""
    fonte = inspect.getsource(database.Database.get_features_do_usuario)
    assert '.eq("bancada", False)' in fonte


def test_o_historico_devolve_a_marca():
    """O Histórico mostra as marcadas numa seção própria: a linha tem de vir
    com a marca, e não filtrada no servidor."""
    fonte = inspect.getsource(database.Database.get_leituras_do_usuario)
    assert '"bancada"' in fonte
    assert '.eq("bancada"' not in fonte


@pytest.mark.parametrize("metodo,funcao", [("apagar_trecho", "apagar_trecho"), ("marcar_trecho", "marcar_trecho")])
def test_as_operacoes_usam_o_cliente_do_usuario(metodo, funcao):
    fonte = inspect.getsource(getattr(database.Database, metodo))
    assert "self.cliente_do_usuario(jwt)" in fonte
    assert f'client.rpc("{funcao}"' in fonte
