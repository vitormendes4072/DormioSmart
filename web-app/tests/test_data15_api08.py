from types import SimpleNamespace
from unittest.mock import patch

from flask import Flask
import database
from routes import init_routes


class Query:
    def __init__(self, dados, falha_em=None):
        self.dados, self.falha_em = dados, falha_em
        self.intervalos = []
        self.inicio = self.fim = 0
    def table(self, *args): return self
    def select(self, *args): return self
    def eq(self, *args): return self
    def gte(self, *args): return self
    def lte(self, *args): return self
    def order(self, *args, **kwargs): return self
    def or_(self, *args): return self
    def limit(self, limite):
        self.inicio, self.fim = 0, min(limite, 1000) - 1
        return self
    def range(self, inicio, fim):
        self.inicio, self.fim = inicio, fim
        self.intervalos.append((inicio, fim))
        return self
    def execute(self):
        if self.inicio == self.falha_em:
            raise RuntimeError("falha simulada")
        return SimpleNamespace(data=self.dados[self.inicio:self.fim + 1])


def test_historico_busca_mais_que_o_teto_e_respeita_limite():
    query = Query(list(range(2200)))
    with patch.object(database.db, "cliente_do_usuario", return_value=query):
        resultado = database.db.get_leituras_do_usuario("jwt", "user", limite=1500)
    assert resultado == list(range(1500))
    assert query.intervalos == [(0, 999), (1000, 1499)]


def test_falha_na_segunda_pagina_nao_entrega_prefixo():
    query = Query(list(range(1500)), falha_em=1000)
    with patch.object(database.db, "cliente_do_usuario", return_value=query):
        assert database.db.get_leituras_do_usuario("jwt", "user", limite=1500) is None


def test_rota_distingue_banco_indisponivel_de_vazio():
    app = Flask(__name__)
    init_routes(app)
    with patch.object(database.db, "validar_token_de_usuario", return_value="user"), \
         patch.object(database.db, "get_leituras_do_usuario", return_value=None):
        resposta = app.test_client().get("/api/sleep-history", headers={"Authorization": "Bearer jwt"})
    assert resposta.status_code == 503


def test_cursor_incompleto_e_invalidado():
    app = Flask(__name__)
    init_routes(app)
    with patch.object(database.db, "validar_token_de_usuario", return_value="user"):
        resposta = app.test_client().get("/api/sleep-history?cursor_id=qualquer", headers={"Authorization": "Bearer jwt"})
    assert resposta.status_code == 400
