"""Testes do health check (WEB-04).

Um health check tem duas obrigacoes que sao faceis de quebrar sem perceber:
responder mesmo com o banco fora (senao ele proprio vira fonte de erro) e nao
vazar detalhe de infraestrutura na resposta publica, ja que nao exige
autenticacao.
"""
from unittest.mock import patch

import os
from flask import Flask

import database
from routes import init_routes

_TEMPLATES = os.path.join(os.path.dirname(__file__), "..", "templates")
_STATIC = os.path.join(os.path.dirname(__file__), "..", "static")


def _client():
    app = Flask(__name__, template_folder=_TEMPLATES, static_folder=_STATIC)
    init_routes(app)
    app.testing = True
    return app.test_client()


def test_banco_ok_responde_200():
    with patch.object(database.db, "verificar_conexao", return_value=(True, None)):
        resp = _client().get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"
    assert resp.get_json()["banco"] == "ok"


def test_banco_fora_responde_503_sem_derrubar_o_endpoint():
    with patch.object(database.db, "verificar_conexao", return_value=(False, "consulta falhou")):
        resp = _client().get("/health")
    assert resp.status_code == 503
    assert resp.get_json()["status"] == "degradado"


def test_excecao_no_banco_nao_propaga_para_a_resposta():
    """verificar_conexao nao deve levantar; se levantasse, o /health viraria 500
    e um monitor externo nao saberia distinguir app fora de banco fora."""

    class ClienteRuim:
        def table(self, *args, **kwargs):
            raise RuntimeError("falha simulada")

    with patch.object(database.db, "get_client", return_value=ClienteRuim()), \
         patch.object(database.db, "url", "https://exemplo.supabase.co"), \
         patch.object(database.db, "key", "chave-de-teste"):
        ok, motivo = database.db.verificar_conexao()

    assert ok is False
    assert motivo == "consulta falhou"


def test_resposta_nao_vaza_infraestrutura():
    """Sem autenticacao, o corpo e publico: nada de URL, chave ou stack trace."""
    with patch.object(database.db, "verificar_conexao", return_value=(False, "credenciais ausentes")):
        resp = _client().get("/health")

    corpo = resp.get_data(as_text=True).lower()
    for proibido in ("supabase.co", "eyj", "traceback", "service_role", "password"):
        assert proibido not in corpo


def test_informa_a_versao_do_contrato_de_dados():
    """Permite conferir de fora qual contrato o backend implementa — util
    quando firmware e servidor podem estar em versoes diferentes."""
    with patch.object(database.db, "verificar_conexao", return_value=(True, None)):
        resp = _client().get("/health")
    assert resp.get_json()["contrato_de_dados"] == "1.2.0"


def test_health_nao_exige_autenticacao():
    """Nenhum header enviado: precisa responder normalmente, nao 401."""
    with patch.object(database.db, "verificar_conexao", return_value=(True, None)):
        resp = _client().get("/health")
    assert resp.status_code != 401
