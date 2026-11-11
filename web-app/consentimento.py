"""O consentimento específico e destacado para dado de saúde (LGPD-12).

A política trata a série de movimento e a estimativa de sono como dado de saúde (art. 11, I):
sem o consentimento na versão vigente do texto, nada disso é tratado. A garantia está no BANCO
(migração 017: a gravação pela sessão e o pareamento recusam). Este módulo existe para o backend
responder 403 com o motivo, em vez de deixar a recusa do banco virar um 503 genérico — que o app
leria como "servidor fora do ar" e tentaria de novo para sempre.

`VERSAO` é a mesma de `public.versao_do_consentimento()` (017) e de `VERSAO_DO_CONSENTIMENTO` no
frontend; `tests/test_consentimento.py` confere as três.
"""
import logging

import perfil

logger = logging.getLogger(__name__)

VERSAO = "2026-11-10"

PENDENTE = "consentimento para dado de saude pendente"


def vigente(dados_do_perfil):
    """True quando o perfil tem o consentimento na versão vigente."""
    return bool(dados_do_perfil) and dados_do_perfil.get("consentimento_saude_versao") == VERSAO


def estado(client, usuario_id):
    """`True`, `False`, ou `None` quando o banco não respondeu.

    `None` não é "sem consentimento": tratar falha de infraestrutura como recusa
    responderia 403 a quem consentiu, e o app pediria o consentimento de novo.
    """
    dados = perfil.ler(client, usuario_id)
    if dados is None:
        return None
    return vigente(dados)


def registrar(client, versao):
    """Grava o consentimento pela função do banco. Devolve o recibo, ou None se falhou."""
    try:
        resposta = client.rpc("consentir_dado_de_saude", {"p_versao": versao}).execute()
        return getattr(resposta, "data", None)
    except Exception:
        logger.exception("Falha ao registrar o consentimento.")
        return None
