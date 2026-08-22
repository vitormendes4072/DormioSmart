"""Testes da validação de entrada (SEC-03).

Autenticado não é o mesmo que confiável. Estes testes garantem que leitura
malformada, fora da faixa física ou internamente incoerente não chega ao banco:
dado sujo em estudo de actigrafia invalida resultado, não só quebra tela.
"""
from unittest.mock import patch

import os
import pytest
from flask import Flask

import database
from device_auth import TOKEN_HEADER
from routes import init_routes
from validacao import STATUS_VALIDOS, validar_leitura


_DEVICE = {"id": "dev-uuid-1", "user_id": "user-uuid-1", "revoked_at": None}
_AUTH = {TOKEN_HEADER: "token-de-teste"}

# Leitura em repouso: az ≈ gravidade, total coerente com (ax, ay, az).
VALIDA = {"ax": 0.10, "ay": 0.20, "az": 9.80, "gx": 0.0, "gy": 0.0, "gz": 0.0,
          "t": 32.0, "total": 9.80, "status": "Repouso"}


def _client():
    app = Flask(__name__)
    init_routes(app)
    app.testing = True
    return app.test_client()


# --- unitários -----------------------------------------------------------

def test_leitura_valida_passa():
    dados, erro = validar_leitura(VALIDA)
    assert erro is None
    assert dados is not None


@pytest.mark.parametrize("campo", list(VALIDA.keys()))
def test_todo_campo_e_obrigatorio(campo):
    incompleta = {k: v for k, v in VALIDA.items() if k != campo}
    _, erro = validar_leitura(incompleta)
    assert erro is not None
    assert campo in erro


@pytest.mark.parametrize("campo", ["ax", "t", "total"])
def test_campo_nulo_e_rejeitado(campo):
    _, erro = validar_leitura(dict(VALIDA, **{campo: None}))
    assert erro is not None


@pytest.mark.parametrize("valor", ["9.8", [9.8], {"v": 9.8}, True, False])
def test_tipo_invalido_e_rejeitado(valor):
    """Booleano incluído de propósito: isinstance(True, int) é True em Python."""
    _, erro = validar_leitura(dict(VALIDA, ax=valor))
    assert erro is not None


@pytest.mark.parametrize("valor", [float("nan"), float("inf"), float("-inf")])
def test_nan_e_infinito_sao_rejeitados(valor):
    _, erro = validar_leitura(dict(VALIDA, ax=valor))
    assert erro is not None
    assert "finito" in erro


@pytest.mark.parametrize("campo,valor", [
    ("ax", 500.0),    # muito além de ±8 g
    ("az", -500.0),
    ("gx", 50.0),     # muito além de ±500 °/s
    ("t", 200.0),     # fora da faixa do datasheet
    ("t", -100.0),
    ("total", -1.0),  # magnitude não é negativa
])
def test_fora_da_faixa_fisica_e_rejeitado(campo, valor):
    _, erro = validar_leitura(dict(VALIDA, **{campo: valor}))
    assert erro is not None
    assert "faixa" in erro


@pytest.mark.parametrize("status", ["Dormindo", "Movimento Detectado!", "", "REPOUSO", 42])
def test_status_fora_do_contrato_e_rejeitado(status):
    """Inclui os rótulos legados: o contrato v1.1.0 não os aceita mais na escrita."""
    _, erro = validar_leitura(dict(VALIDA, status=status))
    assert erro is not None


@pytest.mark.parametrize("status", list(STATUS_VALIDOS))
def test_status_do_contrato_e_aceito(status):
    _, erro = validar_leitura(dict(VALIDA, status=status))
    assert erro is None


def test_total_incoerente_com_os_eixos_e_rejeitado():
    """total precisa ser a magnitude de (ax, ay, az) — pega payload montado errado."""
    _, erro = validar_leitura(dict(VALIDA, total=50.0))
    assert erro is not None
    assert "incoerente" in erro


def test_arredondamento_do_firmware_nao_e_rejeitado():
    """O firmware transmite 2 casas decimais; isso não pode virar 400."""
    dados, erro = validar_leitura(
        dict(VALIDA, ax=0.12, ay=0.23, az=9.81, total=9.81)
    )
    assert erro is None


# --- integração na rota --------------------------------------------------

def test_payload_invalido_responde_400_e_nao_persiste():
    with patch.object(database.db, "get_device_by_token_hash", return_value=_DEVICE), \
         patch.object(database.db, "insert_sleep_data") as insert:
        resp = _client().post("/api/data", json=dict(VALIDA, ax=999.0), headers=_AUTH)
    assert resp.status_code == 400
    assert "faixa" in resp.get_json()["error"]
    insert.assert_not_called()


def test_validacao_roda_depois_da_autenticacao():
    """Payload inválido SEM token deve dar 401, não 400: quem não se
    identifica não recebe diagnóstico do próprio payload."""
    resp = _client().post("/api/data", json={"lixo": 1})
    assert resp.status_code == 401
