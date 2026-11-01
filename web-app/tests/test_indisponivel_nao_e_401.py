"""Serviço fora do ar não é credencial inválida (AUTH-08).

O defeito que estes testes travam: `validar_token_de_usuario` e
`get_device_by_token_hash` devolviam `None` tanto quando o serviço RECUSAVA a
credencial quanto quando ele FALHAVA, e a rota respondia 401 nos dois casos.
O frontend trata 401 como sessão morta e desloga: uma falha momentânea do
Supabase Auth deslogava o usuário. Achado A3/A7 da auditoria de 31/10.

A regra: 401 só quando o serviço recusa; falha do serviço é 503, que o
frontend não trata como logout e que o firmware trata como "recuar e
reenviar". As exceções usadas aqui são as da própria biblioteca
(`supabase_auth` 2.24), com as assinaturas dela.
"""
from unittest.mock import patch

import pytest
from flask import Flask
from supabase_auth.errors import (
    AuthApiError,
    AuthInvalidJwtError,
    AuthRetryableError,
    AuthUnknownError,
)

import database
from device_auth import TOKEN_HEADER
from routes import init_routes

LEITURA = {"ax": 0.10, "ay": 0.20, "az": 9.80, "t": 32.0, "total": 9.80, "status": "Repouso"}


def _client():
    app = Flask(__name__)
    init_routes(app)
    app.testing = True
    return app.test_client()


def _auth_que_levanta(erro):
    class Cliente:
        class auth:
            @staticmethod
            def get_user(_):
                raise erro
    return Cliente()


RECUSAS = [
    AuthApiError("invalid JWT", 401, "bad_jwt"),
    AuthApiError("user not found", 403, "user_not_found"),
    AuthInvalidJwtError("malformed"),
]
FALHAS = [
    AuthRetryableError("timeout", 0),
    AuthRetryableError("bad gateway", 502),
    AuthApiError("internal", 500, None),
    AuthUnknownError("?", RuntimeError("x")),
    RuntimeError("rede"),
]


@pytest.mark.parametrize("erro", RECUSAS, ids=lambda e: type(e).__name__)
def test_auth_que_recusa_o_token_continua_401(erro):
    with patch.object(database.db, "_get_client_anon", return_value=_auth_que_levanta(erro)):
        resp = _client().get("/api/sleep-history", headers={"Authorization": "Bearer x"})
    assert resp.status_code == 401


@pytest.mark.parametrize("erro", FALHAS, ids=lambda e: f"{type(e).__name__}")
def test_auth_que_falha_vira_503_e_nao_desloga(erro):
    with patch.object(database.db, "_get_client_anon", return_value=_auth_que_levanta(erro)):
        resp = _client().get("/api/sleep-history", headers={"Authorization": "Bearer x"})
    assert resp.status_code == 503
    assert "indisponivel" in resp.get_json()["error"]


def test_cliente_anon_sem_configuracao_e_indisponivel_e_nao_recusa():
    """Servidor mal configurado não é culpa do token do usuário."""
    with patch.object(database.db, "_get_client_anon", return_value=None):
        assert database.db.validar_token_de_usuario("x") is database.INDISPONIVEL


@pytest.mark.parametrize("erro", FALHAS, ids=lambda e: type(e).__name__)
def test_caminho_do_celular_tambem_responde_503(erro):
    """POST /api/data com sessão: o mesmo validador, outra rota (routes.py)."""
    with patch.object(database.db, "_get_client_anon", return_value=_auth_que_levanta(erro)):
        resp = _client().post("/api/data", json=dict(LEITURA, device_id="d"),
                              headers={"Authorization": "Bearer x"})
    assert resp.status_code == 503


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
