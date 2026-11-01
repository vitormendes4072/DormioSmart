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


def _cliente_explode():
    """Reproduz o defeito original: o acessor levanta em vez de devolver None.

    UnicodeEncodeError e a excecao real que acontecia — um `print` com emoji
    num console cp1252.

    O metodo se chamava `get_client`; virou `cliente_de_ingestao` na SEC-06,
    quando o caminho de ingestao passou a usar credencial de privilegio minimo.
    O nome novo e proposital: pegar o cliente privilegiado deixou de parecer
    uma operacao neutra. Ver `tests/test_privilegio_minimo.py`.
    """
    return patch.object(
        database.db,
        "cliente_de_ingestao",
        side_effect=UnicodeEncodeError("charmap", "❌", 0, 1, "nao mapeavel"),
    )


# --- a rota de leitura nao pode virar 500 (FIX-01) -----------------------

def test_history_responde_200_mesmo_com_o_cliente_levantando():
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
    with _cliente_explode():
        assert database.db.get_leituras_do_usuario("jwt", "user-1") == []


# --- os demais metodos tambem nao podem levantar -------------------------

def test_get_device_by_token_hash_nao_levanta():
    """✏️ 01/11 (AUTH-08): devolvia `None`, igual a token que não resolve; agora
    a falha é INDISPONIVEL, e a rota responde 503 em vez de 401."""
    with _cliente_explode():
        assert database.db.get_device_by_token_hash("qualquer") is database.INDISPONIVEL


def test_registrar_leitura_devolve_none():
    with _cliente_explode():
        assert database.db.registrar_leitura("hash", {"a": 1}) is None


def test_registrar_leitura_da_sessao_devolve_none():
    """O caminho do celular degrada igual — e por outro cliente.

    Ele nao usa o cliente de ingestao: a gravacao por sessao vai pelo JWT do
    usuario (SEC-06). Entao o que tem de explodir aqui e `cliente_do_usuario`.
    """
    with patch.object(
        database.db,
        "cliente_do_usuario",
        side_effect=UnicodeEncodeError("charmap", "❌", 0, 1, "nao mapeavel"),
    ):
        assert database.db.registrar_leitura_da_sessao("jwt", "dev-1", {"a": 1}) is None


def test_verificar_conexao_reporta_falha_sem_levantar():
    with patch.object(database.db, "url", "https://exemplo.supabase.co"), \
         patch.object(database.db, "key", "chave"), \
         _cliente_explode():
        ok, motivo = database.db.verificar_conexao()
    assert ok is False
    assert motivo == "consulta falhou"


# --- a rota de ingestao degrada com o codigo certo -----------------------

def test_post_data_responde_503_e_nao_400_nem_401_quando_o_banco_falha():
    """Banco fora do ar ao resolver o token -> 503: o firmware mantém a época e
    reenvia. Antes do FIX-08 virava 400 (payload ruim, a época era descartada);
    até 01/11 virava 401 "nao autorizado", que diz a coisa errada (AUTH-08)."""
    with _cliente_explode():
        resp = _client().post("/api/data", json=_LEITURA, headers=_AUTH)
    assert resp.status_code == 503


def test_health_responde_503_e_nunca_500():
    with patch.object(database.db, "url", "https://exemplo.supabase.co"), \
         patch.object(database.db, "key", "chave"), \
         _cliente_explode():
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
