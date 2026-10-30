"""As duas features que só o servidor pode calcular (DATA-07b (e), contrato §2.6).

O dispositivo envia 6 features e a direção da gravidade `g` de cada época. As
outras duas dependem da NOITE INTEIRA:

    inclinacao_rel = arccos( ĝ_t · ĝ_ref )     ĝ_ref = mediana geométrica de todas
    d_angulo       = arccos( ĝ_t · ĝ_{t-1} )

Quando o dispositivo envia a época 12, as épocas 13 em diante ainda não existem,
então `ĝ_ref` não tem como ser dele. Qualquer estimativa incremental seria OUTRO
estimador, e divergiria do que produziu os resultados do ML em silêncio.

── POR QUE PYTHON PURO, E NÃO O `ml/src/features.py` ─────────────────────

O backend roda no Vercel sem numpy nem scipy, e trazê-los para três funções de
vinte linhas pesaria no pacote e no cold start. Então a conta é reescrita aqui,
em laços — e a cópia é exatamente o risco que o dourado da fronteira B existe
para cobrir: `tests/test_features_noite.py` roda este módulo contra
`ml/testes/vetor_dourado_sequencias.json`, que o `ml/` grava com
`features_inter_epoca`. Onde os dois divergirem, é este que está errado.

── UMA DIFERENÇA DELIBERADA: O BURACO ─────────────────────────────────────

`features_inter_epoca` do `ml/` compara a época i com a i−1 da lista, sejam elas
separadas por 30 s ou por duas horas — as bases públicas não têm buracos, e a
documentação dela registra o limite. No dispositivo os buracos existem (Wi-Fi,
bateria, época recusada pela cadeia C2), e uma hora sem leitura apareceria como
uma virada enorme "em 30 s". Aqui, `d_angulo` é **None** na primeira época e em
toda época que começa mais de `LACUNA_MAXIMA_S` depois da anterior: "não sei" e
não "não girou". Para uma sequência sem buraco, o resultado é idêntico ao do
`ml/` — é o que o dourado confere.
"""
from __future__ import annotations

import math
import re
from datetime import datetime

#: Ordem canônica das oito (contrato §2.6). As seis primeiras vêm do dispositivo.
ORDEM_FEATURES = ("enmo_media", "enmo_desvio", "enmo_max", "mag_din_media",
                  "zcr", "p_frac", "inclinacao_rel", "d_angulo")
DO_DISPOSITIVO = ORDEM_FEATURES[:6]

#: Uma época de 30 s seguida da próxima começa 30 s depois. Acima de 45 s, pelo
#: menos uma época faltou no meio, e a comparação deixa de ser "época anterior".
LACUNA_MAXIMA_S = 45.0

#: Os mesmos de `direcao_referencia` no `ml/`: mudar um deles muda o estimador.
ITERACOES_WEISZFELD = 100
TOLERANCIA_WEISZFELD = 1e-9


def _norma(v):
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def unitario(v):
    """Norma 1. Vetor ~nulo volta inalterado, como no `ml/`."""
    n = _norma(v)
    if n < 1e-12:
        n = 1.0
    return (v[0] / n, v[1] / n, v[2] / n)


def direcao_referencia(gs):
    """Mediana GEOMÉTRICA dos vetores unitários, por Weiszfeld.

    Não a mediana por componente: aquela não é invariante a rotação, e
    `inclinacao_rel` precisa ser. Inicializa pela média e itera com os mesmos
    parâmetros do `ml/`.
    """
    u = [unitario(g) for g in gs]
    n = len(u)
    y = tuple(sum(v[k] for v in u) / n for k in range(3))
    for _ in range(ITERACOES_WEISZFELD):
        pesos = []
        for v in u:
            d = _norma((v[0] - y[0], v[1] - y[1], v[2] - y[2]))
            pesos.append(1.0 / (d if d >= 1e-12 else 1e-12))
        soma = sum(pesos)
        y_novo = tuple(sum(w * v[k] for w, v in zip(pesos, u)) / soma for k in range(3))
        passo = _norma((y_novo[0] - y[0], y_novo[1] - y[1], y_novo[2] - y[2]))
        y = y_novo
        if passo < TOLERANCIA_WEISZFELD:
            break
    return unitario(y)


def angulo_graus(u, v):
    """Ângulo entre dois unitários, em graus, com o cosseno saturado em [−1, 1]."""
    c = u[0] * v[0] + u[1] * v[1] + u[2] * v[2]
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def features_inter_epoca(gs):
    """A mesma assinatura de `ml/src/features.py::features_inter_epoca`.

    Devolve `(inclinacao_rel, d_angulo, g_ref)`, com `d_angulo[0] = 0` como no
    `ml/` — é a forma que o dourado confere. Quem tem instante por época usa
    `derivar_noite`, que trata o buraco.
    """
    if not gs:
        return [], [], None
    u = [unitario(g) for g in gs]
    ref = direcao_referencia(gs)
    inclinacao = [angulo_graus(v, ref) for v in u]
    d = [0.0] + [angulo_graus(u[i], u[i - 1]) for i in range(1, len(u))]
    return inclinacao, d, ref


def derivar_noite(epocas):
    """As oito features de cada época de uma janela, mais o `g_ref` usado.

    `epocas`: lista de dicionários com `instante` (datetime com fuso), `g` (3
    números) e as seis features do dispositivo, pelo nome. Ordena por instante.
    Devolve `(lista de dicionários, g_ref)`; cada dicionário traz `instante` em
    ISO 8601, as oito pelo nome e `fs`.

    ⚠️ `g_ref` depende de QUAIS épocas entram: a mesma época tem outra
    `inclinacao_rel` numa janela diferente. Por isso a resposta da rota devolve
    o `g_ref` e a janela, e o conceito de "noite" fica com quem pede (`ESC-01`).
    """
    ordenadas = sorted(epocas, key=lambda e: e["instante"])
    inclinacao, d_sem_lacuna, ref = features_inter_epoca([e["g"] for e in ordenadas])
    saida = []
    anterior = None
    for i, e in enumerate(ordenadas):
        lacuna = anterior is None or (
            (e["instante"] - anterior).total_seconds() > LACUNA_MAXIMA_S)
        linha = {"instante": e["instante"].isoformat()}
        for nome in DO_DISPOSITIVO:
            linha[nome] = e[nome]
        linha["inclinacao_rel"] = inclinacao[i]
        linha["d_angulo"] = None if lacuna else d_sem_lacuna[i]
        linha["fs"] = e.get("fs")
        saida.append(linha)
        anterior = e["instante"]
    return saida, (list(ref) if ref is not None else None)


_FRACAO = re.compile(r"\.(\d+)(?=[+-]\d\d:?\d\d$|$)")


def instante_do_banco(valor):
    """`timestamptz` como o PostgREST o devolve, para datetime com fuso.

    `fromisoformat` só aceita fração de 3 ou 6 dígitos antes do Python 3.11, e
    o Postgres omite os zeros à direita (`...:00.12+00:00`). A fração é
    completada para 6 dígitos aqui, para não depender da versão do deploy.
    """
    texto = str(valor).strip()
    if texto.endswith(("Z", "z")):
        texto = texto[:-1] + "+00:00"
    texto = _FRACAO.sub(lambda m: "." + (m.group(1) + "000000")[:6], texto)
    return datetime.fromisoformat(texto)


def epoca_da_linha(linha):
    """Traduz uma linha de `sleep_data` (migração 010) para `derivar_noite`.

    Devolve None para linha sem vetor ou sem `captured_at`: sem o instante da
    MEDIÇÃO não há como ordenar a noite nem reconhecer um buraco, e o
    `created_at` é a hora de chegada — com o buffer, horas depois.
    """
    if linha.get("fs_features") is None or not linha.get("captured_at"):
        return None
    epoca = {"instante": instante_do_banco(linha["captured_at"]),
             "g": (linha["g_x"], linha["g_y"], linha["g_z"]),
             "fs": linha["fs_features"]}
    for nome in DO_DISPOSITIVO:
        epoca[nome] = linha[nome]
    return epoca
