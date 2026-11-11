"""`gn` e `cal` na ingestão (contrato 2.9.0, CAL-03).

A garantia no banco é a restrição `sleep_data_calibracao_valida` (migração 018,
`tests/rls/test_rls_calibracao.py`). Aqui: o Flask aceita os dois junto do
vetor, recusa fora da régua com 400, e os entrega à função de gravação com o
nome da coluna.
"""
from unittest.mock import patch

import pytest
from flask import Flask

import database
from routes import CONTRATO_DE_DADOS, init_routes
from validacao import colunas_de_features, validar_leitura

_F = [0.0012, 0.0008, 0.0151, 0.0030, 0.12, 0.05]
_G = [0.0, 0.0, -1.0]
_BASE = {"ax": 0.1, "ay": 0.2, "az": -9.8, "total": 9.8, "status": "Repouso",
         "epoca_s": 30, "metodo": "pico-da-magnitude", "amostras": 960,
         "ts": "2026-11-11T03:00:00.000Z"}
_COM_F = dict(_BASE, f=_F, g=_G, fs=32.0)
_DEVICE = {"id": "dev", "user_id": "u", "revoked_at": None}
_AUTH = {"X-Device-Token": "t"}


def _client():
    app = Flask(__name__)
    init_routes(app)
    app.testing = True
    return app.test_client()


def test_o_contrato_e_o_2_9_0():
    assert CONTRATO_DE_DADOS == "2.9.0"


def test_gn_e_cal_vao_para_as_colunas():
    colunas = colunas_de_features(dict(_COM_F, gn=1.0193, cal=1))
    assert colunas["g_norma"] == 1.0193 and colunas["calibrada"] is True
    colunas = colunas_de_features(dict(_COM_F, gn=1.0, cal=0))
    assert colunas["calibrada"] is False


def test_sem_gn_e_cal_continua_valido():
    """O app antigo e o travesseiro não mandam: as colunas vão nulas."""
    leitura, erro = validar_leitura(dict(_COM_F))
    assert erro is None
    colunas = colunas_de_features(leitura)
    assert colunas["g_norma"] is None and colunas["calibrada"] is None


@pytest.mark.parametrize("extra,motivo", [
    ({"gn": 1.0}, "campo gn exige f"),
    ({"cal": 1}, "campo cal exige f"),
])
def test_gn_e_cal_sem_o_vetor_sao_recusados(extra, motivo):
    _, erro = validar_leitura(dict(_BASE, **extra))
    assert erro == motivo


@pytest.mark.parametrize("extra", [
    {"gn": -0.001}, {"gn": 8.001}, {"gn": float("nan")}, {"gn": "1.0"},
    {"cal": 2}, {"cal": -1}, {"cal": "1"}, {"cal": 0.5},
])
def test_fora_da_regua_e_400(extra):
    _, erro = validar_leitura(dict(_COM_F, **extra))
    assert erro, extra


@pytest.mark.parametrize("gn", [0.0, 1.0, 8.0])
def test_as_bordas_de_gn_passam(gn):
    _, erro = validar_leitura(dict(_COM_F, gn=gn, cal=1))
    assert erro is None


def test_api_data_grava_gn_e_cal_pelo_token():
    with patch.object(database.db, "get_device_by_token_hash", return_value=_DEVICE), \
         patch.object(database.db, "registrar_leitura", return_value="id") as gravar:
        resp = _client().post("/api/data", json=dict(_COM_F, gn=1.0002, cal=1), headers=_AUTH)
    assert resp.status_code == 201
    payload = gravar.call_args[0][1]
    assert payload["g_norma"] == 1.0002 and payload["calibrada"] is True


def test_api_data_recusa_gn_fora_da_regua():
    with patch.object(database.db, "get_device_by_token_hash", return_value=_DEVICE), \
         patch.object(database.db, "registrar_leitura") as gravar:
        resp = _client().post("/api/data", json=dict(_COM_F, gn=9.0), headers=_AUTH)
    assert resp.status_code == 400
    gravar.assert_not_called()
