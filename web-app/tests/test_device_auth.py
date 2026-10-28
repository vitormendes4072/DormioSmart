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


# `registrar_leitura` devolve o id da linha criada (SEC-06), nao mais o objeto
# de resposta do PostgREST: a gravacao virou uma chamada de funcao no banco.
ID_GRAVADO = 4242


# --- hashing -------------------------------------------------------------

def test_token_gerado_nao_se_repete():
    assert gerar_token() != gerar_token()


def test_hash_e_deterministico_e_nao_devolve_o_token():
    assert hash_token(TOKEN) == hash_token(TOKEN)
    assert TOKEN not in hash_token(TOKEN)
    assert len(hash_token(TOKEN)) == 64  # SHA-256 em hex


# --- rejeição ------------------------------------------------------------

def test_sem_token_responde_401_e_nao_persiste():
    with patch.object(database.db, "registrar_leitura") as gravar:
        resp = _client().post("/api/data", json=LEITURA)
    assert resp.status_code == 401
    gravar.assert_not_called()


def test_token_vazio_responde_401():
    with patch.object(database.db, "registrar_leitura") as gravar:
        resp = _client().post("/api/data", json=LEITURA, headers={TOKEN_HEADER: "   "})
    assert resp.status_code == 401
    gravar.assert_not_called()


def test_token_desconhecido_responde_401_e_nao_persiste():
    with patch.object(database.db, "get_device_by_token_hash", return_value=None), \
         patch.object(database.db, "registrar_leitura") as gravar:
        resp = _client().post("/api/data", json=LEITURA, headers={TOKEN_HEADER: "invalido"})
    assert resp.status_code == 401
    gravar.assert_not_called()


def test_token_revogado_responde_401():
    """A camada de banco devolve None para device revogado (soft delete)."""
    with patch.object(database.db, "get_device_by_token_hash", return_value=None), \
         patch.object(database.db, "registrar_leitura") as gravar:
        resp = _client().post("/api/data", json=LEITURA, headers={TOKEN_HEADER: TOKEN})
    assert resp.status_code == 401
    gravar.assert_not_called()


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
         patch.object(database.db, "registrar_leitura", return_value=ID_GRAVADO):
        resp = _client().post("/api/data", json=LEITURA, headers={TOKEN_HEADER: TOKEN})
    assert resp.status_code == 201


def test_a_gravacao_recebe_o_hash_do_token_e_nao_o_dono():
    """O dono deixou de ser carimbado em Python (SEC-06).

    Antes, a rota montava `"user_id": device["user_id"]` no payload. Estava
    correto, mas era uma linha de Python entre uma chave vazada e a posse de
    dado alheio. Agora a rota passa o HASH DO TOKEN, e quem resolve o dono é
    `registrar_leitura` dentro do banco — onde não existe parâmetro para
    escolhê-lo. Ver `migrations/005` e `tests/rls/test_rls_ingestao.py`.
    """
    with patch.object(database.db, "get_device_by_token_hash", return_value=DEVICE), \
         patch.object(database.db, "registrar_leitura", return_value=ID_GRAVADO) as gravar:
        _client().post("/api/data", json=LEITURA, headers={TOKEN_HEADER: TOKEN})

    token_hash, gravado = gravar.call_args[0]
    assert token_hash == hash_token(TOKEN), "a gravacao nao recebeu o hash do token"
    assert "user_id" not in gravado, (
        "o dono voltou a ser montado em Python — isso desfaz a SEC-06"
    )
    assert "device_id" not in gravado


def test_corpo_nao_consegue_forjar_o_dono():
    """user_id enviado pelo device é ignorado — quem manda é o token.

    Duas barreiras agora, e esta cobre a primeira: a rota não repassa `user_id`
    nem `device_id` do corpo. A segunda é a própria função no banco, que extrai
    coluna por coluna — coberta por
    `tests/rls/test_rls_ingestao.py::test_a_ingestao_nao_escolhe_o_dono_pelo_json`.
    """
    intruso = dict(LEITURA, user_id="user-de-outra-pessoa", device_id="dev-falso")
    with patch.object(database.db, "get_device_by_token_hash", return_value=DEVICE), \
         patch.object(database.db, "registrar_leitura", return_value=ID_GRAVADO) as gravar:
        _client().post("/api/data", json=intruso, headers={TOKEN_HEADER: TOKEN})

    _, gravado = gravar.call_args[0]
    assert "user_id" not in gravado
    assert "device_id" not in gravado
    assert "user-de-outra-pessoa" not in str(gravado)


def test_last_seen_atualiza_na_mesma_chamada_da_gravacao():
    """`touch_device` deixou de existir como chamada separada (SEC-06).

    O `last_seen_at` passou a ser atualizado dentro de `registrar_leitura`, na
    mesma transação. Era uma segunda ida ao banco com a chave privilegiada, e
    cada uma dessas era superfície a eliminar. O efeito em si é verificado
    contra o Postgres real em `tests/rls/test_rls_ingestao.py::
    test_registrar_leitura_atualiza_o_ultimo_contato`.
    """
    assert not hasattr(database.db, "touch_device"), (
        "`touch_device` reapareceu: o ultimo contato pertence a "
        "`registrar_leitura`, para nao haver segunda chamada privilegiada"
    )


def test_falha_de_persistencia_ainda_responde_503():
    """SEC-02 não pode ter quebrado o FIX-02: autenticado mas sem gravar = 503."""
    with patch.object(database.db, "get_device_by_token_hash", return_value=DEVICE), \
         patch.object(database.db, "registrar_leitura", return_value=None):
        resp = _client().post("/api/data", json=LEITURA, headers={TOKEN_HEADER: TOKEN})
    assert resp.status_code == 503
