"""Serviço fora do ar não é credencial inválida (AUTH-08).

O defeito que estes testes travam: `validar_token_de_usuario` e
`get_device_by_token_hash` devolviam `None` tanto quando o serviço RECUSAVA a
credencial quanto quando ele FALHAVA, e a rota respondia 401 nos dois casos.
O frontend trata 401 como sessão morta e desloga: uma falha momentânea do
Supabase Auth deslogava o usuário. Achado A3/A7 da auditoria de 31/10.

A regra: 401 só quando o serviço recusa; falha do serviço é 503, que o
frontend não trata como logout e que o firmware trata como "recuar e
reenviar". Os testes abaixo verificam o contrato das rotas.
"""
from unittest.mock import patch

import pytest
from flask import Flask
import database
from device_auth import TOKEN_HEADER
from routes import init_routes

LEITURA = {"ax": 0.10, "ay": 0.20, "az": 9.80, "t": 32.0, "total": 9.80, "status": "Repouso"}


def _client():
    app = Flask(__name__)
    init_routes(app)
    app.testing = True
    return app.test_client()


@pytest.mark.parametrize("rota", ["/api/sleep-history", "/api/data"])
def test_fonte_de_autenticacao_indisponivel_responde_503(rota):
    with patch.object(database.db, "validar_token_de_usuario", return_value=database.INDISPONIVEL):
        cliente = _client()
        headers = {"Authorization": "Bearer x"}
        resposta = (cliente.get(rota, headers=headers) if rota == "/api/sleep-history"
                    else cliente.post(rota, json=LEITURA, headers=headers))
    assert resposta.status_code == 503


def test_dispositivo_com_banco_fora_do_ar_responde_503():
    class Explode:
        def rpc(self, *_a, **_k):
            raise RuntimeError("banco fora")
    with patch.object(database.db, "cliente_de_ingestao", return_value=Explode()):
        r1 = _client().post("/api/data", json=LEITURA, headers={TOKEN_HEADER: "t"})
        r2 = _client().post("/api/data/lote", json={"leituras": [LEITURA]},
                            headers={TOKEN_HEADER: "t"})
    assert r1.status_code == 503 and r2.status_code == 503


def test_dispositivo_com_token_que_nao_resolve_continua_401():
    class NaoResolve:
        def rpc(self, *_a, **_k):
            class Execucao:
                def execute(self):
                    class R:
                        data = []
                    return R()
            return Execucao()
    with patch.object(database.db, "cliente_de_ingestao", return_value=NaoResolve()):
        resp = _client().post("/api/data", json=LEITURA, headers={TOKEN_HEADER: "t"})
    assert resp.status_code == 401


def test_indisponivel_e_falso_como_none():
    """Um chamador antigo que só testasse `if not usuario` continua NEGANDO."""
    assert not database.INDISPONIVEL
