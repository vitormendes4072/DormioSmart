"""A rota de exclusão de conta (SEC-07, LGPD art. 18, VI).

Estes testes mockam o banco, como o resto de `tests/` — o que eles verificam é
a rota: a guarda de confirmação, o repasse do JWT, o código de resposta e, o
mais importante, a HONESTIDADE da resposta quando a eliminação sai incompleta.

O comportamento no banco (o que de fato é apagado, e que a exclusão da Ana não
toca no Bruno) está em `tests/rls/test_rls_eliminacao.py`, contra Postgres real.
Separação deliberada: mock nenhum prova isolamento entre usuários.
"""
from unittest.mock import patch

from flask import Flask

import database
from routes import CONFIRMACAO_EXCLUSAO, init_routes

JWT = "jwt-da-ana"
ID_ANA = "aaaaaaaa-0000-4000-8000-aaaaaaaaaaaa"

RECIBO_COMPLETO = {
    "leituras_apagadas": 812,
    "dispositivos_apagados": 2,
    "perfil_apagado": True,
    "conta_de_acesso_removida": True,
}

RECIBO_PARCIAL = dict(RECIBO_COMPLETO, conta_de_acesso_removida=False)


def _client():
    app = Flask(__name__)
    init_routes(app)
    app.testing = True
    return app.test_client()


def _como_ana():
    return {"Authorization": f"Bearer {JWT}"}


def _apagar(corpo=None, recibo=RECIBO_COMPLETO, autenticado=True):
    """Chama DELETE /api/me e devolve (resposta, mock da exclusao)."""
    usuario = ID_ANA if autenticado else None
    with patch.object(database.db, "validar_token_de_usuario", return_value=usuario), \
         patch.object(database.db, "apagar_minha_conta", return_value=recibo) as excluir:
        resposta = _client().delete(
            "/api/me",
            json=corpo if corpo is not None else {"confirmacao": CONFIRMACAO_EXCLUSAO},
            headers=_como_ana(),
        )
    return resposta, excluir


# --- a guarda de confirmação ---------------------------------------------

def test_sem_confirmacao_responde_400_e_nao_apaga():
    """A barreira contra o DELETE disparado por engano.

    Um cliente HTTP com retry, um botão clicado duas vezes, um fetch repetido
    por hot reload: qualquer um deles manda o DELETE outra vez. Nenhum digita
    a frase.
    """
    resposta, excluir = _apagar(corpo={})
    assert resposta.status_code == 400
    excluir.assert_not_called()


def test_confirmacao_errada_responde_400_e_nao_apaga():
    resposta, excluir = _apagar(corpo={"confirmacao": "sim"})
    assert resposta.status_code == 400
    excluir.assert_not_called()


def test_a_resposta_de_400_ensina_o_que_enviar():
    """Erro de 400 que não diz o que falta vira suporte manual."""
    resposta, _ = _apagar(corpo={})
    assert resposta.get_json()["envie"] == {"confirmacao": CONFIRMACAO_EXCLUSAO}


def test_corpo_ausente_responde_400_e_nao_explode():
    """DELETE sem corpo é o caso mais provável de um cliente distraído."""
    with patch.object(database.db, "validar_token_de_usuario", return_value=ID_ANA), \
         patch.object(database.db, "apagar_minha_conta") as excluir:
        resposta = _client().delete("/api/me", headers=_como_ana())
    assert resposta.status_code == 400
    excluir.assert_not_called()


# --- autenticação --------------------------------------------------------

def test_sem_sessao_responde_401_e_nao_apaga():
    resposta, excluir = _apagar(autenticado=False)
    assert resposta.status_code == 401
    excluir.assert_not_called()


def test_a_rota_repassa_o_jwt_e_nada_mais():
    """O dono não pode vir da rota.

    `apagar_minha_conta` no banco não aceita parâmetro de usuário — o dono sai
    de `auth.uid()`. Se a rota passasse um id, seria porque alguém acrescentou o
    parâmetro, e aí um JWT válido apagaria qualquer conta. Ver
    `tests/rls/test_rls_eliminacao.py::test_a_funcao_nao_tem_parametro_de_usuario`.
    """
    _, excluir = _apagar()
    excluir.assert_called_once_with(JWT)


# --- caminho feliz -------------------------------------------------------

def test_exclusao_completa_responde_200_com_o_recibo():
    resposta, _ = _apagar()
    assert resposta.status_code == 200
    corpo = resposta.get_json()
    assert corpo["leituras_apagadas"] == 812
    assert corpo["conta_de_acesso_removida"] is True
    assert "aviso" not in corpo


# --- o caso que não pode ser escondido -----------------------------------

def test_exclusao_parcial_avisa_que_o_cadastro_continua():
    """O e-mail em `auth.users` é dado pessoal.

    Se a linha de `auth.users` não pôde ser removida (privilégio — ver
    migrations/006), a eliminação está INCOMPLETA. Responder 200 limpo aqui
    seria dizer ao titular que o dado dele saiu quando parte não saiu. A rota
    devolve o aviso junto do recibo.
    """
    resposta, _ = _apagar(recibo=RECIBO_PARCIAL)
    assert resposta.status_code == 200
    corpo = resposta.get_json()
    assert corpo["conta_de_acesso_removida"] is False
    assert "aviso" in corpo
    assert "e-mail" in corpo["aviso"] or "acesso" in corpo["aviso"]


def test_exclusao_parcial_registra_aviso_no_log(caplog):
    """É pendência de conformidade, não evento de rotina — WARNING, não INFO.

    E sem id de usuário na mensagem: registrar quem pediu exclusão seria
    guardar justamente o dado que se acabou de apagar.
    """
    import logging

    with caplog.at_level(logging.WARNING):
        _apagar(recibo=RECIBO_PARCIAL)

    avisos = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert avisos, "exclusao incompleta passou sem WARNING no log"
    mensagem = " ".join(r.getMessage() for r in avisos)
    assert ID_ANA not in mensagem, "o log guardou o id de quem pediu exclusao"


def test_falha_de_infraestrutura_responde_503_e_nao_mente_sucesso():
    """Nada apagado tem de ser dito. Um 200 aqui faria o titular acreditar que
    o dado saiu quando ele continua inteiro."""
    resposta, _ = _apagar(recibo=None)
    assert resposta.status_code == 503


# --- o método importa ----------------------------------------------------

def test_get_em_api_me_nao_apaga_nada():
    """Exclusão por GET seria disparável por um prefetch de navegador."""
    with patch.object(database.db, "validar_token_de_usuario", return_value=ID_ANA), \
         patch.object(database.db, "apagar_minha_conta") as excluir:
        resposta = _client().get("/api/me", headers=_como_ana())
    assert resposta.status_code == 405
    excluir.assert_not_called()
