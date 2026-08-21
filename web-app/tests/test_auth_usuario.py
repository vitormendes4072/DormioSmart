"""Testes da autenticação de usuário na leitura (AUTH-03).

Regra: `GET /api/sleep-history` só responde com um JWT válido, e devolve
apenas as leituras de quem pediu. O isolamento real é do RLS no banco — aqui
verificamos o que é verificável sem banco: que a rota exige token, que o JWT
de quem pediu é o repassado ao Supabase, e que o id do usuário nunca vem do
que o cliente mandou.
"""
from unittest.mock import patch

import os
from flask import Flask

import database
from auth import extrair_bearer
from routes import init_routes

_TEMPLATES = os.path.join(os.path.dirname(__file__), "..", "templates")
_STATIC = os.path.join(os.path.dirname(__file__), "..", "static")

JWT_ANA = "jwt-da-ana"
JWT_BRUNO = "jwt-do-bruno"
ID_ANA = "11111111-1111-1111-1111-111111111111"
ID_BRUNO = "22222222-2222-2222-2222-222222222222"

LEITURA_DA_ANA = {
    "created_at": "2026-08-20T03:00:00Z",
    "movimento_total": 9.83,
    "temp": 32.1,
    "status": "Repouso",
}


def _client():
    app = Flask(__name__, template_folder=_TEMPLATES, static_folder=_STATIC)
    init_routes(app)
    app.testing = True
    return app.test_client()


def _como(jwt):
    return {"Authorization": f"Bearer {jwt}"}


def _resolve(jwt):
    """Simula o Auth do Supabase: JWT conhecido -> id; resto -> None."""
    return {JWT_ANA: ID_ANA, JWT_BRUNO: ID_BRUNO}.get(jwt)


# --- extração do header ---------------------------------------------------

def test_extrai_o_token_do_bearer():
    assert extrair_bearer({"Authorization": "Bearer abc123"}) == "abc123"


def test_header_ausente_ou_malformado_nao_vira_token():
    for valor in [None, "", "abc123", "Basic abc123", "Bearer", "Bearer    "]:
        cabecalhos = {} if valor is None else {"Authorization": valor}
        assert extrair_bearer(cabecalhos) is None


# --- a rota exige autenticação -------------------------------------------

def test_sem_token_responde_401_e_nao_consulta():
    with patch.object(database.db, "get_leituras_do_usuario") as consulta:
        resp = _client().get("/api/sleep-history")
    assert resp.status_code == 401
    consulta.assert_not_called()


def test_token_invalido_responde_401_e_nao_consulta():
    with patch.object(database.db, "validar_token_de_usuario", return_value=None), \
         patch.object(database.db, "get_leituras_do_usuario") as consulta:
        resp = _client().get("/api/sleep-history", headers=_como("qualquer-coisa"))
    assert resp.status_code == 401
    consulta.assert_not_called()


def test_401_nao_revela_se_o_token_e_ausente_ou_expirado():
    """Distinguir os casos ajudaria quem estivesse sondando tokens."""
    c = _client()
    sem = c.get("/api/sleep-history")
    with patch.object(database.db, "validar_token_de_usuario", return_value=None):
        invalido = c.get("/api/sleep-history", headers=_como("expirado"))

    assert sem.status_code == invalido.status_code == 401
    for corpo in (sem.get_json(), invalido.get_json()):
        assert "expirad" not in corpo["error"] or "invalid" in corpo["error"]


# --- o dado que volta é do dono ------------------------------------------

def test_token_valido_responde_200_com_as_leituras():
    with patch.object(database.db, "validar_token_de_usuario", side_effect=_resolve), \
         patch.object(database.db, "get_leituras_do_usuario", return_value=[LEITURA_DA_ANA]):
        resp = _client().get("/api/sleep-history", headers=_como(JWT_ANA))
    assert resp.status_code == 200
    assert resp.get_json() == [LEITURA_DA_ANA]


def test_a_consulta_recebe_o_jwt_e_o_id_de_quem_pediu():
    """É o que faz o RLS enxergar `auth.uid()` como o usuário certo."""
    with patch.object(database.db, "validar_token_de_usuario", side_effect=_resolve), \
         patch.object(database.db, "get_leituras_do_usuario", return_value=[]) as consulta:
        _client().get("/api/sleep-history", headers=_como(JWT_BRUNO))

    jwt_usado, id_usado = consulta.call_args[0][:2]
    assert jwt_usado == JWT_BRUNO
    assert id_usado == ID_BRUNO


def test_usuarios_diferentes_produzem_consultas_diferentes():
    chamadas = []

    def registrar(jwt, usuario_id, *args, **kwargs):
        chamadas.append((jwt, usuario_id))
        return []

    with patch.object(database.db, "validar_token_de_usuario", side_effect=_resolve), \
         patch.object(database.db, "get_leituras_do_usuario", side_effect=registrar):
        c = _client()
        c.get("/api/sleep-history", headers=_como(JWT_ANA))
        c.get("/api/sleep-history", headers=_como(JWT_BRUNO))

    assert chamadas == [(JWT_ANA, ID_ANA), (JWT_BRUNO, ID_BRUNO)]


def test_cliente_nao_consegue_pedir_o_dado_de_outro():
    """O id vem SEMPRE do token validado, nunca de parâmetro ou corpo."""
    with patch.object(database.db, "validar_token_de_usuario", side_effect=_resolve), \
         patch.object(database.db, "get_leituras_do_usuario", return_value=[]) as consulta:
        _client().get(
            f"/api/sleep-history?user_id={ID_BRUNO}",
            headers=_como(JWT_ANA),
        )

    _, id_usado = consulta.call_args[0][:2]
    assert id_usado == ID_ANA


# --- degradação -----------------------------------------------------------

def test_falha_de_banco_devolve_lista_vazia_e_nao_500():
    """FIX-01/FIX-08 continuam valendo no caminho autenticado."""
    with patch.object(database.db, "validar_token_de_usuario", side_effect=_resolve), \
         patch.object(database.db, "cliente_do_usuario", return_value=None):
        resp = _client().get("/api/sleep-history", headers=_como(JWT_ANA))
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_validacao_de_token_nunca_levanta():
    """Auth fora do ar deve virar 401, não 500."""
    class ClienteRuim:
        class auth:
            @staticmethod
            def get_user(_):
                raise RuntimeError("auth indisponivel")

    with patch.object(database.db, "_get_client_anon", return_value=ClienteRuim()):
        assert database.db.validar_token_de_usuario("qualquer") is None
