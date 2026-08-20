"""Autenticação do usuário nas rotas de leitura (AUTH-03).

Dois caminhos entram nesta API, com credenciais propositalmente diferentes:

  Ingestão (ESP32)  -> X-Device-Token  -> service_role, RLS ignorado (SEC-02)
  Leitura (usuário) -> Authorization   -> JWT do usuário, RLS APLICADO

Este módulo cuida do segundo. O ponto central é que o backend **repassa o JWT
ao Supabase** em vez de consultar com a service_role e filtrar em Python:
quem isola um usuário do outro passa a ser o banco, não uma linha de código
que pode ser esquecida numa consulta futura.

Contrato: docs/DATA-CONTRACT.md v1.2.0, seção 6.
"""
import logging
from functools import wraps

from flask import g, jsonify, request

from database import db

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
        if usuario_id is None:
            return jsonify({"error": "sessao invalida ou expirada"}), 401

        g.usuario_id = usuario_id
        g.jwt = token
        return rota(*args, **kwargs)

    return envelope
