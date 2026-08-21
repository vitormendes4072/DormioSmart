"""Testes das rotas de dispositivos (AUTH-05).

O que importa verificar aqui: nenhuma rota responde sem JWT, o `user_id` vem
sempre do token (nunca do corpo ou da URL), o token em claro sai uma única vez
e o hash nunca vaza para o cliente.
"""
from unittest.mock import MagicMock, patch

import os
from flask import Flask

import database
import dispositivos
from device_auth import hash_token
from routes import init_routes

_TEMPLATES = os.path.join(os.path.dirname(__file__), "..", "templates")
_STATIC = os.path.join(os.path.dirname(__file__), "..", "static")

JWT = "jwt-da-ana"
ID_ANA = "11111111-1111-1111-1111-111111111111"
ID_BRUNO = "22222222-2222-2222-2222-222222222222"
DEVICE = {
    "id": "dev-1",
    "nome": "ESP32 do quarto",
    "created_at": "2026-08-20T03:00:00Z",
    "last_seen_at": None,
    "revoked_at": None,
}


def _client():
    app = Flask(__name__, template_folder=_TEMPLATES, static_folder=_STATIC)
    init_routes(app)
    app.testing = True
    return app.test_client()


def _autenticado():
    return patch.object(database.db, "validar_token_de_usuario", return_value=ID_ANA)


_SESSAO = {"Authorization": f"Bearer {JWT}"}


# --- toda rota exige autenticação ----------------------------------------

def test_nenhuma_rota_de_dispositivo_responde_sem_jwt():
    c = _client()
    chamadas = [
        c.get("/api/devices"),
        c.post("/api/devices", json={"nome": "x"}),
        c.patch("/api/devices/dev-1", json={"nome": "x"}),
        c.post("/api/devices/dev-1/revogar"),
    ]
    assert [r.status_code for r in chamadas] == [401, 401, 401, 401]


# --- pareamento -----------------------------------------------------------

def test_pareamento_devolve_o_token_em_claro_uma_vez():
    with _autenticado(), \
         patch.object(database.db, "cliente_do_usuario", return_value=MagicMock()), \
         patch.object(dispositivos, "criar", return_value=DEVICE):
        resp = _client().post("/api/devices", json={"nome": "ESP32 do quarto"}, headers=_SESSAO)

    assert resp.status_code == 201
    corpo = resp.get_json()
    assert corpo["token"]
    assert corpo["device"]["nome"] == "ESP32 do quarto"


def test_o_hash_nunca_volta_para_o_cliente():
    """O que o banco guarda é material sensível e não tem uso na interface."""
    with _autenticado(), \
         patch.object(database.db, "cliente_do_usuario", return_value=MagicMock()), \
         patch.object(dispositivos, "criar", return_value=DEVICE):
        resp = _client().post("/api/devices", json={}, headers=_SESSAO)

    texto = resp.get_data(as_text=True)
    token = resp.get_json()["token"]
    assert hash_token(token) not in texto
    assert "token_hash" not in texto


def test_o_token_gravado_e_o_hash_do_token_devolvido():
    """Se os dois divergirem, o dispositivo nunca conseguiria autenticar."""
    capturado = {}

    def criar_falso(_client, _usuario, nome, token_hash):
        capturado["hash"] = token_hash
        return dict(DEVICE, nome=nome)

    with _autenticado(), \
         patch.object(database.db, "cliente_do_usuario", return_value=MagicMock()), \
         patch.object(dispositivos, "criar", side_effect=criar_falso):
        resp = _client().post("/api/devices", json={}, headers=_SESSAO)

    assert capturado["hash"] == hash_token(resp.get_json()["token"])


def test_dois_pareamentos_geram_tokens_diferentes():
    tokens = set()
    for _ in range(2):
        with _autenticado(), \
             patch.object(database.db, "cliente_do_usuario", return_value=MagicMock()), \
             patch.object(dispositivos, "criar", return_value=DEVICE):
            tokens.add(_client().post("/api/devices", json={}, headers=_SESSAO).get_json()["token"])
    assert len(tokens) == 2


def test_o_dono_vem_do_token_e_nao_do_corpo():
    capturado = {}

    def criar_falso(_client, usuario_id, nome, _hash):
        capturado["usuario"] = usuario_id
        return dict(DEVICE, nome=nome)

    with _autenticado(), \
         patch.object(database.db, "cliente_do_usuario", return_value=MagicMock()), \
         patch.object(dispositivos, "criar", side_effect=criar_falso):
        _client().post("/api/devices", json={"user_id": ID_BRUNO}, headers=_SESSAO)

    assert capturado["usuario"] == ID_ANA


# --- nome -----------------------------------------------------------------

def test_nome_ausente_ou_vazio_vira_o_padrao():
    for valor in [None, "", "   "]:
        nome, erro = dispositivos.validar_nome(valor)
        assert erro is None
        assert nome == dispositivos.NOME_PADRAO


def test_nome_e_aparado():
    assert dispositivos.validar_nome("  ESP32  ")[0] == "ESP32"


def test_nome_longo_demais_e_recusado():
    _, erro = dispositivos.validar_nome("x" * (dispositivos.NOME_MAXIMO + 1))
    assert erro is not None


def test_nome_nao_textual_e_recusado():
    for valor in [42, True, ["a"], {"a": 1}]:
        assert dispositivos.validar_nome(valor)[1] is not None


def test_renomear_sem_o_campo_nome_responde_400():
    with _autenticado(), patch.object(database.db, "cliente_do_usuario", return_value=MagicMock()):
        resp = _client().patch("/api/devices/dev-1", json={}, headers=_SESSAO)
    assert resp.status_code == 400


def test_renomear_devolve_o_dispositivo_atualizado():
    novo = dict(DEVICE, nome="protótipo v2")
    with _autenticado(), \
         patch.object(database.db, "cliente_do_usuario", return_value=MagicMock()), \
         patch.object(dispositivos, "renomear", return_value=novo):
        resp = _client().patch("/api/devices/dev-1", json={"nome": "protótipo v2"}, headers=_SESSAO)
    assert resp.status_code == 200
    assert resp.get_json()["nome"] == "protótipo v2"


# --- posse ----------------------------------------------------------------

def test_dispositivo_de_outra_pessoa_responde_404_como_inexistente():
    """Distinguir 403 de 404 revelaria que o id existe — e de quem não é."""
    with _autenticado(), \
         patch.object(database.db, "cliente_do_usuario", return_value=MagicMock()), \
         patch.object(dispositivos, "renomear", return_value=None), \
         patch.object(dispositivos, "revogar", return_value=None):
        c = _client()
        renomear = c.patch("/api/devices/dev-de-outro", json={"nome": "x"}, headers=_SESSAO)
        revogar = c.post("/api/devices/dev-de-outro/revogar", headers=_SESSAO)

    assert renomear.status_code == revogar.status_code == 404


def test_revogar_marca_a_data_e_mantem_a_linha():
    """Soft delete: as leituras já gravadas referenciam este device_id."""
    capturado = {}

    def revogar_falso(_client, _usuario, device_id, agora):
        capturado["id"] = device_id
        capturado["agora"] = agora
        return dict(DEVICE, revoked_at=agora)

    with _autenticado(), \
         patch.object(database.db, "cliente_do_usuario", return_value=MagicMock()), \
         patch.object(dispositivos, "revogar", side_effect=revogar_falso):
        resp = _client().post("/api/devices/dev-1/revogar", headers=_SESSAO)

    assert resp.status_code == 200
    assert resp.get_json()["revoked_at"] == capturado["agora"]
    assert capturado["id"] == "dev-1"


# --- degradação -----------------------------------------------------------

def test_banco_indisponivel_responde_503_e_nao_500():
    with _autenticado(), patch.object(database.db, "cliente_do_usuario", return_value=None):
        c = _client()
        assert c.get("/api/devices", headers=_SESSAO).status_code == 503
        assert c.post("/api/devices", json={}, headers=_SESSAO).status_code == 503


def test_falha_na_listagem_responde_503_em_vez_de_lista_vazia():
    """Aqui, ao contrário do histórico, lista vazia mentiria: o usuário
    concluiria que não tem dispositivo pareado e criaria outro."""
    with _autenticado(), \
         patch.object(database.db, "cliente_do_usuario", return_value=MagicMock()), \
         patch.object(dispositivos, "listar", return_value=None):
        resp = _client().get("/api/devices", headers=_SESSAO)
    assert resp.status_code == 503
