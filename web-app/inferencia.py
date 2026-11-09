"""Inferência sono/vigília por época (ML-INF), com o modelo `ml-inf-cabeca-v2`.

O modelo vem de `ml/experimentos/ml_inf_v2.py` (PR #100): regressão logística
balanceada, treinada no braço de cabeça do Wearanize+ OA, com as oito features,
z-score da noite pelas épocas dela mesma e contexto de ±11 épocas — a
configuração `item9_ctx11` do ML-04, que reproduziu os κ publicados de
Newcastle, Walch e DREAMT. `web-app/modelos/` guarda uma CÓPIA byte a byte de
`ml/modelos/`; `tests/test_inferencia.py` confere o SHA-256 das duas.

── SOB DEMANDA, SEM GRAVAR ────────────────────────────────────────────────

O plano de ML previa um job em lote ao fim da sessão. Aqui a conta é feita a
cada pedido, sobre a janela que o pedido define, e o resultado não é gravado:
não há migração, não há dado de saúde inferido guardado no banco, e uma versão
nova do modelo vale na hora. O custo é refazer ~2 880 × 184 multiplicações no
pior caso (24 h), o que cabe numa requisição.

── A JANELA FAZ PARTE DO RESULTADO ────────────────────────────────────────

O z-score é calculado sobre as épocas da JANELA PEDIDA. O modelo foi treinado
com noites inteiras; uma janela de duas horas no meio da noite normaliza
diferente e pode classificar a mesma época de outro jeito. Por isso a rota
devolve a janela usada, como `/api/features` já devolve o `g_ref`. O que é
"uma noite" é decisão do `ESC-01`, não deste módulo.

── PYTHON PURO ─────────────────────────────────────────────────────────────

Pelo mesmo motivo de `features_noite.py`: o backend roda na Vercel sem numpy.
As somas usam `math.fsum`, que não depende da ordem; o dourado da v2
(`ml/testes/fixtures/ml-inf-cabeca-v2-dourado.json`) é conferido com tolerância
absoluta de 1e-12 na probabilidade e classe exata.
"""
from __future__ import annotations

import json
import logging
import math
from numbers import Real
from pathlib import Path

from features_noite import (LACUNA_MAXIMA_S, ORDEM_FEATURES, derivar_noite,
                            epoca_da_linha, instante_do_banco)

logger = logging.getLogger(__name__)

VERSAO = "ml-inf-cabeca-v2"
CAMINHO_MODELO = Path(__file__).resolve().parent / "modelos" / f"{VERSAO}.json"

#: A grade em que o modelo foi treinado. As features de outra duração de época
#: ou de outra taxa descrevem outra coisa; a validação de entrada aceita
#: `epoca_s` de 1 a 3600 s e `fs` até 200 Hz, então o filtro é daqui.
EPOCA_DO_MODELO_S = 30
FS_DO_MODELO = 32.0

#: O que o contrato da v2 fixa e este módulo implementa. Um JSON que diga outra
#: coisa é recusado inteiro: aplicar coeficientes com a regra errada produz
#: probabilidades plausíveis e erradas, em silêncio.
_CONTRATO = {
    "versao": VERSAO,
    "configuracao": "item9_ctx11",
    "classe_positiva": 1,
    "limiar": 0.5,
    "comparacao": ">",
    "regra_classe": "logit > 0",
    "classe_empate": 0,
}
_NORMALIZACAO = {"ddof": 1, "piso_desvio": 1e-9, "desvio_substituto": 1.0,
                 "minimo_epocas_validas": 23, "d_angulo_ausente_na_borda": 0.0}
_CONTEXTO = {"vizinhas": 11, "preenchimento": "replicar_ponta_do_segmento",
             "quebra_servidor_s": LACUNA_MAXIMA_S, "comparacao_lacuna": ">"}


class ModeloInvalido(ValueError):
    """O JSON não é o modelo que este módulo sabe aplicar."""


class AbaixoDoPiso(ValueError):
    """A janela tem menos épocas válidas do que a normalização exige."""

    def __init__(self, validas, minimo):
        super().__init__(f"{validas} epocas validas; minimo {minimo}")
        self.validas = validas
        self.minimo = minimo


def colunas_esperadas(vizinhas=_CONTEXTO["vizinhas"]):
    """Blocos de deslocamento −n..+n, com as oito features dentro de cada um."""
    return [f"{nome}__{d:+d}" for d in range(-vizinhas, vizinhas + 1)
            for nome in ORDEM_FEATURES]


def _finito(v):
    return isinstance(v, Real) and not isinstance(v, bool) and math.isfinite(v)


def validar_modelo(m):
    """Devolve o próprio dicionário se ele cumpre o contrato; senão levanta."""
    for chave, esperado in _CONTRATO.items():
        if m.get(chave) != esperado:
            raise ModeloInvalido(f"{chave}: esperado {esperado!r}, veio {m.get(chave)!r}")
    if tuple(m.get("features", ())) != ORDEM_FEATURES:
        raise ModeloInvalido("features fora da ordem canonica do servidor")
    if {"medias", "escalas"} & m.keys():
        raise ModeloInvalido("o modelo traz escala global; a v2 normaliza por noite")
    for grupo, esperado in (("normalizacao", _NORMALIZACAO), ("contexto", _CONTEXTO)):
        bloco = m.get(grupo) or {}
        for chave, valor in esperado.items():
            if bloco.get(chave) != valor:
                raise ModeloInvalido(f"{grupo}.{chave}: esperado {valor!r}, veio {bloco.get(chave)!r}")
    colunas = colunas_esperadas()
    if m.get("colunas_contexto") != colunas:
        raise ModeloInvalido("colunas_contexto fora da ordem do empilhamento")
    coeficientes = m.get("coeficientes")
    if not isinstance(coeficientes, list) or len(coeficientes) != len(colunas):
        raise ModeloInvalido(f"esperados {len(colunas)} coeficientes")
    if not all(map(_finito, [*coeficientes, m.get("intercepto")])):
        raise ModeloInvalido("coeficiente ou intercepto nao finito")
    return m


def carregar_modelo(caminho=None):
    caminho = Path(caminho or CAMINHO_MODELO)
    return validar_modelo(json.loads(caminho.read_text(encoding="utf-8")))


_cache = {}


def modelo_carregado():
    """O modelo validado, carregado na primeira chamada; None se falhar.

    A falha fica no log e NÃO derruba o app: a ingestão não depende do modelo,
    e um JSON ausente no pacote da Vercel não pode parar o dispositivo de
    gravar. Só a rota de inferência responde 503, e o `/health` diz qual.
    """
    if "modelo" not in _cache:
        try:
            _cache["modelo"] = carregar_modelo()
        except Exception:
            logger.exception("Falha ao carregar o modelo de inferencia.")
            return None
    return _cache["modelo"]


def _valor(epoca, nome):
    v = epoca[nome]
    if nome == "d_angulo" and v is None:
        # `derivar_noite` diz None na primeira época e depois de uma lacuna; o
        # treino viu 0 na primeira época de cada sequência (contrato da v2).
        return 0.0
    return float(v) if _finito(v) else math.nan


def _zscore(X, ddof, piso, substituto):
    n = len(X)
    colunas = list(zip(*X))
    medias = [math.fsum(c) / n for c in colunas]
    desvios = []
    for c, mu in zip(colunas, medias):
        s = math.sqrt(math.fsum((x - mu) ** 2 for x in c) / (n - ddof))
        desvios.append(s if s >= piso else substituto)
    return [[(x - mu) / s for x, mu, s in zip(linha, medias, desvios)] for linha in X]


def _segmentos(instantes, quebra_s):
    seg, atual = [0], 0
    for a, b in zip(instantes, instantes[1:]):
        if (b - a).total_seconds() > quebra_s:
            atual += 1
        seg.append(atual)
    return seg


def _sigmoide(z):
    e = math.exp(-abs(z))
    return 1 / (1 + e) if z >= 0 else e / (1 + e)


def classe(z):
    """1 (sono) só com logit estritamente positivo: 0,5 exato é vigília, como no
    `predict` do scikit-learn que o ML-04 usou. Decidir pelo logit, e não pela
    probabilidade, evita que o arredondamento da sigmoide mude a classe."""
    return int(z > 0)


def pontuar(modelo, contexto):
    """Logit de uma linha já empilhada, na ordem de `colunas_contexto`."""
    return modelo["intercepto"] + math.fsum(
        w * x for w, x in zip(modelo["coeficientes"], contexto, strict=True))


def inferir_janela(linhas, modelo):
    """Linhas de `sleep_data` (como `get_features_do_usuario` devolve) → épocas.

    Devolve `{"epocas": [{instante, prob_sono, classe}], "n_segmentos",
    "excluidas": {"fora_da_grade", "invalidas"}}`, com classe 1 = sono e
    0 = vigília. Levanta `AbaixoDoPiso` com menos épocas válidas que o mínimo.
    """
    norm, ctx = modelo["normalizacao"], modelo["contexto"]
    epocas, fora_da_grade = [], 0
    for linha in linhas:
        epoca = epoca_da_linha(linha)
        if epoca is None:
            continue
        # Antes de derivar: uma época de outra grade não entra no `g_ref`.
        if linha.get("epoca_segundos") != EPOCA_DO_MODELO_S or epoca["fs"] != FS_DO_MODELO:
            fora_da_grade += 1
            continue
        epocas.append(epoca)

    derivadas, _ = derivar_noite(epocas)
    X, instantes = [], []
    for e in derivadas:
        x = [_valor(e, nome) for nome in ORDEM_FEATURES]
        if all(map(math.isfinite, x)):
            X.append(x)
            instantes.append(e["instante"])
    invalidas = len(derivadas) - len(X)
    if len(X) < norm["minimo_epocas_validas"]:
        raise AbaixoDoPiso(len(X), norm["minimo_epocas_validas"])

    Z = _zscore(X, norm["ddof"], norm["piso_desvio"], norm["desvio_substituto"])
    seg = _segmentos([instante_do_banco(t) for t in instantes], ctx["quebra_servidor_s"])
    inicio, fim = {}, {}
    for i, s in enumerate(seg):
        inicio.setdefault(s, i)
        fim[s] = i
    deslocamentos = range(-ctx["vizinhas"], ctx["vizinhas"] + 1)

    saida = []
    for i, s in enumerate(seg):
        contexto = []
        for d in deslocamentos:
            # Replica a época da ponta do segmento nas bordas e junto às lacunas.
            contexto.extend(Z[max(inicio[s], min(i + d, fim[s]))])
        z = pontuar(modelo, contexto)
        saida.append({"instante": instantes[i], "prob_sono": _sigmoide(z),
                      "classe": classe(z)})
    return {"epocas": saida, "n_segmentos": seg[-1] + 1,
            "excluidas": {"fora_da_grade": fora_da_grade, "invalidas": invalidas}}
