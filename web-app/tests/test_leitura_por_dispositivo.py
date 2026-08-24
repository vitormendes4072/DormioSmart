"""Recorte da leitura por dispositivo e por janela (DASH-05, DASH-06).

── O DEFEITO QUE ISTO CONSERTA ──────────────────────────────────────────

Até aqui `get_leituras_do_usuario` filtrava **só por dono**. Quem pareasse
dois dispositivos recebia os dois misturados na mesma série e nas mesmas
métricas, com o limite repartido por ordem de chegada — dois instrumentos
plotados como um. Ninguém esbarrou porque só existe um dispositivo, o do
autor. Os testes abaixo travam o recorte.
"""
from unittest.mock import patch

from flask import Flask

import database
from consulta import LIMITE_MAXIMO, LIMITE_PADRAO
from routes import init_routes

JWT = "jwt-da-ana"
ID_USUARIO = "11111111-1111-1111-1111-111111111111"
TRAVESSEIRO = "aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa"
CELULAR = "bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb"


def _client():
    app = Flask(__name__)
    init_routes(app)
    app.testing = True
    return app.test_client()


def _como(jwt=JWT):
    return {"Authorization": f"Bearer {jwt}"}


def _pedir(query="", jwt=JWT):
    """Faz a chamada com o Auth mockado e devolve (resposta, kwargs da consulta)."""
    with patch.object(database.db, "validar_token_de_usuario", return_value=ID_USUARIO), \
         patch.object(database.db, "get_leituras_do_usuario", return_value=[]) as consulta:
        resposta = _client().get(f"/api/sleep-history{query}", headers=_como(jwt))
    return resposta, consulta


# --- recorte por dispositivo ---------------------------------------------

def test_sem_parametro_consulta_todos_os_dispositivos():
    """Compatibilidade: quem já usa a rota não muda de comportamento."""
    resposta, consulta = _pedir()
    assert resposta.status_code == 200
    assert consulta.call_args.kwargs["device_id"] is None
    assert consulta.call_args.kwargs["limite"] == LIMITE_PADRAO


def test_device_recorta_a_consulta():
    _, consulta = _pedir(f"?device={TRAVESSEIRO}")
    assert consulta.call_args.kwargs["device_id"] == TRAVESSEIRO


def test_dispositivos_diferentes_produzem_consultas_diferentes():
    """É a essência do DASH-05: travesseiro e celular não se misturam."""
    vistos = []

    def registrar(jwt, usuario_id, **kwargs):
        vistos.append(kwargs["device_id"])
        return []

    with patch.object(database.db, "validar_token_de_usuario", return_value=ID_USUARIO), \
         patch.object(database.db, "get_leituras_do_usuario", side_effect=registrar):
        c = _client()
        c.get(f"/api/sleep-history?device={TRAVESSEIRO}", headers=_como())
        c.get(f"/api/sleep-history?device={CELULAR}", headers=_como())

    assert vistos == [TRAVESSEIRO, CELULAR]


def test_device_malformado_responde_400_e_nao_consulta():
    """Lista vazia faria o usuário concluir que o dispositivo não mandou nada."""
    with patch.object(database.db, "validar_token_de_usuario", return_value=ID_USUARIO), \
         patch.object(database.db, "get_leituras_do_usuario") as consulta:
        resposta = _client().get("/api/sleep-history?device=xxx", headers=_como())
    assert resposta.status_code == 400
    consulta.assert_not_called()


def test_device_nao_substitui_o_dono():
    """O `user_id` continua saindo do JWT, nunca da query string."""
    _, consulta = _pedir(f"?device={CELULAR}&user_id=99999999-9999-4999-8999-999999999999")
    assert consulta.call_args[0][1] == ID_USUARIO


def test_recorte_por_dispositivo_exige_autenticacao():
    with patch.object(database.db, "get_leituras_do_usuario") as consulta:
        resposta = _client().get(f"/api/sleep-history?device={TRAVESSEIRO}")
    assert resposta.status_code == 401
    consulta.assert_not_called()


# --- janela e limite ------------------------------------------------------

def test_janela_chega_na_consulta():
    _, consulta = _pedir("?desde=2026-08-22T00:00:00Z&ate=2026-08-23T00:00:00Z")
    assert consulta.call_args.kwargs["desde"] is not None
    assert consulta.call_args.kwargs["ate"] is not None


def test_limite_maior_atende_uma_noite_inteira():
    # Época de 60 s por uma noite dá ~480 linhas; o limite fixo de 20 não servia.
    _, consulta = _pedir("?limite=480")
    assert consulta.call_args.kwargs["limite"] == 480


def test_limite_absurdo_e_grampeado_e_nao_recusado():
    _, consulta = _pedir("?limite=999999")
    assert consulta.call_args.kwargs["limite"] == LIMITE_MAXIMO


def test_janela_invertida_responde_400():
    with patch.object(database.db, "validar_token_de_usuario", return_value=ID_USUARIO), \
         patch.object(database.db, "get_leituras_do_usuario") as consulta:
        resposta = _client().get(
            "/api/sleep-history?desde=2026-08-23T00:00:00Z&ate=2026-08-22T00:00:00Z",
            headers=_como(),
        )
    assert resposta.status_code == 400
    consulta.assert_not_called()


# --- o SELECT precisa trazer o device_id ---------------------------------

def test_a_consulta_seleciona_o_device_id():
    """Sem ele o cliente não sabe de qual instrumento veio cada ponto."""
    import inspect

    fonte = inspect.getsource(database.Database.get_leituras_do_usuario)
    assert "device_id" in fonte.split(".select(")[1].split(")")[0]
