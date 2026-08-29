"""Testes de resiliencia da camada de banco (FIX-08).

Contexto: o `print` com emoji em `get_client()` levantava UnicodeEncodeError em
console cp1252 (padrao no Windows pt-BR). Como `get_client()` era chamado FORA
do `try` dos metodos, a excecao escapava e `/api/sleep-history` respondia 500 —
justamente o que o FIX-01 existe para impedir.

Os testes existentes nao pegaram porque todos mockam `get_client`, entao o
`print` nunca executava. Estes cobrem a lacuna: a falha e injetada NO
`get_client`, e o contrato verificado e "nenhum metodo levanta, nenhuma rota
responde 500".
"""
from unittest.mock import patch

import os
from flask import Flask

import database
from device_auth import TOKEN_HEADER
from routes import init_routes


_LEITURA = {"ax": 0.10, "ay": 0.20, "az": 9.80, "gx": 0.0, "gy": 0.0, "gz": 0.0,
            "t": 32.0, "total": 9.80, "status": "Repouso"}
_AUTH = {TOKEN_HEADER: "token-de-teste"}


def _client():
    app = Flask(__name__)
    init_routes(app)
    app.testing = True
    return app.test_client()


def _get_client_explode():
    """Reproduz o defeito original: get_client levanta em vez de devolver None.

    UnicodeEncodeError e a excecao real que acontecia — um `print` com emoji
    num console cp1252.
    """
    return patch.object(
        database.db,
        "get_client",
        side_effect=UnicodeEncodeError("charmap", "❌", 0, 1, "nao mapeavel"),
    )


# --- a rota de leitura nao pode virar 500 (FIX-01) -----------------------

def test_history_responde_200_mesmo_com_get_client_levantando():
    # AUTH-03: a rota exige JWT, entao autenticamos e explodimos so a camada
    # de banco — o que se verifica aqui e que falha de banco nao vira 500.
    with patch.object(database.db, "validar_token_de_usuario", return_value="user-1"),          patch.object(database.db, "cliente_do_usuario", side_effect=UnicodeEncodeError(
             "charmap", "x", 0, 1, "nao mapeavel")):
        resp = _client().get("/api/sleep-history", headers={"Authorization": "Bearer jwt"})
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_get_leituras_do_usuario_degrada_para_lista_vazia():
    # Migrado do `get_latest_data`, removido no SEC-07 por ser codigo morto
    # que lia sem RLS. A propriedade continua importando — so que agora no
    # metodo que as rotas de fato usam.
    with _get_client_explode():
        assert database.db.get_leituras_do_usuario("jwt", "user-1") == []


# --- os demais metodos tambem nao podem levantar -------------------------

def test_get_device_by_token_hash_devolve_none():
    with _get_client_explode():
        assert database.db.get_device_by_token_hash("qualquer") is None


def test_insert_sleep_data_devolve_none():
    with _get_client_explode():
        assert database.db.insert_sleep_data({"a": 1}) is None


def test_touch_device_nao_levanta():
    """Best-effort: falhar aqui nao pode derrubar leitura ja persistida."""
    with _get_client_explode():
        database.db.touch_device("dev-1")  # nao deve levantar


def test_verificar_conexao_reporta_falha_sem_levantar():
    with patch.object(database.db, "url", "https://exemplo.supabase.co"), \
         patch.object(database.db, "key", "chave"), \
         _get_client_explode():
        ok, motivo = database.db.verificar_conexao()
    assert ok is False
    assert motivo == "consulta falhou"


# --- a rota de ingestao degrada com o codigo certo -----------------------

def test_post_data_responde_401_e_nao_400_quando_o_banco_falha():
    """Token nao resolve por falha de banco -> 401 (nao autorizado), que e o
    que o firmware sabe tratar. Antes virava 400, sugerindo payload ruim."""
    with _get_client_explode():
        resp = _client().post("/api/data", json=_LEITURA, headers=_AUTH)
    assert resp.status_code == 401


def test_health_responde_503_e_nunca_500():
    with patch.object(database.db, "url", "https://exemplo.supabase.co"), \
         patch.object(database.db, "key", "chave"), \
         _get_client_explode():
        resp = _client().get("/health")
    assert resp.status_code == 503
    assert resp.get_json()["status"] == "degradado"


# --- a causa raiz: nenhuma mensagem de log com caractere fora de ASCII ----

def test_mensagens_de_log_sao_ascii():
    """Emoji em log de servidor quebra em console cp1252. Este teste trava a
    regressao lendo o proprio fonte — mensagem nova com emoji falha aqui."""
    caminho = os.path.join(os.path.dirname(__file__), "..", "database.py")
    with open(caminho, encoding="utf-8") as arquivo:
        linhas = arquivo.readlines()

    chamadas_de_log = [
        (numero, linha)
        for numero, linha in enumerate(linhas, start=1)
        if "logger." in linha
    ]
    assert chamadas_de_log, "esperava encontrar chamadas de logging"

    for numero, linha in chamadas_de_log:
        assert linha.isascii(), f"database.py linha {numero}: log com caractere nao-ASCII"


def test_nenhum_print_sobrou_no_database():
    """`print` em servidor nao respeita nivel de log e foi a origem do FIX-08."""
    caminho = os.path.join(os.path.dirname(__file__), "..", "database.py")
    with open(caminho, encoding="utf-8") as arquivo:
        conteudo = arquivo.read()
    assert "print(" not in conteudo
