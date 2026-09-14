"""As oito features por época. Todas invariantes à orientação.

=============================================================================
DECISÃO TÉCNICA 1 — o problema do ângulo, e como foi resolvido
=============================================================================
O plano original (§7 do ML-DATASETS-E-PLANO.md) listava `angulo_z`:

    angulo_z = atan2(az, sqrt(ax^2 + ay^2))

**Essa feature NÃO transfere entre dataset e Dormio, e foi substituída.**

Por quê: ela depende de qual eixo físico é o "z" e de o aparelho estar montado
sempre do mesmo jeito. Nos datasets isso vale — o protocolo de uso fixa a
orientação (o relógio vai no punho de um jeito só, o ActivPAL é colado na coxa
com fita). **Num travesseiro a orientação é arbitrária E muda durante a noite**,
porque o travesseiro vira. Um modelo treinado com `angulo_z` aprende a
orientação de montagem do dataset, não o movimento.

O que entrou no lugar — duas features, ambas construídas sobre o vetor
gravidade estimado `ĝ` (unitário), e ambas **invariantes a qualquer rotação
fixa do referencial do sensor**:

  inclinacao_rel = arccos( ĝ_t · ĝ_ref )
      Ângulo entre a direção da gravidade agora e a **direção de referência da
      própria gravação** (mediana direcional ao longo da noite). Responde
      "quão longe da orientação típica DESTE aparelho ele está agora?" — que é
      transferível — em vez de "quão longe do eixo z do fabricante?" — que não é.

  d_angulo = arccos( ĝ_t · ĝ_{t-1} )
      Magnitude da reorientação entre épocas vizinhas. É o evento de virada.

A prova de invariância é uma linha: se o sensor inteiro sofre uma rotação fixa
R, então (R ĝ_a) · (R ĝ_b) = ĝ_a^T R^T R ĝ_b = ĝ_a · ĝ_b, porque R é ortogonal.
Os dois produtos internos — e portanto os dois ângulos — não mudam.

Ambas são calculáveis no ESP32: `ĝ` sai de uma média móvel exponencial da
aceleração bruta (memória O(1)); `ĝ_ref` sai de um acumulador direcional com
aquecimento. ⚠️ **Consequência operacional para o firmware:** `inclinacao_rel`
precisa de um período de aquecimento antes de valer — as primeiras épocas da
noite têm referência instável. Tratar como ausente até o aquecimento fechar.

=============================================================================
DECISÃO TÉCNICA 2 — a SMA clássica saiu; entrou a magnitude dinâmica média
=============================================================================
O plano listava `SMA = (1/T)·Σ(|ax|+|ay|+|az|)` sobre a aceleração bruta.
**Isso é sensível à orientação, e de um jeito grave.** A norma L1 não é
invariante a rotação: para um vetor de gravidade de módulo 1 g, |ax|+|ay|+|az|
vale 1,0 g se um eixo aponta para baixo e √3 ≈ 1,73 g se a gravidade se
reparte igualmente pelos três. **São 73% de variação só por causa de como o
aparelho está deitado, antes de qualquer movimento.**

Primeira tentativa: calcular a L1 sobre a **componente dinâmica** (bruto menos
gravidade estimada), de média ~zero. Isso derruba o viés de 73% para a faixa
||v||₂ ≤ ||v||₁ ≤ √3·||v||₂ sobre um sinal pequeno — **mas não zera**.

**O teste de invariância a rotação reprovou essa versão** (`testes/
test_vetor_dourado.py::test_features_invariantes_a_rotacao`): girando o
referencial, a feature variava ~6%. Não é ruído de ponto flutuante, é a
propriedade matemática da L1. E 6% de variação por causa de **como o aparelho
foi montado** é exatamente o que faz um modelo aprender a orientação do dataset
em vez do movimento — o problema que esta lista de features existe para evitar.

**Decisão final: `mag_din_media` = média de ||a − ĝ||₂.** A norma L2 é
exatamente invariante a rotação (‖Rv‖₂ = ‖v‖₂ para R ortogonal), então a feature
passa o teste por construção, não por tolerância. Serve ao mesmo propósito da
SMA — medida barata de quanto movimento houve na época — e custa uma raiz
quadrada por amostra no ESP32, que cabe.

⚠️ **Consequência para o texto do TCC:** isto **não é a SMA clássica** da
literatura de actigrafia. Se a feature for citada, citar como "magnitude média
da aceleração dinâmica", não como *signal magnitude area*. A troca e o motivo
estão registrados aqui.

=============================================================================
Ordem canônica das features — o firmware DEVE emitir nesta ordem
=============================================================================
"""

from __future__ import annotations

import numpy as np
from scipy.signal import butter, filtfilt

__all__ = ["NOMES_FEATURES", "features_de_epoca", "estimar_gravidade", "direcao_referencia"]

#: Ordem canônica. `DATA-07` (contrato de dados) e o firmware seguem esta ordem.
NOMES_FEATURES: tuple[str, ...] = (
    "enmo_media",
    "enmo_desvio",
    "enmo_max",
    "mag_din_media",   # substituiu `sma_din` — ver DECISÃO TÉCNICA 2
    "zcr",
    "p_frac",
    "inclinacao_rel",
    "d_angulo",
)

#: Features cujo valor depende do filtro que estima a gravidade. O firmware
#: aproxima esse filtro, então a paridade Python↔C++ delas tem tolerância
#: declarada (ver testes/test_vetor_dourado.py). As demais batem exatamente.
FEATURES_DEPENDENTES_DO_FILTRO: frozenset[str] = frozenset(
    {"mag_din_media", "p_frac"}
)

#: Corte do passa-baixa que separa gravidade de aceleração dinâmica.
#: 0,25 Hz é o valor usual na área (a gravidade é quase-DC; o movimento humano
#: tem energia predominante em 0,3–3,5 Hz).
CORTE_GRAVIDADE_HZ = 0.25

#: Limiar de `p_frac`, em g, sobre a magnitude dinâmica.
#: 1,2 m/s² / 9,80665 ≈ 0,1224 g — é o limiar que o Dormio já usa hoje
#: (`DATA-02`). ⚠️ Provisório: nasceu de medição por contato de jumper, antes da
#: solda e antes do FW-06. Recalibrar com `CAL-01`/`CAL-02`.
LIMIAR_P_FRAC_G = 1.2 / 9.80665


def estimar_gravidade(a: np.ndarray, fs: float) -> np.ndarray:
    """Componente de gravidade, por passa-baixa de fase zero. `a` em g, (n, 3)."""
    a = np.asarray(a, dtype=float)
    nyq = fs / 2.0
    if CORTE_GRAVIDADE_HZ >= nyq:
        return a.copy()
    b, aa = butter(2, CORTE_GRAVIDADE_HZ / nyq, btype="low")
    if a.shape[0] <= 3 * max(len(aa), len(b)):
        # Janela curta demais para filtrar: a média é o melhor estimador de DC.
        return np.repeat(a.mean(axis=0, keepdims=True), a.shape[0], axis=0)
    return filtfilt(b, aa, a, axis=0)


def _unitario(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    n = np.where(n < 1e-12, 1.0, n)
    return v / n


def direcao_referencia(
    g_epocas: np.ndarray, n_iter: int = 100, tol: float = 1e-9
) -> np.ndarray:
    """Direção de gravidade de referência da gravação inteira.

    Mediana GEOMÉTRICA (L1) dos vetores unitários, via Weiszfeld — não a
    mediana por componente. Robusta às épocas de virada, que são exatamente
    as atípicas, mas a robustez não é o único requisito: a mediana por
    componente NÃO é equivariante a rotação (`test_features_invariantes_a_
    rotacao` pegou isso), porque opera eixo a eixo. A mediana geométrica só
    depende de distâncias euclidianas entre os vetores — ‖Ra−Rb‖ = ‖a−b‖ para
    R ortogonal — então herda a invariância que `inclinacao_rel` exige.

    A inicialização (média) e cada passo de Weiszfeld são equivariantes por
    serem médias ponderadas por pesos que só dependem de normas; com o mesmo
    número de iterações dos dois lados, o resultado é equivariante a menos de
    arredondamento de ponto flutuante.
    """
    u = _unitario(np.asarray(g_epocas, dtype=float))
    y = u.mean(axis=0)
    for _ in range(n_iter):
        d = np.linalg.norm(u - y, axis=1)
        d = np.where(d < 1e-12, 1e-12, d)
        w = 1.0 / d
        y_novo = (w[:, None] * u).sum(axis=0) / w.sum()
        if np.linalg.norm(y_novo - y) < tol:
            y = y_novo
            break
        y = y_novo
    return _unitario(y)


def _angulo_entre(u: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Ângulo em graus entre vetores unitários, por linha."""
    c = np.clip(np.sum(u * v, axis=-1), -1.0, 1.0)
    return np.degrees(np.arccos(c))


def features_de_epoca(
    a_epocas: np.ndarray,
    fs: float,
    limiar_p_frac_g: float = LIMIAR_P_FRAC_G,
) -> tuple[np.ndarray, np.ndarray]:
    """Extrai as 8 features de cada época.

    Parameters
    ----------
    a_epocas : (n_epocas, n_amostras, 3) aceleração em **g**, já na grade comum.
    fs : taxa da grade comum, Hz.

    Returns
    -------
    X : (n_epocas, 8) na ordem de NOMES_FEATURES.
    g_media : (n_epocas, 3) vetor gravidade médio por época (útil para depurar).
    """
    a_epocas = np.asarray(a_epocas, dtype=float)
    if a_epocas.ndim != 3 or a_epocas.shape[2] != 3:
        raise ValueError(f"esperado (n_epocas, n_amostras, 3), recebido {a_epocas.shape}")

    n_ep, n_am, _ = a_epocas.shape
    X = np.zeros((n_ep, len(NOMES_FEATURES)), dtype=float)
    g_media = np.zeros((n_ep, 3), dtype=float)

    # --- por época: ENMO, magnitude dinâmica, zcr, p_frac ------------------
    for i in range(n_ep):
        a = a_epocas[i]
        grav = estimar_gravidade(a, fs)
        din = a - grav
        g_media[i] = grav.mean(axis=0)

        # ENMO: max(|a|/g - 1, 0). `a` já está em g, então |a| - 1.
        # O max(., 0) é um RETIFICADOR: em repouso o valor verdadeiro é zero,
        # mas o ruído oscila para os dois lados e só o lado negativo é cortado.
        # O ruído portanto NÃO se cancela — vira um viés positivo. Ver §2.2 do
        # ML-DATASETS-E-PLANO.md para o piso que isso impõe (~0,64 mg no
        # MPU6050, ~1,95 mg no Empatica E4).
        enmo = np.maximum(np.linalg.norm(a, axis=1) - 1.0, 0.0)
        X[i, 0] = enmo.mean()
        X[i, 1] = enmo.std()
        X[i, 2] = enmo.max()

        # Magnitude média da aceleração dinâmica — norma L2, exatamente
        # invariante a rotação. Substituiu a SMA (L1), que não era.
        # Ver DECISÃO TÉCNICA 2 no topo do módulo.
        X[i, 3] = np.linalg.norm(din, axis=1).mean()

        # zcr sobre um escalar invariante a rotação: a magnitude dinâmica sem DC.
        s = np.linalg.norm(a, axis=1)
        s = s - s.mean()
        X[i, 4] = float(np.count_nonzero(np.diff(np.signbit(s)))) / max(n_am - 1, 1)

        # p_frac: fração da época acima do limiar. É o que o Dormio calcula hoje.
        X[i, 5] = float(np.count_nonzero(np.linalg.norm(din, axis=1) > limiar_p_frac_g)) / n_am

    # --- entre épocas: os dois ângulos -------------------------------------
    u = _unitario(g_media)
    u_ref = direcao_referencia(g_media)
    X[:, 6] = _angulo_entre(u, np.broadcast_to(u_ref, u.shape))

    d = np.zeros(n_ep, dtype=float)
    if n_ep > 1:
        d[1:] = _angulo_entre(u[1:], u[:-1])
    X[:, 7] = d

    return X, g_media
