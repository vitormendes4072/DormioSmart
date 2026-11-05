"""API-05: a ordem temporal deve considerar o fuso, nas duas rotas."""
from unittest.mock import patch

import pytest
from flask import Flask

import database
from consulta import ler_parametros
from routes import init_routes


VALIDAS = [
    ("2026-11-04T10:00:00+03:00", "2026-11-04T08:00:00+00:00"),
    ("2026-11-04T10:00:00+03:00", "2026-11-04T07:00:00Z"),
    ("2026-11-04T01:00:00+03:00", "2026-11-03T23:00:00Z"),
    ("2026-11-04T08:00:00Z", "2026-11-04T08:00:00.1Z"),
    ("2026-11-04T08:00:00.100Z", "2026-11-04T08:00:00.1Z"),
]
INVALIDAS = [
    ("2026-11-04T08:00:00+00:00", "2026-11-04T10:00:00+03:00"),
    ("2026-11-03T23:00:00Z", "2026-11-04T01:00:00+03:00"),
    ("2026-11-04T08:00:00.1Z", "2026-11-04T08:00:00Z"),
    ("2026-11-04T07:00:00", "2026-11-04T08:00:00Z"),
    ("2026-11-04T07:00:00Z", "2026-11-04T08:00:00"),
]


@pytest.mark.parametrize("desde,ate", VALIDAS)
def test_validacao_aceita_ordem_cronologica(desde, ate):
    parametros, erro = ler_parametros({"desde": desde, "ate": ate})
    assert erro is None
    assert parametros is not None


@pytest.mark.parametrize("desde,ate", INVALIDAS)
def test_validacao_recusa_inversao_ou_ambiguidade(desde, ate):
    parametros, erro = ler_parametros({"desde": desde, "ate": ate})
    assert parametros is None
    assert erro is not None


@pytest.mark.parametrize("rota,metodo", [
    ("/api/sleep-history", "get_leituras_do_usuario"),
    ("/api/features", "get_features_do_usuario"),
])
@pytest.mark.parametrize("desde,ate,valida", [
    *( (d, a, True) for d, a in VALIDAS ),
    *( (d, a, False) for d, a in INVALIDAS ),
])
def test_rotas_validam_antes_de_consultar(rota, metodo, desde, ate, valida):
    app = Flask(__name__)
    init_routes(app)
    app.testing = True
    with patch.object(database.db, "validar_token_de_usuario", return_value="usuario"), \
         patch.object(database.db, metodo, return_value=[]) as consulta:
        resp = app.test_client().get(
            rota, query_string={"device": "11111111-1111-1111-1111-111111111111",
                                "desde": desde, "ate": ate},
            headers={"Authorization": "Bearer jwt-de-teste"})
    assert resp.status_code == (200 if valida else 400)
    if valida:
        consulta.assert_called_once()
    else:
        consulta.assert_not_called()


def test_historico_preserva_duas_datas_sem_fuso():
    parametros, erro = ler_parametros({"desde": "2026-11-03", "ate": "2026-11-04"})
    assert erro is None
    assert parametros["desde"] == "2026-11-03T00:00:00"
    assert parametros["ate"] == "2026-11-04T00:00:00"


@pytest.mark.parametrize("nome", ["desde", "ate"])
@pytest.mark.parametrize("valor", ["2026-11-04", "2026-11-04T08:00:00-03:00"])
def test_limite_isolado_e_preservado(nome, valor):
    parametros, erro = ler_parametros({nome: valor})
    assert erro is None
    assert parametros[nome] is not None


def test_preserva_offset_no_parametro_devolvido():
    parametros, erro = ler_parametros({"desde": VALIDAS[0][0], "ate": VALIDAS[0][1]})
    assert erro is None
    assert parametros["desde"] == VALIDAS[0][0]
    assert parametros["ate"] == VALIDAS[0][1]
