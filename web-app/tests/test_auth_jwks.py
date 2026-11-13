from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4
import time

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from flask import Flask

import auth
import database

URL = "https://projeto.example"
ISS = URL + "/auth/v1"


@pytest.fixture
def cenario(monkeypatch):
    privada = ec.generate_private_key(ec.SECP256R1())
    publica = jwt.algorithms.ECAlgorithm.to_jwk(privada.public_key(), as_dict=True)
    publica.update(kid="atual", alg="ES256")
    buscar = Mock(return_value=httpx.Response(
        200, json={"keys": [publica]}, request=httpx.Request("GET", ISS)
    ))
    monkeypatch.setattr(auth.httpx, "get", buscar)
    monkeypatch.setattr(database.db, "url", URL)
    remoto = Mock(side_effect=AssertionError("validacao remota inesperada"))
    monkeypatch.setattr(database.db, "_get_client_anon", remoto)
    auth.chaves_do_projeto.cache_clear()

    app = Flask(__name__)
    @app.get("/privada")
    @auth.require_auth
    def privada_rota():
        return "", 204

    agora = int(time.time())
    claims = dict(iss=ISS, aud="authenticated", role="authenticated",
                  sub=str(uuid4()), iat=agora - 3600, exp=agora + 3600)

    def token(chave=privada, algoritmo="ES256", kid="atual", **alteracoes):
        return jwt.encode(claims | alteracoes, chave, algorithm=algoritmo, headers={"kid": kid})

    def pedir(jwt_):
        return app.test_client().get("/privada", headers={"Authorization": f"Bearer {jwt_}"}).status_code

    yield SimpleNamespace(token=token, pedir=pedir, buscar=buscar, remoto=remoto)
    auth.chaves_do_projeto.cache_clear()


def test_jwt_local_nao_consulta_auth_com_cache(cenario):
    token = cenario.token()
    assert cenario.pedir(token) == 204
    cenario.buscar.side_effect = httpx.ConnectError("indisponivel")
    assert cenario.pedir(token) == 204
    assert cenario.buscar.call_count == 1
    cenario.remoto.assert_not_called()


def test_assinatura_por_chave_errada(cenario):
    assert cenario.pedir(cenario.token(chave=ec.generate_private_key(ec.SECP256R1()))) == 401
    cenario.remoto.assert_not_called()


def test_token_expirado(cenario):
    assert cenario.pedir(cenario.token(exp=int(time.time()) - 60)) == 401


def test_emissor_de_outro_projeto(cenario):
    assert cenario.pedir(cenario.token(iss="https://outro.example/auth/v1")) == 401


@pytest.mark.parametrize("role", ["anon", "service_role"])
def test_role_nao_autenticada(cenario, role):
    assert cenario.pedir(cenario.token(role=role)) == 401


def test_audiencia_errada(cenario):
    assert cenario.pedir(cenario.token(aud="anon")) == 401


@pytest.mark.parametrize("algoritmo", ["HS256", "RS256", "none"])
def test_algoritmo_fora_da_lista_e_recusado_antes_do_jwks(cenario, algoritmo):
    from base64 import urlsafe_b64encode
    import json

    header = urlsafe_b64encode(json.dumps({"alg": algoritmo, "kid": "atual"}).encode())
    token = header.rstrip(b"=").decode() + ".e30.AA"
    assert cenario.pedir(token) == 401
    cenario.buscar.assert_not_called()
    cenario.remoto.assert_not_called()


def test_kid_desconhecido_tem_limite_de_buscas(cenario):
    for i in range(8):
        assert cenario.pedir(cenario.token(kid=f"desconhecida-{i}")) == 401
    assert cenario.buscar.call_count == 1


def test_jwks_indisponivel_e_503(cenario):
    cenario.buscar.side_effect = httpx.ConnectError("indisponivel")
    assert cenario.pedir(cenario.token()) == 503
    assert cenario.pedir(cenario.token()) == 503
    assert cenario.buscar.call_count == 1


def test_rotacao_atualiza_o_cache(cenario, monkeypatch):
    agora = 100
    monkeypatch.setattr(auth, "monotonic", lambda: agora)
    assert cenario.pedir(cenario.token()) == 204
    nova = ec.generate_private_key(ec.SECP256R1())
    publica = jwt.algorithms.ECAlgorithm.to_jwk(nova.public_key(), as_dict=True)
    publica.update(kid="nova", alg="ES256")
    cenario.buscar.return_value = httpx.Response(
        200, json={"keys": [publica]}, request=httpx.Request("GET", ISS)
    )
    agora += 31
    assert cenario.pedir(cenario.token(chave=nova, kid="nova")) == 204
    assert cenario.pedir(cenario.token()) == 401
    assert cenario.buscar.call_count == 2
