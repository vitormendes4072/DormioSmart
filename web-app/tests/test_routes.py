"""Testes das rotas da API: leitura (FIX-01) e escrita (FIX-02).

Objetivo: garantir que /api/sleep-history nunca devolva 500 (degrada para
lista vazia), que /api/data não minta sucesso — respondendo 503 quando nada
persiste — e que as páginas / e /dashboard retornem 200. O Supabase é sempre
mockado — nenhum teste depende de credencial ou rede.
"""
from unittest.mock import patch

import os
from flask import Flask

import database
from device_auth import TOKEN_HEADER
from routes import init_routes


# SEC-02: POST /api/data passou a exigir X-Device-Token. Os testes abaixo
# verificam persistência (FIX-02), não autenticação — então autenticam com um
# device válido mockado. A autenticação em si é coberta em test_device_auth.py.
_DEVICE = {"id": "dev-uuid-1", "user_id": "user-uuid-1", "revoked_at": None}
_AUTH = {TOKEN_HEADER: "token-de-teste"}

# SEC-03: o corpo passou a ser validado por completo. Estes testes verificam
# persistência (FIX-02), não validação — então usam uma leitura válida. As
# regras de validação em si estão em test_validacao.py.
_LEITURA = {"ax": 0.10, "ay": 0.20, "az": 9.80, "gx": 0.0, "gy": 0.0, "gz": 0.0,
            "t": 32.0, "total": 9.80, "status": "Repouso"}

# AUTH-03: /api/sleep-history passou a exigir JWT. Estes testes verificam a
# resiliencia da leitura (FIX-01), nao a autenticacao — entao autenticam com
# um usuario mockado. A autenticacao em si esta em test_auth_usuario.py.
_JWT = "jwt-de-teste"
_USUARIO = "user-uuid-1"
_SESSAO = {"Authorization": f"Bearer {_JWT}"}


def _client():
    app = Flask(__name__)
    init_routes(app)
    app.testing = True
    return app.test_client()


def test_history_retorna_dados():
    amostra = [
        {
            "created_at": "2026-06-03T00:00:00Z",
            "movimento_total": 9.8,
            "temp": 24.0,
            "status": "Dormindo",
        }
    ]
    with patch.object(database.db, "validar_token_de_usuario", return_value=_USUARIO),          patch.object(database.db, "get_leituras_do_usuario", return_value=amostra):
        resp = _client().get("/api/sleep-history", headers=_SESSAO)
    assert resp.status_code == 200
    assert resp.get_json() == amostra


def test_history_vazio_retorna_200():
    with patch.object(database.db, "validar_token_de_usuario", return_value=_USUARIO),          patch.object(database.db, "get_leituras_do_usuario", return_value=[]):
        resp = _client().get("/api/sleep-history", headers=_SESSAO)
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_get_latest_data_vazio_sem_cliente():
    # Sem cliente Supabase (credenciais ausentes) → lista vazia, sem exceção.
    with patch.object(database.db, "get_client", return_value=None):
        assert database.db.get_latest_data() == []


def test_get_latest_data_vazio_em_excecao():
    # Consulta que lança exceção → tratada, devolve [] (nunca propaga → nunca 500).
    class ClienteRuim:
        def table(self, *args, **kwargs):
            raise RuntimeError("falha simulada")

    with patch.object(database.db, "get_client", return_value=ClienteRuim()):
        assert database.db.get_latest_data() == []


def test_receive_data_persistido_retorna_201():
    # Insert bem-sucedido (resposta com .data) → 201.
    class RespOK:
        data = [{"id": 1}]

    with patch.object(database.db, "get_device_by_token_hash", return_value=_DEVICE),          patch.object(database.db, "insert_sleep_data", return_value=RespOK()),          patch.object(database.db, "touch_device"):
        resp = _client().post("/api/data", json=_LEITURA, headers=_AUTH)
    assert resp.status_code == 201
    assert resp.get_json()["status"] == "success"


def test_receive_data_nao_persistido_retorna_503():
    # Nada persistiu (cliente indisponível → None) → 503, sem mentir sucesso (FIX-02).
    with patch.object(database.db, "get_device_by_token_hash", return_value=_DEVICE),          patch.object(database.db, "insert_sleep_data", return_value=None):
        resp = _client().post("/api/data", json=_LEITURA, headers=_AUTH)
    assert resp.status_code == 503


def test_receive_data_json_invalido_retorna_400():
    # Corpo não-JSON → erro de parse tratado → 400 (comportamento preservado).
    with patch.object(database.db, "get_device_by_token_hash", return_value=_DEVICE):
        resp = _client().post(
            "/api/data", data="nao-e-json", content_type="application/json", headers=_AUTH
        )
    assert resp.status_code == 400



