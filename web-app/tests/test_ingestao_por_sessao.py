"""Segundo caminho de autenticacao na ingestao (APP-08, contrato v2.2.0).

O `X-Device-Token` existe porque o ESP32 NAO TEM LOGIN. O celular tem sessao,
e exigir que ele use token colocaria uma credencial de escrita dentro do
navegador, onde nao ha equivalente ao Keystore.

Estes testes cobrem sobretudo o risco que o caminho novo cria: uma porta de
escrita a mais. A regra que nao pode cair e que o `user_id` sai do JWT, nunca
do corpo.
"""
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

import database
import dispositivos
from ingestao import (
    CAMINHO_SESSAO,
    CAMINHO_TOKEN,
    extrair_device_id,
    identificar_caminho,
)
from routes import init_routes

JWT_ANA = "jwt-da-ana"
ID_ANA = "11111111-1111-1111-1111-111111111111"
ID_BRUNO = "22222222-2222-2222-2222-222222222222"
DEV_ANA = "aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa"
DEV_BRUNO = "bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb"

LEITURA = {"ax": 0.10, "ay": 0.20, "az": 9.80, "total": 9.80, "status": "Repouso"}


def _client():
    app = Flask(__name__)
    init_routes(app)
    app.testing = True
    return app.test_client()


def _sessao(jwt=JWT_ANA):
    return {"Authorization": f"Bearer {jwt}"}


# --- identificar_caminho (funcao pura) -----------------------------------

class TestIdentificarCaminho:
    def test_token_e_reconhecido(self):
        assert identificar_caminho({"X-Device-Token": "abc"}) == CAMINHO_TOKEN

    def test_bearer_e_reconhecido(self):
        assert identificar_caminho({"Authorization": "Bearer abc"}) == CAMINHO_SESSAO

    def test_bearer_e_insensivel_a_caixa(self):
        assert identificar_caminho({"Authorization": "bearer abc"}) == CAMINHO_SESSAO

    def test_sem_credencial_nenhuma(self):
        assert identificar_caminho({}) is None
        assert identificar_caminho(None) is None

    def test_header_vazio_nao_conta_como_credencial(self):
        assert identificar_caminho({"X-Device-Token": "   "}) is None

    def test_authorization_sem_bearer_nao_conta(self):
        assert identificar_caminho({"Authorization": "Basic abc"}) is None

    def test_token_tem_precedencia_sobre_sessao(self):
        """Um ESP32 nunca manda Authorization; se vierem os dois, e engano de
        cliente, e o mais especifico vence."""
        cabecalhos = {"X-Device-Token": "abc", "Authorization": "Bearer xyz"}
        assert identificar_caminho(cabecalhos) == CAMINHO_TOKEN


class TestExtrairDeviceId:
    def test_aceita_e_limpa(self):
        assert extrair_device_id({"device_id": f"  {DEV_ANA} "}) == (DEV_ANA, None)

    @pytest.mark.parametrize("corpo", [{}, {"device_id": None}, {"device_id": "  "}])
    def test_ausente_e_erro(self, corpo):
        _, erro = extrair_device_id(corpo)
        assert erro is not None and "device_id" in erro

    def test_tipo_errado_e_erro(self):
        _, erro = extrair_device_id({"device_id": 42})
        assert erro is not None

    def test_corpo_que_nao_e_objeto(self):
        _, erro = extrair_device_id("nao sou objeto")
        assert erro is not None


# --- a rota ---------------------------------------------------------------

def _com_sessao(usuario_id=ID_ANA, device=None):
    """Mocka o Auth e a busca do dispositivo."""
    return (
        patch.object(database.db, "validar_token_de_usuario", return_value=usuario_id),
        patch.object(database.db, "cliente_do_usuario", return_value=MagicMock()),
        patch.object(dispositivos, "buscar_do_dono", return_value=device),
    )


def test_sem_credencial_nenhuma_responde_401_e_nao_grava():
    with patch.object(database.db, "insert_sleep_data") as gravar:
        resp = _client().post("/api/data", json=LEITURA)
    assert resp.status_code == 401
    gravar.assert_not_called()


def test_sessao_valida_com_dispositivo_proprio_grava():
    a, b, c = _com_sessao(device={"id": DEV_ANA, "nome": "Meu celular"})
    resultado = MagicMock()
    resultado.data = [{"id": 1}]
    with a, b, c, \
         patch.object(database.db, "insert_sleep_data", return_value=resultado) as gravar, \
         patch.object(database.db, "touch_device"):
        resp = _client().post(
            "/api/data", json=dict(LEITURA, device_id=DEV_ANA), headers=_sessao()
        )
    assert resp.status_code == 201
    # O dono carimbado na linha vem do JWT.
    assert gravar.call_args[0][0]["user_id"] == ID_ANA


def test_nao_da_para_gravar_no_dispositivo_de_outro():
    """O risco central do caminho novo. `buscar_do_dono` filtra por dono."""
    a, b, c = _com_sessao(device=None)  # o dispositivo de Bruno nao e da Ana
    with a, b, c, patch.object(database.db, "insert_sleep_data") as gravar:
        resp = _client().post(
            "/api/data", json=dict(LEITURA, device_id=DEV_BRUNO), headers=_sessao()
        )
    assert resp.status_code == 404
    gravar.assert_not_called()


def test_o_user_id_do_corpo_e_ignorado():
    a, b, c = _com_sessao(device={"id": DEV_ANA})
    resultado = MagicMock()
    resultado.data = [{"id": 1}]
    with a, b, c, \
         patch.object(database.db, "insert_sleep_data", return_value=resultado) as gravar, \
         patch.object(database.db, "touch_device"):
        _client().post(
            "/api/data",
            json=dict(LEITURA, device_id=DEV_ANA, user_id=ID_BRUNO),
            headers=_sessao(),
        )
    assert gravar.call_args[0][0]["user_id"] == ID_ANA


def test_sessao_invalida_responde_401_e_nao_grava():
    with patch.object(database.db, "validar_token_de_usuario", return_value=None), \
         patch.object(database.db, "insert_sleep_data") as gravar:
        resp = _client().post(
            "/api/data", json=dict(LEITURA, device_id=DEV_ANA), headers=_sessao("expirado")
        )
    assert resp.status_code == 401
    gravar.assert_not_called()


def test_sessao_sem_device_id_responde_400():
    with patch.object(database.db, "validar_token_de_usuario", return_value=ID_ANA), \
         patch.object(database.db, "insert_sleep_data") as gravar:
        resp = _client().post("/api/data", json=LEITURA, headers=_sessao())
    assert resp.status_code == 400
    gravar.assert_not_called()


def test_a_leitura_continua_sendo_validada_no_caminho_novo():
    """Sessao valida nao dispensa validacao de conteudo (SEC-03)."""
    a, b, c = _com_sessao(device={"id": DEV_ANA})
    with a, b, c, patch.object(database.db, "insert_sleep_data") as gravar:
        resp = _client().post(
            "/api/data",
            # Fora da faixa fisica (SEC-03). Deliberadamente independente do
            # SEC-06, que ainda vive numa branch separada.
            json=dict(LEITURA, ax=1e9, device_id=DEV_ANA),
            headers=_sessao(),
        )
    assert resp.status_code == 400
    gravar.assert_not_called()


def test_o_caminho_por_token_continua_funcionando():
    """Regressao: o ESP32 nao pode ter sido afetado."""
    from device_auth import TOKEN_HEADER
    resultado = MagicMock()
    resultado.data = [{"id": 1}]
    device = {"id": DEV_ANA, "user_id": ID_ANA}
    with patch.object(database.db, "get_device_by_token_hash", return_value=device), \
         patch.object(database.db, "insert_sleep_data", return_value=resultado), \
         patch.object(database.db, "touch_device"):
        resp = _client().post("/api/data", json=LEITURA, headers={TOKEN_HEADER: "tok"})
    assert resp.status_code == 201
