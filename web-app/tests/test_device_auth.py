"""Testes da autenticação do dispositivo (SEC-02).

Regra: `POST /api/data` só persiste se o `X-Device-Token` resolver para um
dispositivo ativo. Token ausente, desconhecido ou revogado → 401, sem tocar no
banco. O `user_id` da linha vem SEMPRE do token, nunca do corpo — o device não
escolhe de quem é o dado que envia.
"""
from unittest.mock import patch

import os
from flask import Flask

import database
from device_auth import TOKEN_HEADER, gerar_token, hash_token
from routes import init_routes


TOKEN = "token-de-teste"
DEVICE = {"id": "dev-uuid-1", "user_id": "user-uuid-1", "revoked_at": None}
LEITURA = {"ax": 0.1, "ay": 0.2, "az": 9.8, "gx": 0.0, "gy": 0.0, "gz": 0.0,
           "t": 32.0, "total": 9.80, "status": "Repouso"}


def _client():
    app = Flask(__name__)
    init_routes(app)
    app.testing = True
    return app.test_client()


class _ResultadoOk:
    data = [{"id": 1}]


# --- hashing -------------------------------------------------------------

def test_token_gerado_nao_se_repete():
    assert gerar_token() != gerar_token()


def test_hash_e_deterministico_e_nao_devolve_o_token():
    assert hash_token(TOKEN) == hash_token(TOKEN)
    assert TOKEN not in hash_token(TOKEN)
    assert len(hash_token(TOKEN)) == 64  # SHA-256 em hex


# --- rejeição ------------------------------------------------------------

def test_sem_token_responde_401_e_nao_persiste():
    with patch.object(database.db, "insert_sleep_data") as insert:
        resp = _client().post("/api/data", json=LEITURA)
    assert resp.status_code == 401
    insert.assert_not_called()


def test_token_vazio_responde_401():
    with patch.object(database.db, "insert_sleep_data") as insert:
        resp = _client().post("/api/data", json=LEITURA, headers={TOKEN_HEADER: "   "})
    assert resp.status_code == 401
    insert.assert_not_called()


def test_token_desconhecido_responde_401_e_nao_persiste():
    with patch.object(database.db, "get_device_by_token_hash", return_value=None), \
         patch.object(database.db, "insert_sleep_data") as insert:
        resp = _client().post("/api/data", json=LEITURA, headers={TOKEN_HEADER: "invalido"})
    assert resp.status_code == 401
    insert.assert_not_called()


def test_token_revogado_responde_401():
    """A camada de banco devolve None para device revogado (soft delete)."""
    with patch.object(database.db, "get_device_by_token_hash", return_value=None), \
         patch.object(database.db, "insert_sleep_data") as insert:
        resp = _client().post("/api/data", json=LEITURA, headers={TOKEN_HEADER: TOKEN})
    assert resp.status_code == 401
    insert.assert_not_called()


def test_resposta_401_nao_revela_qual_e_o_caso():
    """Ausente e inválido devem ser indistinguíveis para quem sonda tokens."""
    c = _client()
    sem = c.post("/api/data", json=LEITURA)
    with patch.object(database.db, "get_device_by_token_hash", return_value=None):
        invalido = c.post("/api/data", json=LEITURA, headers={TOKEN_HEADER: "x"})
    assert sem.status_code == invalido.status_code == 401
    assert "revogado" not in invalido.get_json()["error"].lower()


# --- aceitação -----------------------------------------------------------

def test_token_valido_persiste_e_responde_201():
    with patch.object(database.db, "get_device_by_token_hash", return_value=DEVICE), \
         patch.object(database.db, "insert_sleep_data", return_value=_ResultadoOk()), \
         patch.object(database.db, "touch_device"):
        resp = _client().post("/api/data", json=LEITURA, headers={TOKEN_HEADER: TOKEN})
    assert resp.status_code == 201


def test_linha_recebe_dono_resolvido_pelo_token():
    with patch.object(database.db, "get_device_by_token_hash", return_value=DEVICE), \
         patch.object(database.db, "insert_sleep_data", return_value=_ResultadoOk()) as insert, \
         patch.object(database.db, "touch_device"):
        _client().post("/api/data", json=LEITURA, headers={TOKEN_HEADER: TOKEN})

    gravado = insert.call_args[0][0]
    assert gravado["user_id"] == DEVICE["user_id"]
    assert gravado["device_id"] == DEVICE["id"]


def test_corpo_nao_consegue_forjar_o_dono():
    """user_id enviado pelo device é ignorado — quem manda é o token."""
    intruso = dict(LEITURA, user_id="user-de-outra-pessoa", device_id="dev-falso")
    with patch.object(database.db, "get_device_by_token_hash", return_value=DEVICE), \
         patch.object(database.db, "insert_sleep_data", return_value=_ResultadoOk()) as insert, \
         patch.object(database.db, "touch_device"):
        _client().post("/api/data", json=intruso, headers={TOKEN_HEADER: TOKEN})

    gravado = insert.call_args[0][0]
    assert gravado["user_id"] == DEVICE["user_id"]
    assert gravado["device_id"] == DEVICE["id"]


def test_last_seen_atualizado_apos_persistir():
    with patch.object(database.db, "get_device_by_token_hash", return_value=DEVICE), \
         patch.object(database.db, "insert_sleep_data", return_value=_ResultadoOk()), \
         patch.object(database.db, "touch_device") as touch:
        _client().post("/api/data", json=LEITURA, headers={TOKEN_HEADER: TOKEN})
    touch.assert_called_once_with(DEVICE["id"])


def test_falha_de_persistencia_ainda_responde_503():
    """SEC-02 não pode ter quebrado o FIX-02: autenticado mas sem gravar = 503."""
    with patch.object(database.db, "get_device_by_token_hash", return_value=DEVICE), \
         patch.object(database.db, "insert_sleep_data", return_value=None):
        resp = _client().post("/api/data", json=LEITURA, headers={TOKEN_HEADER: TOKEN})
    assert resp.status_code == 503
