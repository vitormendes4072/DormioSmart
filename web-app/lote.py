"""Ingestao em lote: `POST /api/data/lote` (API-03, contrato v2.6.0).

Funcoes puras, como `ingestao.py` e `validacao.py`: o envelope e a montagem da
resposta podem ser testados sem subir aplicacao.

── POR QUE EXISTE ──────────────────────────────────────────────────────

Drenar uma noite de 8 h pelo `POST /api/data` sao 960 requisicoes, cada uma
com um handshake TLS novo (`firmware/nucleo/capacidade.cpp`). Na arquitetura
decidida no ARQ-01 (sono leve + FIFO), o radio e 63 % da corrente media do
dispositivo com uma entrega por epoca; com uma entrega por hora, a corrente cai
de 5,31 para 2,03 mA (`scripts/estudo_cadencia.py`). O lote e o que torna a
entrega por hora possivel.

── O QUE A RESPOSTA PROMETE ────────────────────────────────────────────

Cada leitura do lote termina em exatamente UMA de tres listas, pelo indice
dela no array enviado:

  aceitas     gravadas e confirmadas. O dispositivo as apaga da fila.
  rejeitadas  invalidas (`{indice, erro}`). Reenviar nao adianta: o
              dispositivo as descarta, e o motivo vai para o log dele.
  pendentes   nao gravadas por falha do banco ou por falta de tempo. O
              dispositivo as reenvia no proximo lote.

A regra do FIX-02 continua valendo item a item: nada e "aceita" sem gravacao
confirmada. E vale para o lote inteiro: se NADA foi gravado e ha pendentes, a
resposta e 503, nao 200 — um 200 vazio pareceria sucesso para quem so olha o
codigo.

── POR QUE GRAVAR ITEM A ITEM, E NAO NUMA FUNCAO NOVA NO BANCO ─────────

O que custa energia e o enlace dispositivo → Vercel, e esse o lote resolve.
O enlace Vercel → Supabase continua uma chamada por leitura, pela mesma
funcao que o `POST /api/data` usa (`registrar_leitura`). Uma funcao de lote
no banco seria uma migracao nova a aplicar em producao para ganhar tempo de
servidor, que ninguem paga em bateria. O preco desta escolha e o tempo: por
isso o lote tem teto de tamanho e orcamento de tempo, e o que nao couber volta
como pendente em vez de estourar o limite da funcao serverless.
"""

#: Teto de leituras por lote. 60 epocas de 30 s = meia hora. Com uma entrega
#: por hora sao dois lotes, o que nao muda a conta de energia; com 120 por
#: lote, 120 chamadas ao banco arriscariam o limite de 10 s da funcao.
MAX_LEITURAS_POR_LOTE = 60

#: Segundos de trabalho antes de parar de gravar e devolver o resto como
#: pendente. Abaixo dos 10 s do Vercel com folga para a partida a frio.
ORCAMENTO_DE_TEMPO_S = 6.0


def extrair_leituras(corpo):
    """Le o array `leituras` do envelope.

    Devolve `(leituras, None, None)` ou `(None, motivo, status)`.

    413 para lote grande demais (o cliente precisa dividir, nao corrigir um
    campo); 400 para o resto.
    """
    if not isinstance(corpo, dict):
        return None, "corpo deve ser um objeto JSON", 400

    leituras = corpo.get("leituras")
    if leituras is None:
        return None, "campo leituras ausente", 400
    if not isinstance(leituras, list):
        return None, "campo leituras deve ser uma lista", 400
    if len(leituras) == 0:
        return None, "campo leituras vazio", 400
    if len(leituras) > MAX_LEITURAS_POR_LOTE:
        return None, (
            f"lote com {len(leituras)} leituras; o maximo e "
            f"{MAX_LEITURAS_POR_LOTE}"
        ), 413
    return leituras, None, None


def nova_resposta():
    return {"aceitas": [], "rejeitadas": [], "pendentes": []}


def status_da_resposta(resposta):
    """503 se nada foi gravado e algo ficou pendente; 200 nos demais casos.

    Lote todo rejeitado e 200: o servidor funcionou, as leituras e que nao
    prestam, e reenvia-las nao adianta.
    """
    if not resposta["aceitas"] and resposta["pendentes"]:
        return 503
    return 200
