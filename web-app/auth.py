"""Autenticação do usuário nas rotas de leitura (AUTH-03).

Dois caminhos entram nesta API, com credenciais propositalmente diferentes:

  Ingestão (ESP32)  -> X-Device-Token  -> credencial dedicada de ingestao (SEC-19)
  Leitura (usuário) -> Authorization   -> JWT do usuário, RLS APLICADO

Este módulo cuida do segundo. O ponto central é que o backend **repassa o JWT
ao Supabase** em vez de consultar com a service_role e filtrar em Python:
quem isola um usuário do outro passa a ser o banco, não uma linha de código
que pode ser esquecida numa consulta futura.

Contrato: docs/DATA-CONTRACT.md v1.2.0, seção 6.
"""
import logging
from functools import lru_cache, wraps
from threading import Lock
from time import monotonic
from uuid import UUID

import httpx
import jwt

from flask import g, jsonify, request

from database import INDISPONIVEL, db

logger = logging.getLogger(__name__)

CABECALHO = "Authorization"
PREFIXO = "Bearer "


def extrair_bearer(headers):
    """Lê o JWT do header Authorization. None quando ausente ou malformado."""
    valor = (headers.get(CABECALHO) or "").strip()
    if not valor.startswith(PREFIXO):
        return None
    token = valor[len(PREFIXO):].strip()
    return token or None


# Um snapshot por projeto e processo, com renovação serializada.
class ChavesDoProjeto:
    def __init__(self, emissor):
        self.emissor = emissor
        self._chaves = None
        self._vence = 0
        self._limite_de_recuo = 0
        self._ultima_busca = float("-inf")
        self._falhou = False
        self._lock = Lock()

    def chave(self, kid):
        with self._lock:
            agora = monotonic()
            atual = self._chaves is not None and agora < self._vence
            if atual and kid in self._chaves:
                return self._chaves[kid]
            if agora - self._ultima_busca < 30:
                if self._falhou and self._chaves is not None and agora < self._limite_de_recuo:
                    return self._chaves.get(kid, INDISPONIVEL)
                return INDISPONIVEL if self._falhou or not atual else None

            self._ultima_busca = agora
            try:
                resposta = httpx.get(
                    self.emissor + "/.well-known/jwks.json",
                    timeout=httpx.Timeout(2.0),
                )
                resposta.raise_for_status()
                chaves = resposta.json()["keys"]
                if not isinstance(chaves, list):
                    raise ValueError("JWKS invalido")
                novas = {}
                for chave in chaves:
                    if chave.get("alg") == "ES256" and chave.get("kty") == "EC" and chave.get("crv") == "P-256":
                        kid_da_chave = chave["kid"]
                        if not isinstance(kid_da_chave, str) or not kid_da_chave or kid_da_chave in novas:
                            raise ValueError("kid invalido no JWKS")
                        novas[kid_da_chave] = jwt.PyJWK.from_dict(chave, algorithm="ES256").key
            except (httpx.HTTPError, ValueError, TypeError, KeyError, AttributeError, jwt.PyJWTError):
                self._falhou = True
                if self._chaves is not None and monotonic() < self._limite_de_recuo:
                    return self._chaves.get(kid, INDISPONIVEL)
                return INDISPONIVEL
            self._falhou = False
            self._chaves = novas
            concluida = monotonic()
            self._vence = concluida + 300
            self._limite_de_recuo = concluida + 24 * 3600
            return novas.get(kid)


@lru_cache(maxsize=4)
def chaves_do_projeto(emissor):
    return ChavesDoProjeto(emissor)


def validar_jwt_de_usuario(token, url):
    try:
        header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError:
        return None
    algoritmo = header.get("alg")
    if algoritmo != "ES256":
        return None
    kid = header.get("kid")
    if not isinstance(kid, str) or not kid:
        return None
    if not url:
        return INDISPONIVEL

    emissor = url.rstrip("/") + "/auth/v1"
    chave = chaves_do_projeto(emissor).chave(kid)
    if chave is None or chave is INDISPONIVEL:
        return chave
    try:
        claims = jwt.decode(
            token, chave, algorithms=["ES256"],
            issuer=emissor, audience="authenticated", leeway=5,
            options={"require": ["exp", "iat", "iss", "aud", "sub", "role"], "strict_aud": True},
        )
        if claims["role"] != "authenticated":
            return None
        return str(UUID(claims["sub"]))
    except (jwt.InvalidTokenError, ValueError, TypeError, AttributeError, OverflowError):
        return None


def require_auth(rota):
    """Exige um JWT válido e deixa o usuário em `g.usuario_id` / `g.jwt`.

    Responde 401 sem revelar se o token é ausente, expirado ou inválido —
    distinguir os casos só ajudaria quem estivesse sondando tokens.
    """

    @wraps(rota)
    def envelope(*args, **kwargs):
        token = extrair_bearer(request.headers)
        if token is None:
            return jsonify({"error": "autenticacao necessaria"}), 401

        usuario_id = db.validar_token_de_usuario(token)
        if usuario_id is INDISPONIVEL:
            # O Auth falhou, não recusou (AUTH-08). 503, e não 401: 401 o
            # frontend trata como sessão morta, e desloga.
            return jsonify({"error": "servico de autenticacao indisponivel"}), 503
        if usuario_id is None:
            return jsonify({"error": "sessao invalida ou expirada"}), 401

        g.usuario_id = usuario_id
        g.jwt = token
        return rota(*args, **kwargs)

    return envelope
