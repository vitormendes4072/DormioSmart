"""Autenticação do dispositivo (SEC-02).

O ESP32 não tem sessão de usuário e não pode carregar segredo de alto
privilégio (ver Decisões técnicas no CLAUDE.md). Ele se identifica com um
**token opaco de device**, enviado no header `X-Device-Token`.

O banco guarda apenas o SHA-256 do token (`devices.token_hash`). O valor em
claro existe uma única vez — no momento do pareamento, exibido ao usuário — e
não é recuperável depois. Vazamento do banco não entrega os tokens.

Contrato: docs/DATA-CONTRACT.md v1.1.0, seção 3.
"""
import hashlib
import secrets

TOKEN_HEADER = "X-Device-Token"

# 32 bytes = 256 bits de entropia. token_urlsafe devolve texto seguro para
# header HTTP, sem precisar de escape.
_TOKEN_BYTES = 32


def gerar_token():
    """Gera um token novo de device. Só o usuário verá este valor."""
    return secrets.token_urlsafe(_TOKEN_BYTES)


def hash_token(token):
    """SHA-256 hex do token — é isto que o banco guarda e indexa.

    Sem salt de propósito: o token já tem 256 bits de entropia aleatória, então
    não há dicionário a proteger, e a busca precisa ser um lookup indexado
    direto (o POST do device acontece a cada evento de movimento).
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def extrair_token(headers):
    """Lê o token do header, devolvendo None quando ausente ou vazio."""
    valor = (headers.get(TOKEN_HEADER) or "").strip()
    return valor or None
