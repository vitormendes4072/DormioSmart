"""Quem esta enviando a leitura? (APP-08, contrato v2.2.0)

Funcoes puras: a decisao de qual caminho de autenticacao usar pode ser
testada sem subir aplicacao. Mesma escolha de `validacao.py` e `consulta.py`.

── POR QUE EXISTEM DOIS CAMINHOS ────────────────────────────────────────

O `X-Device-Token` nasceu para o ESP32, e a razao e simples: **o ESP32 nao
tem login**. Nao ha usuario sentado na frente dele, nao ha sessao, nao ha
como renovar credencial. Um segredo longo, gravado no `secrets.h`, e o que
resta.

O celular nao tem esse problema. Quem abre a tela de coleta ja esta
autenticado — a mesma sessao que carrega o painel. Exigir que essa pessoa
pareie um dispositivo, copie um token de 43 caracteres e cole noutra tela e
pedir que ela faca a mao o que o navegador ja fez.

Pior: coloca uma credencial de ESCRITA dentro do navegador, onde nao existe
equivalente ao Keystore do Android. O melhor que da para fazer la e
`sessionStorage`, que apenas encurta a janela de exposicao.

Com autenticacao por sessao, **nao ha token nenhum no navegador**. Nao ha o
que um XSS exfiltrar.

── A REGRA DE SEGURANCA ─────────────────────────────────────────────────

Nos dois caminhos, o `user_id` NUNCA vem do corpo da requisicao:

  - por token   : sai da linha do dispositivo, resolvida pelo hash do token;
  - por sessao  : sai do JWT validado.

O que o cliente informa, no caminho por sessao, e apenas QUAL dos seus
dispositivos esta enviando. E isso e conferido contra o dono antes de
qualquer escrita. Pedir para gravar no dispositivo de outra pessoa responde
como "nao encontrado" — mesma resposta de id inexistente, porque distinguir
os dois casos permitiria descobrir ids alheios.
"""

CAMINHO_TOKEN = "token"
CAMINHO_SESSAO = "sessao"


def identificar_caminho(headers):
    """Qual caminho de autenticacao a requisicao esta usando?

    Devolve `CAMINHO_TOKEN`, `CAMINHO_SESSAO` ou None.

    O token tem precedencia: e o caminho do dispositivo em campo, e um ESP32
    nunca manda `Authorization`. Se os dois vierem — cenario que so acontece
    por engano de cliente — vale o token, porque e o mais especifico.
    """
    if headers is None:
        return None

    if _tem_valor(headers, "X-Device-Token"):
        return CAMINHO_TOKEN

    autorizacao = _valor(headers, "Authorization")
    if isinstance(autorizacao, str) and autorizacao.strip().lower().startswith("bearer "):
        return CAMINHO_SESSAO

    return None


def _valor(headers, nome):
    try:
        return headers.get(nome)
    except Exception:
        return None


def _tem_valor(headers, nome):
    bruto = _valor(headers, nome)
    return isinstance(bruto, str) and bruto.strip() != ""


def extrair_device_id(corpo):
    """Le o `device_id` do corpo, no caminho por sessao.

    Devolve `(device_id, None)` ou `(None, motivo)`.

    Obrigatorio aqui, e nao opcional com algum padrao: adivinhar "o
    dispositivo celular do usuario" dentro da rota de ingestao faria a
    gravacao depender de um estado que o cliente nao declarou. Quem envia diz
    de onde veio; o backend so confere se pode.
    """
    if not isinstance(corpo, dict):
        return None, "corpo deve ser um objeto JSON"

    bruto = corpo.get("device_id")
    if bruto is None or (isinstance(bruto, str) and bruto.strip() == ""):
        return None, "campo device_id ausente (obrigatorio na ingestao por sessao)"

    if not isinstance(bruto, str):
        return None, "campo device_id deve ser texto"

    return bruto.strip(), None
