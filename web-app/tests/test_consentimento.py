"""O consentimento destacado no backend (LGPD-12).

A garantia é do banco (migração 017; `tests/rls/test_rls_consentimento.py`). Aqui se trava o que
o backend faz com ela: responder 403 com o motivo — e não 503, que o app leria como servidor fora
do ar e reenviaria para sempre —, registrar o consentimento só na versão vigente, e as três
constantes de versão (banco, backend, frontend) iguais.
"""
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

import consentimento
import database
import dispositivos
from routes import init_routes

RAIZ = Path(__file__).resolve().parents[2]
JWT = {"Authorization": "Bearer jwt-de-teste"}
LEITURA = {"ax": 0.1, "ay": 0.2, "az": 9.8, "total": 9.8, "status": "Repouso"}


def _client():
    app = Flask(__name__)
    init_routes(app)
    app.testing = True
    return app.test_client()


def _logado():
    return patch.object(database.db, "validar_token_de_usuario", return_value="user-ana")


def _cliente(rpc_data=None):
    c = MagicMock()
    c.rpc.return_value.execute.return_value.data = rpc_data
    return patch.object(database.db, "cliente_do_usuario", return_value=c), c


# --- as três versões ----------------------------------------------------------

def test_a_versao_e_a_mesma_no_banco_no_backend_e_no_frontend():
    sql = (RAIZ / "web-app" / "migrations" / "017_consentimento_destacado.sql").read_text(encoding="utf-8")
    banco = re.search(r"versao_do_consentimento\(\).*?select '([^']+)'::text", sql, re.S).group(1)
    ts = (RAIZ / "frontend" / "src" / "lib" / "consentimento.ts").read_text(encoding="utf-8")
    frontend = re.search(r'VERSAO_DO_CONSENTIMENTO\s*=\s*"([^"]+)"', ts).group(1)
    assert banco == consentimento.VERSAO == frontend


def test_versao_antiga_nao_vale():
    assert consentimento.vigente({"consentimento_saude_versao": consentimento.VERSAO})
    assert not consentimento.vigente({"consentimento_saude_versao": "2000-01-01"})
    assert not consentimento.vigente({"consentimento_saude_versao": None})
    assert not consentimento.vigente({})


@pytest.mark.sem_consentimento
def test_banco_fora_do_ar_nao_e_falta_de_consentimento():
    with patch("perfil.ler", return_value=None):
        assert consentimento.estado(MagicMock(), "u") is None


# --- registrar ----------------------------------------------------------------

def test_registrar_na_versao_vigente():
    recibo = {"consentimento_saude_em": "2026-11-10T22:00:00+00:00",
              "consentimento_saude_versao": consentimento.VERSAO}
    cliente, c = _cliente(recibo)
    with _logado(), cliente:
        resp = _client().post("/api/me/consentimento", json={"versao": consentimento.VERSAO}, headers=JWT)
    assert resp.status_code == 200 and resp.get_json() == recibo
    c.rpc.assert_called_once_with("consentir_dado_de_saude", {"p_versao": consentimento.VERSAO})


@pytest.mark.parametrize("corpo", [{"versao": "2000-01-01"}, {}, None])
def test_versao_errada_ou_ausente_e_409_e_nao_grava(corpo):
    cliente, c = _cliente()
    with _logado(), cliente:
        resp = _client().post("/api/me/consentimento", json=corpo, headers=JWT)
    assert resp.status_code == 409
    assert resp.get_json()["versao_vigente"] == consentimento.VERSAO
    c.rpc.assert_not_called()


def test_falha_ao_gravar_e_503():
    cliente, _ = _cliente(None)
    with _logado(), cliente:
        resp = _client().post("/api/me/consentimento", json={"versao": consentimento.VERSAO}, headers=JWT)
    assert resp.status_code == 503


def test_sem_sessao_e_401():
    resp = _client().post("/api/me/consentimento", json={"versao": consentimento.VERSAO})
    assert resp.status_code == 401


# --- as travas ----------------------------------------------------------------

@pytest.mark.sem_consentimento
@pytest.mark.parametrize("situacao,esperado", [(False, 403), (None, 503)])
def test_lote_pela_sessao(situacao, esperado):
    cliente, _ = _cliente()
    with _logado(), cliente, patch.object(consentimento, "estado", return_value=situacao), \
         patch.object(dispositivos, "buscar_do_dono", return_value={"id": "dev"}), \
         patch.object(database.db, "registrar_leitura_da_sessao") as gravar:
        resp = _client().post("/api/data/lote", json={"device_id": "dev", "leituras": [LEITURA]}, headers=JWT)
    assert resp.status_code == esperado
    gravar.assert_not_called()
    if esperado == 403:
        assert resp.get_json()["error"] == consentimento.PENDENTE


@pytest.mark.sem_consentimento
@pytest.mark.parametrize("rota,corpo", [("/api/devices/celular", None), ("/api/devices", {"nome": "T"})])
def test_pareamento_sem_consentimento_e_403(rota, corpo):
    cliente, _ = _cliente()
    with _logado(), cliente, patch.object(consentimento, "estado", return_value=False), \
         patch.object(dispositivos, "criar") as criar, \
         patch.object(dispositivos, "primeiro_do_tipo", return_value=None):
        resp = _client().post(rota, json=corpo, headers=JWT)
    assert resp.status_code == 403
    assert resp.get_json()["versao_vigente"] == consentimento.VERSAO
    criar.assert_not_called()


@pytest.mark.sem_consentimento
def test_inferencia_sem_consentimento_e_403():
    cliente, _ = _cliente()
    with _logado(), cliente, patch.object(consentimento, "estado", return_value=False), \
         patch.object(database.db, "get_features_do_usuario") as consulta:
        resp = _client().get("/api/inferencia", headers=JWT, query_string={
            "device": "00000000-0000-0000-0000-0000000000d1",
            "desde": "2026-11-01T22:00:00Z", "ate": "2026-11-02T08:00:00Z"})
    assert resp.status_code == 403
    consulta.assert_not_called()


def test_o_caminho_do_token_nao_pergunta_pelo_consentimento():
    """Decisão do autor (10/11), a mesma do banco: o dispositivo do travesseiro grava sem a trava."""
    with patch.object(database.db, "get_device_by_token_hash",
                      return_value={"id": "dev", "user_id": "u", "revoked_at": None}), \
         patch.object(database.db, "registrar_leitura", return_value="id"), \
         patch.object(consentimento, "estado", return_value=False) as estado:
        resp = _client().post("/api/data", json=LEITURA, headers={"X-Device-Token": "t"})
    assert resp.status_code == 201
    estado.assert_not_called()


def test_o_perfil_devolve_o_consentimento():
    cliente, _ = _cliente()
    linha = {"nome": "Ana", "idade": None, "updated_at": None,
             "consentimento_saude_em": "2026-11-10T22:00:00+00:00",
             "consentimento_saude_versao": consentimento.VERSAO}
    with _logado(), cliente, patch("perfil.ler", return_value=linha):
        resp = _client().get("/api/me/perfil", headers=JWT)
    assert resp.get_json()["consentimento_saude_versao"] == consentimento.VERSAO
