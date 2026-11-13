from types import SimpleNamespace
from unittest.mock import patch

from flask import Flask
import database
from routes import init_routes


TEMPO = "2026-11-01T00:00:00+00:00"
DESDE = "2026-10-01T00:00:00+00:00"
ATE = "2026-11-12T00:00:00+00:00"


def leitura(numero, tempo=TEMPO):
    return {"created_at": tempo, "id": f"{numero:04d}"}


def filtro_cursor(tempo, id_):
    return f"created_at.lt.{tempo},and(created_at.eq.{tempo},id.lt.{id_})"


class Query:
    def __init__(self, dados, *, inserir=False, falhar=False):
        self.dados = dados
        self.inserir = inserir
        self.falhar = falhar
        self.paginas = []

    def table(self, nome):
        assert nome == "sleep_data"
        self.filtros = []
        self.cursor = None
        self.inicio = 0
        return self

    def select(self, *args):
        return self

    def eq(self, *args):
        self.filtros.append(("eq", *args))
        return self

    def gte(self, *args):
        self.filtros.append(("gte", *args))
        return self

    def lte(self, *args):
        self.filtros.append(("lte", *args))
        return self

    def order(self, *args, **kwargs):
        return self

    def or_(self, expressao):
        self.filtros.append(("or", expressao))
        tempo, resto = expressao.removeprefix("created_at.lt.").split(",and(")
        assert resto.startswith(f"created_at.eq.{tempo},id.lt.")
        self.cursor = tempo, resto.split("id.lt.", 1)[1][:-1]
        return self

    def limit(self, limite):
        self.tamanho = min(limite, 1000)
        return self

    def range(self, inicio, fim):
        self.inicio = inicio
        return self.limit(fim - inicio + 1)

    def execute(self):
        if self.paginas:
            if self.falhar:
                raise RuntimeError("falha simulada")
            if self.inserir:
                self.dados.insert(0, leitura(9999, "2026-11-02T00:00:00+00:00"))
        self.paginas.append((self.tamanho, self.filtros))
        dados = self.dados
        if self.cursor:
            dados = [linha for linha in dados if (linha["created_at"], linha["id"]) < self.cursor]
        return SimpleNamespace(data=dados[self.inicio:self.inicio + self.tamanho])


def test_historico_preserva_filtros_e_avanca_cursor_em_todas_as_paginas():
    query = Query([leitura(n) for n in range(2000, 0, -1)])
    with patch.object(database.db, "cliente_do_usuario", return_value=query):
        resultado = database.db.get_leituras_do_usuario(
            "jwt", "user", device_id="dispositivo", desde=DESDE, ate=ATE,
            limite=1500, cursor=(TEMPO, "2000"),
        )
    assert resultado == [leitura(n) for n in range(1999, 499, -1)]
    filtros = [("eq", "user_id", "user"), ("eq", "device_id", "dispositivo"),
               ("gte", "created_at", DESDE), ("lte", "created_at", ATE)]
    assert query.paginas == [
        (1000, [*filtros, ("or", filtro_cursor(TEMPO, "2000"))]),
        (500, [*filtros, ("or", filtro_cursor(TEMPO, "1000"))]),
    ]


def test_insercao_entre_paginas_nao_duplica_nem_pula_leitura():
    esperadas = [leitura(n) for n in range(1500, 0, -1)]
    query = Query(esperadas.copy(), inserir=True)
    with patch.object(database.db, "cliente_do_usuario", return_value=query):
        resultado = database.db.get_leituras_do_usuario("jwt", "user", limite=1500)
    assert len({linha["id"] for linha in resultado}) == 1500
    assert resultado == esperadas


def test_falha_na_segunda_pagina_nao_entrega_prefixo():
    query = Query([leitura(n) for n in range(1500, 0, -1)], falhar=True)
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
