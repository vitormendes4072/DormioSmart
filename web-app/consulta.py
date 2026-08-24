"""Parametros da consulta de leituras (DASH-05, DASH-06).

Funcoes puras, sem Flask: a decisao de aceitar ou recusar um parametro pode
ser testada sem subir aplicacao. Mesma escolha de `validacao.py`.

── POR QUE 400, E NAO LISTA VAZIA ───────────────────────────────────────

`GET /api/sleep-history` sempre devolveu lista, nunca 500 (FIX-01). Isso vale
para *falha de infraestrutura*: banco fora do ar nao deve derrubar o painel.

Nao vale para *parametro malformado*. Um `device` com uuid digitado errado que
respondesse `[]` mostraria um grafico vazio e deixaria o usuario concluindo que
o dispositivo nao mandou nada. Erro do cliente responde 400 e diz o que esta
errado; indisponibilidade continua respondendo lista.

── POR QUE O `device` DO CLIENTE E SEGURO ───────────────────────────────

O `device_id` vem da query string, mas o `user_id` NUNCA vem — ele sai do JWT
validado. A consulta filtra pelos dois, e o RLS filtra de novo no banco. Pedir
o dispositivo de outra pessoa devolve vazio porque o `user_id` nao casa, nao
porque confiamos no parametro.
"""
import re
from datetime import datetime

LIMITE_PADRAO = 20
# Uma noite agregada em epocas de 60 s da ~480 linhas. O teto e folgado o
# bastante para varias noites e apertado o bastante para ninguem pedir a base
# inteira numa requisicao.
LIMITE_MAXIMO = 2000

_UUID = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def validar_uuid(valor):
    """Devolve o uuid normalizado em minusculas, ou None se nao for uuid."""
    if not isinstance(valor, str):
        return None
    valor = valor.strip()
    return valor.lower() if _UUID.match(valor) else None


def validar_instante(valor):
    """Devolve o instante ISO 8601 normalizado, ou None se nao for valido.

    Aceita o sufixo `Z`, que `fromisoformat` so entende a partir do 3.11 —
    normalizar aqui evita depender da versao do interpretador do deploy.
    """
    if not isinstance(valor, str):
        return None
    texto = valor.strip()
    if not texto:
        return None
    if texto.endswith(("Z", "z")):
        texto = texto[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(texto).isoformat()
    except ValueError:
        return None


def validar_limite(valor):
    """Devolve o limite dentro do teto, ou None se nao for inteiro positivo."""
    if valor is None:
        return LIMITE_PADRAO
    try:
        # `int(valor)` aceitaria "20.5"? Nao — ValueError. Mas aceita bool,
        # que nao chega aqui porque a origem e sempre string de query.
        numero = int(str(valor).strip())
    except (TypeError, ValueError):
        return None
    if numero < 1:
        return None
    return min(numero, LIMITE_MAXIMO)


def ler_parametros(args):
    """Interpreta a query string. Devolve `(parametros, erro)`.

    `args` e qualquer mapeamento com `.get` — `request.args` do Flask ou um
    dicionario nos testes.
    """
    parametros = {"device_id": None, "desde": None, "ate": None, "limite": LIMITE_PADRAO}

    bruto = args.get("device")
    if bruto not in (None, ""):
        device_id = validar_uuid(bruto)
        if device_id is None:
            return None, "parametro 'device' nao e um uuid valido"
        parametros["device_id"] = device_id

    for nome in ("desde", "ate"):
        bruto = args.get(nome)
        if bruto in (None, ""):
            continue
        instante = validar_instante(bruto)
        if instante is None:
            return None, f"parametro '{nome}' nao e um instante ISO 8601 valido"
        parametros[nome] = instante

    if parametros["desde"] and parametros["ate"]:
        if parametros["desde"] > parametros["ate"]:
            return None, "'desde' e posterior a 'ate'"

    bruto = args.get("limite")
    if bruto not in (None, ""):
        limite = validar_limite(bruto)
        if limite is None:
            return None, "parametro 'limite' deve ser inteiro maior que zero"
        parametros["limite"] = limite

    return parametros, None
