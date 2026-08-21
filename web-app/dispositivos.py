"""Gerenciamento de dispositivos do usuário (AUTH-05).

Um usuário tem muitos dispositivos; cada dispositivo tem um dono. Todas as
operações usam o cliente montado com o JWT de quem pediu, então o **RLS decide
a posse** — não há verificação de dono escrita em Python que possa ser
esquecida numa rota futura.

Sobre o token: o banco guarda apenas o SHA-256 (SEC-02). O valor em claro
existe uma única vez, na resposta do pareamento. Não há como recuperá-lo
depois — só gerar outro. É o mesmo comportamento de token de API do GitHub e
do próprio Supabase, e é o que impede que um vazamento do banco entregue as
credenciais dos dispositivos.
"""
import logging

logger = logging.getLogger(__name__)

# Campos devolvidos ao cliente. `token_hash` NUNCA entra nesta lista: ele não
# tem utilidade para a interface e é material sensível.
CAMPOS = "id, nome, created_at, last_seen_at, revoked_at"

NOME_PADRAO = "Smart Dormio"
NOME_MAXIMO = 60


def validar_nome(valor):
    """Devolve (nome, erro). Nome vazio vira o padrão, não erro."""
    if valor is None:
        return NOME_PADRAO, None
    if not isinstance(valor, str):
        return None, "nome deve ser texto"

    nome = valor.strip()
    if not nome:
        return NOME_PADRAO, None
    if len(nome) > NOME_MAXIMO:
        return None, f"nome deve ter no maximo {NOME_MAXIMO} caracteres"
    return nome, None


def listar(client, usuario_id):
    """Dispositivos do usuário, mais recentes primeiro."""
    try:
        resposta = (
            client.table("devices")
            .select(CAMPOS)
            .eq("user_id", usuario_id)
            .order("created_at", desc=True)
            .execute()
        )
        return resposta.data or []
    except Exception:
        logger.exception("Falha ao listar devices.")
        return None


def criar(client, usuario_id, nome, token_hash):
    """Cria o dispositivo. Devolve a linha criada ou None."""
    try:
        resposta = (
            client.table("devices")
            .insert({"user_id": usuario_id, "nome": nome, "token_hash": token_hash})
            .execute()
        )
        linhas = resposta.data or []
        return linhas[0] if linhas else None
    except Exception:
        logger.exception("Falha ao criar device.")
        return None


def renomear(client, usuario_id, device_id, nome):
    """Renomeia. O filtro por user_id acompanha o RLS — se um cair, o outro segura."""
    try:
        resposta = (
            client.table("devices")
            .update({"nome": nome})
            .eq("id", device_id)
            .eq("user_id", usuario_id)
            .execute()
        )
        linhas = resposta.data or []
        return linhas[0] if linhas else None
    except Exception:
        logger.exception("Falha ao renomear device.")
        return None


def revogar(client, usuario_id, device_id, agora):
    """Revoga por soft delete.

    A linha permanece de propósito: as leituras já gravadas referenciam este
    `device_id`, e apagá-lo transformaria histórico legítimo em dado órfão.
    O token para de valer imediatamente (SEC-02 rejeita `revoked_at` não nulo).
    """
    try:
        resposta = (
            client.table("devices")
            .update({"revoked_at": agora})
            .eq("id", device_id)
            .eq("user_id", usuario_id)
            .is_("revoked_at", "null")
            .execute()
        )
        linhas = resposta.data or []
        return linhas[0] if linhas else None
    except Exception:
        logger.exception("Falha ao revogar device.")
        return None
