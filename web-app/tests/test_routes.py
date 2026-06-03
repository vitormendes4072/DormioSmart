"""Testes das rotas da web-app: leitura (FIX-01), escrita (FIX-02) e páginas (DASH-01).

Objetivo: garantir que /api/sleep-history nunca devolva 500 (degrada para
lista vazia), que /api/data não minta sucesso — respondendo 503 quando nada
persiste — e que as páginas / e /dashboard retornem 200. O Supabase é sempre
mockado — nenhum teste depende de credencial ou rede.
"""
from unittest.mock import patch

import os
from flask import Flask

import database
from routes import init_routes

# Caminho para a pasta de templates (web-app/templates/), relativo a este arquivo
_TEMPLATES = os.path.join(os.path.dirname(__file__), "..", "templates")
_STATIC    = os.path.join(os.path.dirname(__file__), "..", "static")


def _client():
    app = Flask(__name__, template_folder=_TEMPLATES, static_folder=_STATIC)
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
    with patch.object(database.db, "get_latest_data", return_value=amostra):
        resp = _client().get("/api/sleep-history")
    assert resp.status_code == 200
    assert resp.get_json() == amostra


def test_history_vazio_retorna_200():
    with patch.object(database.db, "get_latest_data", return_value=[]):
        resp = _client().get("/api/sleep-history")
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

    with patch.object(database.db, "insert_sleep_data", return_value=RespOK()):
        resp = _client().post("/api/data", json={"ax": 0.1, "total": 9.8, "status": "Dormindo"})
    assert resp.status_code == 201
    assert resp.get_json()["status"] == "success"


def test_receive_data_nao_persistido_retorna_503():
    # Nada persistiu (cliente indisponível → None) → 503, sem mentir sucesso (FIX-02).
    with patch.object(database.db, "insert_sleep_data", return_value=None):
        resp = _client().post("/api/data", json={"ax": 0.1, "total": 9.8, "status": "Dormindo"})
    assert resp.status_code == 503


def test_receive_data_json_invalido_retorna_400():
    # Corpo não-JSON → erro de parse tratado → 400 (comportamento preservado).
    resp = _client().post("/api/data", data="nao-e-json", content_type="application/json")
    assert resp.status_code == 400


def test_index_retorna_200():
    # Landing Page (/) deve sempre responder 200 (DASH-01).
    resp = _client().get("/")
    assert resp.status_code == 200
    assert b"SmartDormio" in resp.data


def test_dashboard_retorna_200():
    # Dashboard (/dashboard) deve sempre responder 200 (DASH-01).
    resp = _client().get("/dashboard")
    assert resp.status_code == 200
    assert b"SmartDormio" in resp.data
