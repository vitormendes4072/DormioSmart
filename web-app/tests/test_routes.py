"""Testes da rota /api/sleep-history e da leitura do banco (FIX-01).

Objetivo: garantir que o endpoint nunca devolva 500 e que a camada de
banco degrade para uma lista vazia em qualquer falha. O Supabase é
sempre mockado — nenhum teste depende de credencial ou rede.
"""
from unittest.mock import patch

from flask import Flask

import database
from routes import init_routes


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
