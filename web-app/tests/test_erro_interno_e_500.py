"""Bug do servidor não é payload inválido (API-04).

O defeito que estes testes travam: `/api/data` e `/api/data/lote` tinham um
`except Exception` que respondia 400 com `str(e)` no corpo. Para o firmware,
400 quer dizer "leitura inválida, não adianta reenviar", e ele a descarta: um
defeito NOSSO apagava uma leitura boa do dispositivo. E o texto da exceção
saía para fora. Achado A4 da auditoria de 31/10.

A regra:
  - erro HTTP do próprio Flask (JSON quebrado, `Content-Type` errado) é culpa
    do pedido e mantém o código dele (400, 415);
  - qualquer outra exceção é 500 "erro interno", com o detalhe só no log;
  - no lote, exceção num item deixa ele e os seguintes PENDENTES, e não
    rejeitados (o firmware reenvia pendente; rejeitada ele apaga).
"""
from unittest.mock import patch

import pytest
from flask import Flask

import database
from device_auth import TOKEN_HEADER
from routes import init_routes

_DEVICE = {"id": "dev-uuid-1", "user_id": "user-uuid-1", "revoked_at": None,
           "token_hash": "h"}
_AUTH = {TOKEN_HEADER: "token-de-teste"}
_LEITURA = {"ax": 0.10, "ay": 0.20, "az": 9.80, "gx": 0.0, "gy": 0.0, "gz": 0.0,
            "t": 32.0, "total": 9.80, "status": "Repouso"}
_SEGREDO = "detalhe-interno-que-nao-pode-sair"


def _client():
    app = Flask(__name__)
    init_routes(app)
    app.testing = True
    return app.test_client()


def _com_device():
    return patch.object(database.db, "get_device_by_token_hash", return_value=_DEVICE)


def _gravacao_que_levanta():
    return patch.object(database.db, "registrar_leitura",
                        side_effect=RuntimeError(_SEGREDO))


def test_excecao_na_gravacao_responde_500_e_nao_400():
    with _com_device(), _gravacao_que_levanta():
        resp = _client().post("/api/data", json=_LEITURA, headers=_AUTH)
    assert resp.status_code == 500
    assert resp.get_json() == {"error": "erro interno"}


def test_texto_da_excecao_nao_sai_no_corpo():
    with _com_device(), _gravacao_que_levanta():
        resp = _client().post("/api/data", json=_LEITURA, headers=_AUTH)
    assert _SEGREDO not in resp.get_data(as_text=True)


def test_excecao_vai_para_o_log(caplog):
    """O detalhe que saiu do corpo precisa estar em algum lugar: no log da Vercel."""
    with _com_device(), _gravacao_que_levanta(), caplog.at_level("ERROR", logger="routes"):
        _client().post("/api/data", json=_LEITURA, headers=_AUTH)
    assert any(_SEGREDO in (r.exc_text or "") or (r.exc_info and _SEGREDO in str(r.exc_info[1]))
               for r in caplog.records)


def test_excecao_fora_do_item_do_lote_responde_500():
    """Exceção antes do laço (aqui, na autenticação) não tem item onde cair."""
    with patch.object(database.db, "get_device_by_token_hash",
                      side_effect=RuntimeError(_SEGREDO)):
        resp = _client().post("/api/data/lote", json={"leituras": [_LEITURA]},
                              headers=_AUTH)
    assert resp.status_code == 500
    assert _SEGREDO not in resp.get_data(as_text=True)


def test_lote_com_excecao_no_primeiro_item_nada_gravado_e_503():
    """Nada aceito e tudo pendente: 503, para o firmware recuar e reenviar."""
    with _com_device(), _gravacao_que_levanta():
        resp = _client().post("/api/data/lote", json={"leituras": [_LEITURA] * 3},
                              headers=_AUTH)
    corpo = resp.get_json()
    assert resp.status_code == 503
    assert corpo["aceitas"] == [] and corpo["rejeitadas"] == []
    assert corpo["pendentes"] == [0, 1, 2]
    assert _SEGREDO not in resp.get_data(as_text=True)


def test_json_quebrado_continua_400():
    with _com_device():
        resp = _client().post("/api/data", data="{nao e json",
                              content_type="application/json", headers=_AUTH)
    assert resp.status_code == 400


def test_sem_content_type_json_e_415_e_nao_500():
    """Antes virava 400 pelo `except` genérico; o código certo é o do Flask."""
    with _com_device():
        resp = _client().post("/api/data", data="ax=1", headers=_AUTH)
    assert resp.status_code == 415


@pytest.mark.parametrize("rota", ["/api/data", "/api/data/lote"])
def test_leitura_invalida_continua_400_ou_rejeitada(rota):
    """A validação não levanta: leitura ruim segue sendo culpa do pedido."""
    invalida = dict(_LEITURA, total=3.0)
    corpo = invalida if rota == "/api/data" else {"leituras": [invalida]}
    with _com_device(), patch.object(database.db, "registrar_leitura", return_value=1):
        resp = _client().post(rota, json=corpo, headers=_AUTH)
    if rota == "/api/data":
        assert resp.status_code == 400
    else:
        assert resp.get_json()["rejeitadas"][0]["indice"] == 0
