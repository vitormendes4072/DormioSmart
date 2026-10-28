"""Vetor dourado: as três implementações calculam a MESMA feature.

Por que este teste é o mais importante dos três
-----------------------------------------------
O `DATA-07` manda o dispositivo enviar o vetor de features por época, não o
sinal bruto. Isso significa que existem **duas implementações** da mesma
fórmula: a de Python (aqui) e a de C++ (no ESP32). Duas implementações da mesma
fórmula divergem — é quase certo — e a divergência é **silenciosa**: o modelo
treina numa definição de `enmo_media` e roda sobre outra, e ninguém vê.

=============================================================================
As DUAS fronteiras (contrato v2.5.0) — e por que o dourado tem dois arquivos
=============================================================================
A v2.5.0 mudou o que viaja: o dispositivo manda **6 features + `ĝ` bruto**, e o
servidor deriva as outras 2 sobre a noite inteira. São duas fronteiras, com
riscos de natureza diferente, e cada uma tem o seu arquivo:

  ┌─ FRONTEIRA A — dispositivo · `vetor_dourado.json` ─────────────────────┐
  │ Python ↔ C++, duas linguagens, dois compiladores, dois tamanhos de     │
  │ float. 6 features intra-época + `ĝ`. Precisa das amostras brutas.      │
  │ Tolerância: DERIVADA, não zero — g++ do host e xtensa não batem bit a  │
  │ bit. Ver o bloco de tolerâncias abaixo.                                │
  └────────────────────────────────────────────────────────────────────────┘
  ┌─ FRONTEIRA B — servidor · `vetor_dourado_sequencias.json` ─────────────┐
  │ `inclinacao_rel` e `d_angulo` a partir da sequência de `ĝ` guardada.   │
  │ **Python dos dois lados** (o backend chama `features_inter_epoca`),    │
  │ então aqui a tolerância é praticamente zero — 1e-12. O que se testa    │
  │ não é aritmética, é se a derivação continua sendo a mesma FUNÇÃO.      │
  │ Não precisa de amostra bruta: cabe em 8 KB.                            │
  └────────────────────────────────────────────────────────────────────────┘

Antes do `DATA-07c` os 5 casos eram todos de época única, então
`inclinacao_rel` e `d_angulo` valiam 0 em todos os cinco: **as duas features de
definição mais delicada não tinham referência nenhuma**, e o instrumento que
devia pegar a divergência era cego exatamente ali. A fronteira B existe para
fechar isso.

⚠️ Enquanto o firmware não consumir o JSON da fronteira A, a paridade está
garantida só de um lado. O item fica registrado no `DATA-07b`.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

import numpy as np
import pytest

from dourado_casos import (
    N_AMOSTRAS_CURTAS, N_AMOSTRAS_EPOCA, SEEDS_DISPOSITIVO, SEQUENCIAS,
    epoca_sintetica, montar_sequencia,
)
from src.features import (
    CORTE_GRAVIDADE_HZ, FEATURES_DEPENDENTES_DO_FILTRO, FEATURES_DO_DISPOSITIVO,
    LIMIAR_P_FRAC_G, NOMES_FEATURES, _angulo_entre, direcao_referencia,
    features_de_epoca, features_inter_epoca, unitario,
)

RAIZ = Path(__file__).resolve().parents[1]
CAMINHO_DOURADO = RAIZ / "testes" / "vetor_dourado.json"
CAMINHO_SEQUENCIAS = RAIZ / "testes" / "vetor_dourado_sequencias.json"

#: Regravar os dourados em vez de conferir contra eles. Ver
#: `test_dourado_do_dispositivo_confere_com_o_arquivo` para o porquê de isto
#: NÃO ser o padrão.
REGRAVAR = os.environ.get("DORMIO_REGRAVAR_DOURADO", "").strip() == "1"


# =========================================================================
# AS TOLERÂNCIAS, E DE ONDE CADA UMA SAIU
# =========================================================================
# Nenhuma delas é um número redondo escolhido no olho. Cada uma foi posta entre
# dois limites medidos, e `test_as_tolerancias_ainda_cercam_o_piso` re-mede os
# limites a cada execução — se o piso subir, o teste cai, em vez de a
# tolerância virar mentira em silêncio.
#
#   PISO   = a menor divergência que duas implementações CORRETAS ainda terão.
#            Apertar abaixo dele reprova firmware correto.
#   TETO   = a menor divergência que mudaria alguma decisão a jusante.
#            Afrouxar acima dele deixa passar divergência que importa.
#
# ⚠️ Uma distinção que custa caro se for ignorada: **ruído do sensor não é
# régua de paridade**. As duas implementações recebem as MESMAS amostras, então
# o ruído é modo-comum e se cancela — ele não contribui para o piso. O ruído é
# régua do TETO: ele diz a partir de que tamanho uma diferença deixa de ser
# distinguível de jitter e passa a ser fórmula diferente.
#
# -------------------------------------------------------------------------
# ENMO (média, desvio, máximo) — tolerância ABSOLUTA, em g
# -------------------------------------------------------------------------
# Piso: em float64 as duas fórmulas batem em 1,5e-15 relativo (é arredondamento
# puro). Mas o ESP32 calcula em float32, e o ENMO faz `‖a‖ − 1` com ‖a‖ ≈ 1 —
# **cancelamento catastrófico**: o float32 tem ~1,2e-7 g de resolução em 1 g, e
# é essa resolução, não a do resultado, que limita. Medido em 60 sementes com
# a fórmula em float32: até 3,5e-6 RELATIVO em `enmo_max`, que em absoluto é
# ~1,0e-7 g — exatamente 1 ULP de float32 em 1 g, como a análise prevê.
# (Trocar o acumulador para double NÃO resolve: medido, 1,101e-6 vs 1,097e-6.
# O erro entra no `sqrt` por amostra, não na soma. Quem quiser apertar isto
# precisa de `‖a‖` em double, não de somatório em double.)
# Teto: o piso de ruído do ENMO no MPU6050 é 0,64 mg = 6,4e-4 g
# (ML-DATASETS §2.2, repetido em scripts/estudo_buffer.py). 1e-7 g está
# **6 400× abaixo** dele: uma divergência desse tamanho não é observável no
# sensor que o projeto usa.
TOL_ENMO_ABS_G = 1e-7

# -------------------------------------------------------------------------
# `zcr` — contagem inteira, sem tolerância
# -------------------------------------------------------------------------
# É uma contagem de trocas de sinal dividida por (n−1). Não passa pelo filtro e
# não tem aritmética que possa divergir: ou as duas contam o mesmo, ou uma das
# duas está errada. Medido: 0,000e+00 em 60 sementes.
TOL_ZCR_ABS = 0.0

# -------------------------------------------------------------------------
# `mag_din_media` — tolerância RELATIVA
# -------------------------------------------------------------------------
# Piso: aqui o filtro difere de verdade. O `filtfilt` do scipy faz
# preenchimento por reflexão ímpar nas bordas; o firmware roda um biquad causal
# nos dois sentidos, inicializado em regime permanente. Não é o mesmo estimador
# nas bordas. Medido em 60 sementes: até 1,00e-2 relativo (1,0 %).
# Medido em 200 sementes: p95 = 0,99 %, **máximo 1,43 %**.
# Teto: o ruído do sensor contribui com ~2,6 mg para ‖a − ĝ‖ (σ=1,6 mg/eixo,
# E‖n‖ ≈ 1,6·1,60 mg), sobre valores típicos de ~24 mg — ou seja ~10 % do valor
# da feature já é ruído.
# 4 % = 2,8× o piso medido, 2,5× abaixo do teto de ruído. A janela é estreita, e
# é estreita porque o filtro é o ponto fraco desta feature — o que está certo:
# é ali que se quer sensibilidade.
TOL_MAG_DIN_REL = 0.04

# -------------------------------------------------------------------------
# `p_frac` — tolerância ABSOLUTA em número de amostras
# -------------------------------------------------------------------------
# Não é quantidade contínua: é fração de amostras acima de um limiar RÍGIDO. O
# resíduo de borda do filtro pode empurrar uma amostra que caiu em cima do
# limiar para o outro lado, o que muda a contagem em ±1 — não o valor. Por isso
# a régua é em amostras, e não percentual: percentual falha justamente quando
# `p_frac` é pequeno (noite parada), que é o caso normal.
TOL_P_FRAC_AMOSTRAS = 2.5

# -------------------------------------------------------------------------
# `ĝ` e os ângulos — tolerância ANGULAR, em graus
# -------------------------------------------------------------------------
# Piso, decomposto (medido):
#     float32 vs float64, fórmula idêntica ......... 1,20e-4 grau  (desprezível)
#     filtfilt reflexivo vs causal ida-e-volta ..... domina, e é sensível à
#         AMPLITUDE de movimento da época: 0,008 grau com amplitude 0,005 g,
#         0,093 grau com amplitude 0,08 g (o topo da faixa da geradora).
#     200 sementes: p50 0,017 · p95 0,054 · **máx 0,082** grau.
#   → piso de projeto ≈ 0,10 grau, e é o FILTRO que manda, não o float.
#
# ⚠️ **A primeira estimativa deste número estava errada, e o teste a pegou.**
# Medido em 5 sementes o piso parecia 0,018 grau, e a tolerância foi fixada em
# 0,05. Com 30 sementes o piso apareceu em 0,063 e reprovou a própria
# tolerância. É para isso que `test_as_tolerancias_ainda_cercam_o_piso` existe:
# um piso medido de menos vira tolerância apertada demais, que reprova firmware
# correto — o custo simétrico de afrouxar.
#
# Teto: a menor distinção que o estudo do buffer faz é a fronteira de 1 grau
# (faixa [0,1) = "sem virada", n=73 386 de 87 795 épocas). Abaixo dela, nenhuma
# decisão a jusante muda.
#
# Escolhido 0,25 grau: 2,7× acima do piso medido, 4× abaixo da menor decisão.
#
# 📌 Uma confusão que vale registrar porque quase entrou aqui: o `‖g‖ = 1 ± 1e−3`
# do contrato (§2.6) **não é um orçamento de paridade**. É uma checagem de
# coerência de UM lado — "este vetor é mesmo unitário?" —, que os dois lados
# satisfazem sozinhos porque os dois normalizam. Ela não diz nada sobre quanto
# as duas implementações podem discordar em DIREÇÃO, que é o que se mede aqui.
TOL_ANGULO_GRAUS = 0.25

#: Por componente de `ĝ`. Derivado do ângulo, não independente:
#: sin(0,25°) ≈ 4,4e−3, arredondado para cima.
TOL_G_COMPONENTE = 5e-3

#: A checagem de coerência do contrato §2.6, que cada lado satisfaz por si só.
#: Separada da tolerância de paridade de propósito — ver a nota acima.
TOL_NORMA_G = 1e-3

# -------------------------------------------------------------------------
# FRONTEIRA B — servidor
# -------------------------------------------------------------------------
#: Python dos dois lados: mesma linguagem, mesma libm, mesmo float64. Não há
#: fonte de divergência legítima. Qualquer coisa acima disto é mudança de
#: fórmula, e é para pegar mudança de fórmula que este dourado existe.
TOL_SERVIDOR_EXATO = 1e-12

#: A exceção: quando `ĝ` chega quantizado em int16 (o layout de 40 B do
#: firmware). Medido: a quantização move `inclinacao_rel` em até 1,1e-3 grau e
#: `d_angulo` em até 2,0e-3 grau. 0,01 grau dá 5× de folga e continua 100×
#: abaixo da fronteira de decisão de 1 grau.
TOL_SERVIDOR_QUANTIZADO_GRAUS = 0.01

#: Piso de ruído do ENMO no MPU6050, em g — a âncora do teto acima.
PISO_RUIDO_ENMO_G = 0.00064

#: A paridade é declarada **só para épocas completas**. Ver
#: `test_epoca_incompleta_nao_tem_paridade`, que mede o estrago.
N_AMOSTRAS_MINIMO_PARIDADE = N_AMOSTRAS_EPOCA


# --------------------------------------------------------------------------
# Referência "estilo firmware": laços escalares, sem numpy. É esta a fórmula
# que o C++ deve implementar, linha por linha.
# --------------------------------------------------------------------------
def _biquad_butter2(fs: float, corte_hz: float) -> tuple[float, float, float, float, float]:
    """Coeficientes de um Butterworth passa-baixa de ordem 2, forma direta.

    São EXATAMENTE os que `scipy.signal.butter(2, corte/(fs/2), "low")` produz:
    prewarp por tangente + transformada bilinear, com Q = 1/√2 (Butterworth).
    Escrever a forma fechada aqui é de propósito — é o que o C++ implementa, sem
    depender de biblioteca de DSP no ESP32.
    """
    k = math.tan(math.pi * corte_hz / fs)
    q = math.sqrt(2.0)
    norma = 1.0 / (1.0 + q * k + k * k)
    b0 = k * k * norma
    b1 = 2.0 * b0
    b2 = b0
    a1 = 2.0 * (k * k - 1.0) * norma
    a2 = (1.0 - q * k + k * k) * norma
    return b0, b1, b2, a1, a2


def _passa_baixa_butter2(x: list[float], fs: float, corte_hz: float) -> list[float]:
    """Butterworth de ordem 2 aplicado ida e volta — fase zero, como o filtfilt.

    Duas passagens de um biquad de ordem 2 equivalem, em magnitude, à ordem 4
    de fase zero da referência em Python, que é `butter(2, ...)` + `filtfilt`
    (o filtfilt já dobra a ordem efetiva). Cabe num ESP32: 5 multiplicações e
    4 somas por amostra, duas vezes.

    Cada passagem inicializa o estado no regime permanente da primeira amostra.
    Sem isso o filtro "liga" do zero e cria um transiente de meio segundo bem
    onde a época começa. ⚠️ Ainda não é idêntico ao `filtfilt` do scipy, que
    faz preenchimento por reflexão ímpar nas bordas — daí a tolerância
    declarada para as features que dependem deste filtro.
    """
    b0, b1, b2, a1, a2 = _biquad_butter2(fs, corte_hz)

    def _passagem(v: list[float]) -> list[float]:
        # regime permanente: para entrada constante v[0], a saída é v[0]
        x1 = x2 = v[0]
        y1 = y2 = v[0]
        saida = [0.0] * len(v)
        for i, amostra in enumerate(v):
            y = b0 * amostra + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
            x2, x1 = x1, amostra
            y2, y1 = y1, y
            saida[i] = y
        return saida

    ida = _passagem(x)
    volta = _passagem(ida[::-1])
    return volta[::-1]


def features_estilo_firmware(a: np.ndarray, fs: float) -> dict[str, float]:
    """As 6 features intra-época **e `ĝ`**, em laços escalares. `a` em g, (n, 3).

    É esta a especificação que o C++ implementa. Nada de numpy, nada de
    vetorização: só o que roda num ESP32 em ponto flutuante simples.

    `ĝ` entrou aqui no `DATA-07c`. Antes o dourado não fixava o vetor de
    gravidade, e a v2.5.0 fez dele **o dado transportado** de que as duas
    features do servidor dependem inteiramente. Um firmware que emitisse `ĝ`
    não-unitário, ou normalizado antes de promediar em vez de depois, passava
    em tudo o que existia.
    """
    n = a.shape[0]
    ax = [float(v) for v in a[:, 0]]
    ay = [float(v) for v in a[:, 1]]
    az = [float(v) for v in a[:, 2]]

    gx = _passa_baixa_butter2(ax, fs, CORTE_GRAVIDADE_HZ)
    gy = _passa_baixa_butter2(ay, fs, CORTE_GRAVIDADE_HZ)
    gz = _passa_baixa_butter2(az, fs, CORTE_GRAVIDADE_HZ)

    soma = soma2 = maximo = 0.0
    soma_mag_din = 0.0
    acima = 0
    mags: list[float] = []
    for i in range(n):
        mag = math.sqrt(ax[i] ** 2 + ay[i] ** 2 + az[i] ** 2)
        mags.append(mag)
        e = mag - 1.0
        if e < 0.0:
            e = 0.0                       # o retificador do ENMO
        soma += e
        soma2 += e * e
        if e > maximo:
            maximo = e
        dx, dy, dz = ax[i] - gx[i], ay[i] - gy[i], az[i] - gz[i]
        mag_din = math.sqrt(dx * dx + dy * dy + dz * dz)
        soma_mag_din += mag_din           # norma L2: invariante a rotação
        if mag_din > LIMIAR_P_FRAC_G:
            acima += 1

    media = soma / n
    var = soma2 / n - media * media
    desvio = math.sqrt(var) if var > 0.0 else 0.0

    m_media = sum(mags) / n
    cruz = 0
    for i in range(1, n):
        if (mags[i - 1] - m_media < 0.0) != (mags[i] - m_media < 0.0):
            cruz += 1

    # ĝ: média da gravidade filtrada NA ÉPOCA, normalizada DEPOIS.
    # A ordem importa. Normalizar cada amostra antes de promediar dá outro
    # estimador (média de direções, não direção da média) — ver o sabotador
    # `ordem_normaliza_antes` em verificar_vetor_dourado_por_mutacao.py.
    gmx, gmy, gmz = sum(gx) / n, sum(gy) / n, sum(gz) / n
    norma = math.sqrt(gmx * gmx + gmy * gmy + gmz * gmz)
    if norma < 1e-12:
        norma = 1.0

    return {
        "enmo_media": media,
        "enmo_desvio": desvio,
        "enmo_max": maximo,
        "mag_din_media": soma_mag_din / n,
        "zcr": cruz / (n - 1),
        "p_frac": acima / n,
        "g": [gmx / norma, gmy / norma, gmz / norma],
    }


def _epoca_sintetica(seed: int, fs: float = 32.0, dur_s: float = 30.0) -> np.ndarray:
    """Alias histórico. A geradora mora em `dourado_casos.py` desde o DATA-07c."""
    return epoca_sintetica(seed, fs, dur_s)


# =========================================================================
# FRONTEIRA A — dispositivo: Python ↔ C++
# =========================================================================
@pytest.mark.parametrize("seed", SEEDS_DISPOSITIVO)
def test_paridade_python_firmware(seed):
    """As 6 features intra-época batem entre as duas implementações."""
    fs = 32.0
    a = _epoca_sintetica(seed, fs)
    X, _ = features_de_epoca(a[None, :, :], fs=fs)
    ref = features_estilo_firmware(a, fs)
    n_amostras = a.shape[0]

    # Features que NÃO passam pelo filtro de gravidade. A tolerância é o ULP de
    # float32 em 1 g, onde o ENMO faz a subtração que cancela — não é "exato",
    # é o limite do float do alvo. Ver o bloco de tolerâncias.
    for nome in ("enmo_media", "enmo_desvio", "enmo_max"):
        i = NOMES_FEATURES.index(nome)
        assert X[0, i] == pytest.approx(ref[nome], abs=TOL_ENMO_ABS_G, rel=0), (
            f"{nome} divergiu além de 1 ULP de float32 em 1 g "
            f"({TOL_ENMO_ABS_G:.1e} g) e NÃO depende do filtro — é bug: "
            f"Python {X[0, i]!r} vs firmware {ref[nome]!r}"
        )

    # `zcr` é contagem inteira: não há aritmética que justifique divergir.
    i = NOMES_FEATURES.index("zcr")
    assert X[0, i] == pytest.approx(ref["zcr"], abs=TOL_ZCR_ABS, rel=0), (
        f"zcr divergiu — é uma CONTAGEM, não tem tolerância possível: "
        f"Python {X[0, i]!r} vs firmware {ref['zcr']!r}"
    )

    # Features que dependem da gravidade estimada. O firmware usa o mesmo
    # Butterworth de ordem 2 ida-e-volta, mas o `filtfilt` do scipy ainda faz
    # preenchimento por reflexão ímpar nas bordas, que o firmware não faz.
    for nome in sorted(FEATURES_DEPENDENTES_DO_FILTRO):
        i = NOMES_FEATURES.index(nome)
        if nome == "p_frac":
            tol_abs = TOL_P_FRAC_AMOSTRAS / n_amostras
            assert X[0, i] == pytest.approx(ref[nome], abs=tol_abs, rel=0), (
                f"p_frac divergiu além de ±2 amostras (de {n_amostras}, "
                f"tolerância de resíduo de borda do filtro): "
                f"Python {X[0, i]!r} vs firmware {ref[nome]!r}. "
                f"Verifique se o biquad do firmware ainda é butter(2, "
                f"{CORTE_GRAVIDADE_HZ} Hz) aplicado nos dois sentidos."
            )
        else:
            assert X[0, i] == pytest.approx(ref[nome], rel=TOL_MAG_DIN_REL, abs=0), (
                f"{nome} divergiu além do resíduo de borda esperado "
                f"({TOL_MAG_DIN_REL:.0%} = 3× o piso medido): "
                f"Python {X[0, i]!r} vs firmware {ref[nome]!r}. "
                f"Verifique se o biquad do firmware ainda é butter(2, "
                f"{CORTE_GRAVIDADE_HZ} Hz) aplicado nos dois sentidos."
            )


@pytest.mark.parametrize("seed", SEEDS_DISPOSITIVO)
def test_paridade_do_vetor_gravidade(seed):
    """`ĝ` bate entre as duas implementações — a fronteira que a v2.5.0 criou.

    Desde que o contrato passou a transportar `ĝ` em vez dos dois ângulos, este
    vetor é o **único** insumo das features do servidor. Um erro aqui não
    aparece em nenhuma das 6 features transmitidas e corrompe as 2 derivadas.
    """
    fs = 32.0
    a = _epoca_sintetica(seed, fs)
    _, g_media = features_de_epoca(a[None, :, :], fs=fs)
    u_py = unitario(g_media[0])
    u_fw = np.asarray(features_estilo_firmware(a, fs)["g"], dtype=float)

    assert np.linalg.norm(u_fw) == pytest.approx(1.0, abs=TOL_NORMA_G), (
        f"ĝ do firmware não é unitário: ‖g‖ = {np.linalg.norm(u_fw)!r}. "
        f"O contrato §2.6 exige 1 ± 1e-3 e o layout de 40 B satura fora disso."
    )
    assert np.allclose(u_py, u_fw, atol=TOL_G_COMPONENTE, rtol=0), (
        f"ĝ divergiu por componente além de {TOL_G_COMPONENTE:.0e} "
        f"(= sin da tolerância angular de {TOL_ANGULO_GRAUS}°): "
        f"Python {u_py!r} vs firmware {u_fw!r}"
    )
    ang = float(np.degrees(np.arccos(np.clip(float(np.dot(u_py, u_fw)), -1.0, 1.0))))
    assert ang <= TOL_ANGULO_GRAUS, (
        f"ĝ divergiu {ang:.4f} grau, acima de {TOL_ANGULO_GRAUS} — o piso "
        f"medido do resíduo de borda é 0,082 grau no pior caso, então isto "
        f"não é borda: é o filtro do firmware fora de sincronia."
    )


def test_epoca_incompleta_nao_tem_paridade():
    """A borda que o dourado **precisa** declarar: época curta não tem paridade.

    `estimar_gravidade` tem um ramo degenerado — se a janela é curta demais
    para filtrar (n ≤ 9), ela devolve a média em vez de filtrar. A referência
    estilo-firmware **não tem esse ramo**: ela filtra sempre. São dois
    estimadores diferentes, e a divergência não é resíduo de borda, é de 30 a
    54 %.

    Mesmo passando do ramo, o filtro ainda não assentou: n=64 diverge 3 %,
    n=300 diverge 0,8 %, e só na época completa cai para 0,26 %.

    **Consequência de contrato, e é o resultado útil deste teste:** o
    dispositivo não pode emitir `f` de uma época incompleta. Ou ele descarta a
    época truncada, ou o campo precisa carregar a contagem de amostras para o
    servidor descartar. Enquanto isso não estiver decidido no `DATA-07b`, este
    teste fixa o tamanho do problema para que ninguém o descubra em campo.
    """
    fs = 32.0
    divergencias = {}
    for n in N_AMOSTRAS_CURTAS:
        a = _epoca_sintetica(1, fs)[:n]
        X, _ = features_de_epoca(a[None, :, :], fs=fs)
        ref = features_estilo_firmware(a, fs)
        i = NOMES_FEATURES.index("mag_din_media")
        divergencias[n] = abs(X[0, i] - ref["mag_din_media"]) / max(X[0, i], 1e-12)

    for n in (8, 10):
        assert divergencias[n] > TOL_MAG_DIN_REL, (
            f"época de {n} amostras passou a caber na tolerância de paridade "
            f"({divergencias[n]:.1%}). Se `estimar_gravidade` perdeu o ramo "
            f"degenerado, ou a referência ganhou um, revise a decisão de "
            f"descartar época incompleta — ela pode ter deixado de ser necessária."
        )
    # E a divergência tem de ENCOLHER conforme a época se aproxima do tamanho
    # completo — se não encolhesse, o problema não seria o assentamento do
    # filtro e o diagnóstico acima estaria errado.
    ordenadas = [divergencias[n] for n in sorted(N_AMOSTRAS_CURTAS)]
    assert ordenadas == sorted(ordenadas, reverse=True), (
        f"a divergência deixou de cair com o tamanho da época: {divergencias}. "
        f"A explicação 'o filtro ainda não assentou' não se sustenta mais."
    )
    # A época completa, essa sim, cabe.
    a = _epoca_sintetica(1, fs)
    X, _ = features_de_epoca(a[None, :, :], fs=fs)
    ref = features_estilo_firmware(a, fs)
    i = NOMES_FEATURES.index("mag_din_media")
    assert abs(X[0, i] - ref["mag_din_media"]) / X[0, i] < TOL_MAG_DIN_REL


# =========================================================================
# FRONTEIRA B — servidor: derivar os dois ângulos do `ĝ` guardado
# =========================================================================
@pytest.mark.parametrize("nome", sorted(SEQUENCIAS))
def test_derivacao_servidor_bate_com_o_pipeline(nome):
    """O servidor, partindo só de `ĝ`, reproduz o que o pipeline calculou.

    É a prova de que transportar `ĝ` em vez dos dois ângulos não perde nada —
    e agora sobre sequências com virada, deriva e retorno, em vez de sobre
    épocas únicas onde as duas features valiam 0.
    """
    epocas, _ = montar_sequencia(nome)
    X, g_media = features_de_epoca(epocas, fs=32.0)
    inc, dang = features_inter_epoca(g_media)

    i_inc = NOMES_FEATURES.index("inclinacao_rel")
    i_dang = NOMES_FEATURES.index("d_angulo")
    assert np.allclose(inc, X[:, i_inc], atol=TOL_SERVIDOR_EXATO, rtol=0), (
        f"[{nome}] inclinacao_rel do servidor divergiu do pipeline"
    )
    assert np.allclose(dang, X[:, i_dang], atol=TOL_SERVIDOR_EXATO, rtol=0), (
        f"[{nome}] d_angulo do servidor divergiu do pipeline"
    )


def test_derivacao_servidor_sobrevive_a_quantizacao_int16():
    """`ĝ` chega ao servidor depois de passar pelo int16 do buffer de 40 B.

    O dourado guarda `ĝ` em float64, mas em campo ele atravessa a quantização
    do layout do firmware. Se a derivação fosse sensível a isso, o dourado
    estaria fixando um número que a produção nunca vai reproduzir.
    """
    passo = 2.0 / 65535
    for nome in sorted(SEQUENCIAS):
        epocas, _ = montar_sequencia(nome)
        _, g_media = features_de_epoca(epocas, fs=32.0)
        u = unitario(g_media)
        inc0, d0 = features_inter_epoca(u)
        inc1, d1 = features_inter_epoca(unitario(np.round(u / passo) * passo))

        assert np.abs(inc1 - inc0).max() <= TOL_SERVIDOR_QUANTIZADO_GRAUS, (
            f"[{nome}] quantizar ĝ em int16 moveu inclinacao_rel em "
            f"{np.abs(inc1 - inc0).max():.5f} grau"
        )
        assert np.abs(d1 - d0).max() <= TOL_SERVIDOR_QUANTIZADO_GRAUS, (
            f"[{nome}] quantizar ĝ em int16 moveu d_angulo em "
            f"{np.abs(d1 - d0).max():.5f} grau"
        )


def test_primeira_epoca_tem_d_angulo_zero_por_definicao():
    """`d_angulo[0] = 0` significa INDEFINIDO, não 'ficou parado'.

    A distinção importa porque as duas coisas viram o mesmo número no vetor de
    features, e um modelo que veja muitas primeiras-épocas aprende que o início
    da noite é sempre imóvel. Está registrado aqui para que a decisão de como
    tratar isso (máscara? descartar a primeira época?) seja tomada de propósito
    no `DATA-07b`, e não por omissão.
    """
    for nome in sorted(SEQUENCIAS):
        epocas, _ = montar_sequencia(nome)
        _, g_media = features_de_epoca(epocas, fs=32.0)
        _, dang = features_inter_epoca(g_media)
        assert dang[0] == 0.0, f"[{nome}] d_angulo[0] deixou de ser 0"


def test_angulo_entre_vetores_paralelos_nao_e_nan():
    """O `clip` do produto interno não é decoração — é o que evita NaN.

    `arccos` exige argumento em [−1, 1], e o produto interno de dois unitários
    dá 1 + 1 ulp com facilidade. Sem o `clip`, `inclinacao_rel` de uma época
    cujo `ĝ` coincide com `ĝ_ref` vira NaN — e NaN atravessa o pipeline até o
    modelo, onde aparece como erro de treino, longe da causa.

    📌 **Este teste nasceu de uma falha do verificador por mutação.** O
    sabotador `clip_removido` era detectado só pela comparação byte a byte do
    dourado do dispositivo, por acidente: nas sequências o produto interno
    nunca chega a passar de 1, e o caso `uma_epoca` cai exatamente em 1,0 por
    sorte de arredondamento. Medido: só o caso de época única do dispositivo
    produz 1,0000000000000002. Depender de sorte de float para pegar um NaN não
    é cobertura — então aqui a condição é exercitada de propósito.
    """
    # Em lote, e não com um vetor escolhido a dedo: ~19 % dos unitários
    # aleatórios têm produto interno consigo mesmo acima de 1,0 em float64,
    # então 2 000 deles cobrem a condição sem depender de constante mágica.
    # (Um exemplo fixo chegou a ser tentado aqui e não sobreviveu: re-normalizar
    # um vetor já unitário muda o último bit, e `np.dot` soma em ordem
    # diferente de `np.sum(u*v, axis=-1)`, que é o que `_angulo_entre` usa. O
    # lote não tem esse problema.)
    rng = np.random.default_rng(4242)
    u = unitario(rng.normal(size=(2000, 3)))
    estouram = np.sum(u * u, axis=-1) > 1.0
    assert np.count_nonzero(estouram) > 0, (
        "nenhum dos 2 000 unitários estourou 1,0 — a condição não foi exercitada"
    )
    v = u[int(np.argmax(np.sum(u * u, axis=-1)))]
    assert np.all(np.isfinite(_angulo_entre(u, u))), "paralelos viraram NaN"
    assert np.all(np.isfinite(_angulo_entre(u, -u))), "antiparalelos viraram NaN"
    # ⚠️ A tolerância aqui é 1e-5 grau, e não zero, por um motivo que vale
    # registrar: `arccos` é MAL CONDICIONADO perto de ±1. A derivada
    # dθ/dc = −1/√(1−c²) explode, e 1 ulp de erro em c (2,2e−16) vira
    # 2,2e−16/√(2·2,2e−16) ≈ 1,1e−8 rad ≈ 6e−7 grau no ângulo. Medido: 8,5e−7.
    # Ou seja: dois ĝ idênticos podem dar 0,00000085° em vez de 0°, e nenhuma
    # implementação — Python, C++ ou backend — pode fazer melhor com esta
    # fórmula. É o piso absoluto de qualquer feature angular deste projeto.
    assert np.allclose(_angulo_entre(u, u), 0.0, atol=1e-5)
    assert np.allclose(_angulo_entre(u, -u), 180.0, atol=1e-5)

    # E pela porta da frente, na função que o servidor chama.
    par = np.stack([v, v])
    inc, dang = features_inter_epoca(par)
    assert np.all(np.isfinite(inc)) and np.all(np.isfinite(dang)), (
        f"features_inter_epoca devolveu NaN para ĝ repetido: {inc!r} {dang!r}"
    )
    assert dang[1] == pytest.approx(0.0, abs=1e-5)

    anti = np.stack([v, -v])
    inc2, dang2 = features_inter_epoca(anti)
    assert np.all(np.isfinite(inc2)) and np.all(np.isfinite(dang2))
    assert dang2[1] == pytest.approx(180.0, abs=1e-5)


def test_uma_epoca_zera_as_duas_features():
    """O degenerado: com n=1 não há referência nem vizinho."""
    epocas, _ = montar_sequencia("uma_epoca")
    X, _ = features_de_epoca(epocas, fs=32.0)
    assert X[0, NOMES_FEATURES.index("inclinacao_rel")] == pytest.approx(0.0, abs=1e-9)
    assert X[0, NOMES_FEATURES.index("d_angulo")] == 0.0


def test_deriva_lenta_separa_as_duas_features():
    """O caso que uma implementação confusa NÃO passa.

    Deriva de 0,8°/época: `d_angulo` fica abaixo de 1 grau em toda a sequência,
    mas `inclinacao_rel` acumula até mais de 5 graus. Quem trocasse uma pela
    outra, ou derivasse `d_angulo` de `inclinacao_rel`, passaria em
    `virada_brusca` e cairia aqui.
    """
    epocas, _ = montar_sequencia("deriva_lenta")
    X, _ = features_de_epoca(epocas, fs=32.0)
    inc = X[:, NOMES_FEATURES.index("inclinacao_rel")]
    dang = X[:, NOMES_FEATURES.index("d_angulo")]

    assert dang[1:].max() < 1.0, (
        f"a deriva deixou de ser sub-grau (máx {dang[1:].max():.2f}) — "
        f"o caso perdeu o propósito de separar as duas features"
    )
    assert inc.max() > 5.0, (
        f"inclinacao_rel só chegou a {inc.max():.2f} grau; o caso precisa de um "
        f"deslocamento acumulado grande para contrastar com o d_angulo pequeno"
    )
    assert inc.max() > 4 * dang[1:].max(), (
        "a separação entre as duas features encolheu"
    )


def test_retorno_a_mesma_orientacao_devolve_a_mesma_inclinacao():
    """Voltar à postura inicial devolve `inclinacao_rel` ao valor inicial — exato.

    As épocas 10..14 são bit a bit iguais às 0..4 (mesmas sementes, mesma
    direção), então não há margem: ou o número volta igual, ou `ĝ_ref` está
    derivando com o tempo. É o teste que pega o acumulador incremental que o
    contrato §2.6 proíbe — aquele que "aproximaria" a mediana geométrica e
    divergiria em silêncio.
    """
    epocas, meta = montar_sequencia("retorno_a_mesma_orientacao")
    X, _ = features_de_epoca(epocas, fs=32.0)
    inc = X[:, NOMES_FEATURES.index("inclinacao_rel")]
    dang = X[:, NOMES_FEATURES.index("d_angulo")]

    for i, j in meta["indices_identicos"]:
        assert inc[i] == pytest.approx(inc[j], abs=TOL_SERVIDOR_EXATO), (
            f"épocas {i} e {j} têm ĝ idêntico mas inclinacao_rel diferente "
            f"({inc[i]!r} vs {inc[j]!r}) — ĝ_ref está dependendo da POSIÇÃO na "
            f"sequência, não do conjunto. Ver contrato §2.6."
        )
    # E as duas viradas aparecem em d_angulo, sem virar uma só.
    picos = int(np.count_nonzero(dang > 30.0))
    assert picos == 2, f"esperadas 2 viradas de ~70 graus, vistas {picos}"


def test_faixa_de_viradas_cobre_as_faixas_do_estudo_do_buffer():
    """As faixas de `d_angulo` que o `estudo_buffer.py` isolou têm representante.

    O estudo mostrou que o erro da alternativa barata cresce monotonicamente
    com o tamanho da virada — 0,03 grau em [0,1), 3,70 em [5,20), 31,10 em
    [60,180). Um dourado que só tivesse épocas paradas mediria a região onde
    qualquer implementação acerta.
    """
    epocas, _ = montar_sequencia("faixa_de_viradas")
    X, _ = features_de_epoca(epocas, fs=32.0)
    dang = X[1:, NOMES_FEATURES.index("d_angulo")]

    faixas = [(0.0, 1.0), (1.0, 5.0), (5.0, 20.0), (20.0, 60.0), (60.0, 180.0)]
    for lo, hi in faixas:
        assert np.any((dang >= lo) & (dang < hi)), (
            f"nenhuma época com d_angulo em [{lo}, {hi}) — a faixa do estudo "
            f"do buffer ficou sem cobertura. Valores: {np.round(dang, 2).tolist()}"
        )


def test_lacuna_entre_epocas_e_tratada_como_adjacente():
    """⚠️ Documenta um comportamento conhecido, e não o endossa.

    `features_inter_epoca` não conhece tempo: ela compara vizinhos na ordem do
    array. Numa drenagem com buraco de 40 min, o `d_angulo` da época seguinte
    sai como se a virada tivesse ocorrido em 30 s.

    Este teste existe para que, no dia em que o `DATA-07b` resolver carregar
    carimbo por época, a mudança de valor **apareça** em vez de entrar calada.
    Se ele cair porque a lacuna passou a ser tratada, a correção é atualizar o
    dourado — não relaxar o teste.
    """
    epocas, meta = montar_sequencia("lacuna_entre_epocas")
    X, _ = features_de_epoca(epocas, fs=32.0)
    dang = X[:, NOMES_FEATURES.index("d_angulo")]
    i = meta["lacuna_apos_indice"] + 1

    assert dang[i] > 60.0, (
        f"o comportamento mudou: d_angulo através da lacuna agora vale "
        f"{dang[i]:.2f} grau. Se a lacuna passou a ser tratada, atualize o "
        f"dourado e o contrato §2.6; se não, algo quebrou."
    )
    vizinhas = np.delete(dang[1:], i - 1)
    assert vizinhas.max() < 1.0, "as épocas fora da lacuna deixaram de ser paradas"


# =========================================================================
# Os arquivos dourados — CONFERIR, não regravar
# =========================================================================
def _monta_dourado_dispositivo() -> dict:
    fs = 32.0
    casos = []
    for seed in SEEDS_DISPOSITIVO:
        a = epoca_sintetica(seed, fs)
        X, g_media = features_de_epoca(a[None, :, :], fs=fs)
        esperado = {n: float(X[0, i]) for i, n in enumerate(NOMES_FEATURES)}
        esperado["g"] = [float(v) for v in unitario(g_media[0])]
        casos.append({
            "seed": seed,
            "fs_hz": fs,
            "n_amostras": int(a.shape[0]),
            "entrada_g": np.round(a, 9).tolist(),
            "esperado": esperado,
        })
    return {
        "descricao": ("FRONTEIRA A (dispositivo). O teste em C++ do firmware deve ler "
                      "este arquivo e reproduzir 'esperado'. As 6 primeiras features e "
                      "`g` são o que o dispositivo transmite (contrato v2.5.0 §2.6)."),
        "limiar_p_frac_g": LIMIAR_P_FRAC_G,
        "corte_gravidade_hz": CORTE_GRAVIDADE_HZ,
        "ordem_features": list(NOMES_FEATURES),
        "features_do_dispositivo": list(FEATURES_DO_DISPOSITIVO),
        "tolerancias": {
            "enmo_abs_g": TOL_ENMO_ABS_G,
            "zcr_abs": TOL_ZCR_ABS,
            "mag_din_rel": TOL_MAG_DIN_REL,
            "p_frac_abs_amostras": TOL_P_FRAC_AMOSTRAS,
            "g_componente_abs": TOL_G_COMPONENTE,
            "g_angulo_graus": TOL_ANGULO_GRAUS,
            "nota": ("Derivadas, nao escolhidas: cada uma esta entre um PISO medido "
                     "(o que duas implementacoes corretas ainda divergem) e um TETO "
                     "(o que mudaria uma decisao a jusante). A derivacao esta no "
                     "cabecalho de test_vetor_dourado.py e e re-medida por "
                     "test_as_tolerancias_ainda_cercam_o_piso."),
        },
        "n_amostras_minimo_paridade": N_AMOSTRAS_MINIMO_PARIDADE,
        "nota": ("inclinacao_rel e d_angulo sao INTER-epoca e valem 0 aqui, onde cada "
                 "caso tem uma epoca so. A paridade delas NAO e desta fronteira: elas "
                 "sao derivadas no servidor, e o dourado delas e "
                 "vetor_dourado_sequencias.json (DATA-07c)."),
        "casos": casos,
    }


def _monta_dourado_sequencias() -> dict:
    fs = 32.0
    seqs = []
    for nome in SEQUENCIAS:
        epocas, meta = montar_sequencia(nome, fs=fs)
        _, g_media = features_de_epoca(epocas, fs=fs)
        u = unitario(g_media)
        # ⚠️ Calculado a partir de `u` — o valor que o arquivo GUARDA —, e não
        # de `g_media`. Parecem a mesma coisa e não são: normalizar um vetor já
        # unitário muda o último bit (‖u‖ é 1 ± 1 ulp), e `arccos` amplifica
        # isso perto de 0°, onde a derivada −1/√(1−c²) explode. Calculando de
        # `g_media`, o dourado guardava números que não saíam da própria
        # entrada dele, e o round-trip falhava por ~1e−8 grau.
        # Regra geral: o esperado de um dourado é função do que ele GRAVA.
        inc, dang = features_inter_epoca(u)
        seqs.append({
            "nome": nome,
            "fs_hz": fs,
            "n_epocas": int(epocas.shape[0]),
            "n_amostras_por_epoca": int(epocas.shape[1]),
            "meta": {k: v for k, v in meta.items() if k != "sementes"},
            "sementes": meta["sementes"],
            # A ENTRADA da fronteira B é só isto: o ĝ por época, que é o que o
            # dispositivo transmitiu. Nenhuma amostra bruta.
            # ⚠️ Sem arredondar. Arredondar em 12 casas parecia inofensivo e
            # quebrava o round-trip: os ângulos saem de `arccos` de um produto
            # interno, e 1e-12 por componente já move o resultado mais que a
            # tolerância exata de 1e-12 grau. Quem grava o dourado não pode
            # perder precisão que quem confere vai exigir.
            "g_por_epoca": [[float(c) for c in linha] for linha in u],
            "esperado": {
                "g_ref": [float(v) for v in direcao_referencia(u)],
                "inclinacao_rel": [float(v) for v in inc],
                "d_angulo": [float(v) for v in dang],
            },
        })
    return {
        "descricao": ("FRONTEIRA B (servidor). Derivacao de inclinacao_rel e d_angulo a "
                      "partir da sequencia de `g` guardada, sobre a noite inteira. "
                      "Entrada: g_por_epoca. Saida esperada: 'esperado'. Nenhuma amostra "
                      "bruta — as duas features sao funcao SO de `g`."),
        "ordem_features": list(NOMES_FEATURES),
        "features_derivadas_no_servidor": ["inclinacao_rel", "d_angulo"],
        "unidade_dos_angulos": "graus",
        "tolerancias": {
            "exato": TOL_SERVIDOR_EXATO,
            "com_g_quantizado_int16_graus": TOL_SERVIDOR_QUANTIZADO_GRAUS,
            "nota": ("Python dos dois lados: nao ha divergencia de aritmetica legitima. "
                     "A folga maior so vale quando `g` chega quantizado pelo layout de "
                     "40 B do firmware."),
        },
        "nota": ("g_ref e a mediana geometrica (Weiszfeld) de TODAS as epocas da "
                 "sequencia. Um estimador incremental daria outro numero — ver "
                 "DATA-CONTRACT secao 2.6."),
        "sequencias": seqs,
    }


# A REFERÊNCIA FIXA E A PLATAFORMA (ML-WIN-01, 28/10)
#
# Até 28/10 a comparação era `gravado == montado`, exata. O dourado foi gravado
# em Linux (Python 3.10), e no Windows (3.11, mesmas versões pinadas de numpy e
# scipy) 71 de 14 952 floats divergem **no último dígito**: medido, o pior caso
# é 8,0e-13 relativo (`sequencias[4].esperado.g_ref[0]`) e 4,7e-14 absoluto. Não
# é mudança de definição: é a ordem de soma e a libm de cada plataforma. A
# igualdade exata prendia o dourado à máquina que o gravou, e a saída errada —
# regravar no Windows — só trocaria a dependência de lado.
#
# Daí a régua, derivada como as outras deste arquivo, entre um piso e um teto:
#   piso  — 8,0e-13 relativo, a divergência entre plataformas medida;
#   teto  — o que o dourado existe para pegar: as sabotagens do
#           `verificar_vetor_dourado_por_mutacao.py` cujo `exige` é um destes
#           dois testes (`filtro_liga_do_zero`, `g_ref_so_do_comeco`). Têm de
#           continuar caindo, em Linux e no Windows — conferido em 28/10.
# 1e-9 relativo fica três ordens acima do piso. O piso absoluto (1e-15) existe só
# para valores que deveriam ser zero, e fica abaixo do menor valor não nulo do
# arquivo (1e-12). **A estrutura continua exata:** chaves, comprimentos, tipos e
# todo valor que não é float — uma feature a mais ou a menos reprova como antes.
TOL_DOURADO_REL = 1e-9
TOL_DOURADO_ABS = 1e-15


def _divergencias(gravado, montado, caminho="") -> list[str]:
    """Onde `montado` deixa de bater com `gravado`. Vazio quando bate."""
    if isinstance(gravado, float) or isinstance(montado, float):
        if not (isinstance(gravado, (int, float)) and isinstance(montado, (int, float))):
            return [f"{caminho}: tipo {type(gravado).__name__} vs {type(montado).__name__}"]
        if math.isclose(gravado, montado, rel_tol=TOL_DOURADO_REL, abs_tol=TOL_DOURADO_ABS):
            return []
        return [f"{caminho}: {gravado!r} vs {montado!r}"]
    if type(gravado) is not type(montado):
        return [f"{caminho}: tipo {type(gravado).__name__} vs {type(montado).__name__}"]
    if isinstance(gravado, dict):
        if set(gravado) != set(montado):
            return [f"{caminho}: chaves {sorted(set(gravado) ^ set(montado))}"]
        return [d for k in gravado for d in _divergencias(gravado[k], montado[k], f"{caminho}.{k}")]
    if isinstance(gravado, list):
        if len(gravado) != len(montado):
            return [f"{caminho}: comprimento {len(gravado)} vs {len(montado)}"]
        return [d for i, (a, b) in enumerate(zip(gravado, montado))
                for d in _divergencias(a, b, f"{caminho}[{i}]")]
    return [] if gravado == montado else [f"{caminho}: {gravado!r} vs {montado!r}"]


def _confere_ou_regrava(caminho: Path, montado: dict, rotulo: str):
    texto = json.dumps(montado, indent=2)
    if REGRAVAR or not caminho.exists():
        caminho.write_text(texto, encoding="utf-8")
        if REGRAVAR:
            pytest.skip(f"{rotulo} regravado (DORMIO_REGRAVAR_DOURADO=1)")
        return
    gravado = json.loads(caminho.read_text(encoding="utf-8"))
    # `json` ida e volta para comparar o que seria gravado, não o objeto vivo.
    divergencias = _divergencias(gravado, json.loads(texto))
    assert not divergencias, (
        f"o {rotulo} no disco NÃO bate com o que o código produz agora "
        f"({len(divergencias)} valor(es); o primeiro: {divergencias[0]}).\n"
        f"  Se a mudança foi INTENCIONAL, regrave de propósito:\n"
        f"      DORMIO_REGRAVAR_DOURADO=1 pytest testes/test_vetor_dourado.py\n"
        f"      e explique no commit o que mudou de definição.\n"
        f"  Se não foi, você acabou de encontrar uma regressão silenciosa — "
        f"que é exatamente o que este arquivo existe para pegar."
    )


def test_dourado_do_dispositivo_confere_com_o_arquivo():
    """O dourado é uma REFERÊNCIA FIXA, não um retrato do código de hoje.

    📌 Esta função antes gravava o arquivo e conferia que ele existia — ou
    seja, **não podia falhar**. Qualquer mudança na definição de uma feature
    reescrevia o dourado e a suíte seguia verde: o arquivo perseguia o código
    em vez de prendê-lo. Um vetor dourado que se regrava sozinho não é um vetor
    dourado, é um log.

    Agora ele confere. Regravar exige dizer que se quer regravar.
    """
    _confere_ou_regrava(CAMINHO_DOURADO, _monta_dourado_dispositivo(),
                        "vetor dourado do dispositivo")


def test_dourado_das_sequencias_confere_com_o_arquivo():
    """Mesma regra para a fronteira B."""
    _confere_ou_regrava(CAMINHO_SEQUENCIAS, _monta_dourado_sequencias(),
                        "vetor dourado das sequências")


def test_o_arquivo_de_sequencias_basta_para_o_servidor():
    """O JSON da fronteira B tem de ser autossuficiente.

    Quem for implementar a derivação no backend (`DATA-07b`, item (e)) precisa
    conseguir rodar o dourado **sem** o pipeline de ML: lê `g_por_epoca`, aplica
    a própria implementação, compara com `esperado`. Este teste faz esse
    percurso, para garantir que o arquivo não depende de nada que só exista
    aqui dentro.
    """
    if not CAMINHO_SEQUENCIAS.exists():
        pytest.skip("dourado de sequências ainda não gravado")
    dourado = json.loads(CAMINHO_SEQUENCIAS.read_text(encoding="utf-8"))
    assert dourado["sequencias"], "nenhuma sequência no arquivo"

    for seq in dourado["sequencias"]:
        g = np.asarray(seq["g_por_epoca"], dtype=float)
        assert g.shape == (seq["n_epocas"], 3)
        assert np.allclose(np.linalg.norm(g, axis=1), 1.0, atol=1e-9), (
            f"[{seq['nome']}] g_por_epoca não está unitário"
        )
        inc, dang = features_inter_epoca(g)
        assert np.allclose(inc, seq["esperado"]["inclinacao_rel"],
                           atol=TOL_SERVIDOR_EXATO, rtol=0), (
            f"[{seq['nome']}] inclinacao_rel não sai de g_por_epoca"
        )
        assert np.allclose(dang, seq["esperado"]["d_angulo"],
                           atol=TOL_SERVIDOR_EXATO, rtol=0), (
            f"[{seq['nome']}] d_angulo não sai de g_por_epoca"
        )


# =========================================================================
# As tolerâncias são uma afirmação sobre o mundo. Esta suíte a re-mede.
# =========================================================================
def test_as_tolerancias_ainda_cercam_o_piso():
    """Re-mede o PISO e confere que cada tolerância continua acima dele.

    Uma tolerância derivada de uma medição feita uma vez, e depois só
    comentada, envelhece: muda a versão do scipy, muda a geradora, muda o corte
    do filtro, e o comentário continua dizendo 1,0 %. Aqui a derivação é
    executável.

    Se este teste cair, a resposta **não** é afrouxar a constante: é entender
    por que o piso subiu. Piso subindo significa que as duas implementações
    estão se afastando.
    """
    fs = 32.0
    piso_enmo = 0.0
    piso_mag = 0.0
    piso_ang = 0.0
    for seed in range(1, 31):
        a = epoca_sintetica(seed, fs)
        X, g_media = features_de_epoca(a[None, :, :], fs=fs)
        ref = features_estilo_firmware(a, fs)
        for nome in ("enmo_media", "enmo_desvio", "enmo_max"):
            i = NOMES_FEATURES.index(nome)
            piso_enmo = max(piso_enmo, abs(X[0, i] - ref[nome]))
        i = NOMES_FEATURES.index("mag_din_media")
        piso_mag = max(piso_mag, abs(X[0, i] - ref["mag_din_media"]) / X[0, i])
        u_py, u_fw = unitario(g_media[0]), np.asarray(ref["g"], dtype=float)
        piso_ang = max(piso_ang, float(np.degrees(np.arccos(
            np.clip(float(np.dot(u_py, u_fw)), -1.0, 1.0)))))

    assert piso_enmo < TOL_ENMO_ABS_G, (
        f"o piso do ENMO em float64 subiu para {piso_enmo:.3e} g, encostando na "
        f"tolerância de {TOL_ENMO_ABS_G:.0e}. A margem para o float32 do ESP32 sumiu."
    )
    assert piso_mag < TOL_MAG_DIN_REL, (
        f"o resíduo de borda de mag_din_media subiu para {piso_mag:.2%}, contra "
        f"a tolerância de {TOL_MAG_DIN_REL:.0%}"
    )
    assert piso_ang < TOL_ANGULO_GRAUS, (
        f"o piso angular de ĝ subiu para {piso_ang:.4f} grau, contra a "
        f"tolerância de {TOL_ANGULO_GRAUS} grau"
    )
    # E o teto: a tolerância do ENMO tem de ficar MUITO abaixo do ruído do
    # sensor, senão ela deixaria passar divergência observável em campo.
    assert TOL_ENMO_ABS_G < PISO_RUIDO_ENMO_G / 100, (
        f"a tolerância do ENMO ({TOL_ENMO_ABS_G:.0e} g) não está mais com folga "
        f"sob o piso de ruído do MPU6050 ({PISO_RUIDO_ENMO_G:.1e} g)"
    )
    # E a tolerância angular tem de ficar abaixo da menor decisão a jusante,
    # que é a fronteira de 1 grau do estudo do buffer. A folga aqui é de 4×,
    # não de 10×: o piso do resíduo de borda (0,082 grau) não deixa mais. É a
    # tolerância mais apertada das seis contra o seu teto, e é o número a
    # revisar se o filtro do firmware mudar.
    assert TOL_ANGULO_GRAUS <= 1.0 / 4, (
        "a tolerância angular encostou na fronteira de 1 grau do estudo do buffer"
    )


def test_features_invariantes_a_rotacao():
    """A propriedade que justifica a escolha das 8 features.

    Se o sensor inteiro sofre uma rotação fixa, NENHUMA das features pode mudar.
    É a diferença entre medir movimento e medir a orientação de montagem — e
    num travesseiro, onde a orientação é arbitrária e muda durante a noite, é a
    diferença entre uma feature que transfere e uma que não.

    📌 **Este teste já reprovou uma feature de verdade.** A versão anterior de
    `mag_din_media` usava norma L1 (a SMA clássica) e variava ~6% sob rotação.
    Foi trocada por L2, que é invariante por construção. O registro está na
    DECISÃO TÉCNICA 2 de `src/features.py`. Não relaxe a tolerância daqui para
    fazer uma feature passar: se ela não é invariante, ela não serve.
    """
    fs = 32.0
    rng = np.random.default_rng(7)
    a = np.stack([_epoca_sintetica(s, fs) for s in range(1, 9)])

    q, r = np.linalg.qr(rng.normal(size=(3, 3)))
    R = q @ np.diag(np.sign(np.diag(r)))
    if np.linalg.det(R) < 0:
        R[:, 0] *= -1

    X0, _ = features_de_epoca(a, fs=fs)
    X1, _ = features_de_epoca(a @ R.T, fs=fs)

    for i, nome in enumerate(NOMES_FEATURES):
        assert np.allclose(X0[:, i], X1[:, i], atol=1e-8, rtol=1e-5), (
            f"{nome} MUDOU sob rotação do referencial — não é invariante à "
            f"orientação e não pode ser usada (ver DECISÃO TÉCNICA 1)."
        )


@pytest.mark.parametrize("nome", sorted(SEQUENCIAS))
def test_sequencias_tambem_sao_invariantes_a_rotacao(nome):
    """A invariância valia só para épocas únicas. Agora vale para as sequências.

    É aqui que a invariância de `inclinacao_rel` e `d_angulo` deixa de ser
    afirmação de docstring e vira teste: com época única as duas valiam 0, e 0
    é trivialmente invariante.
    """
    epocas, _ = montar_sequencia(nome)
    rng = np.random.default_rng(13)
    q, r = np.linalg.qr(rng.normal(size=(3, 3)))
    R = q @ np.diag(np.sign(np.diag(r)))
    if np.linalg.det(R) < 0:
        R[:, 0] *= -1

    X0, _ = features_de_epoca(epocas, fs=32.0)
    X1, _ = features_de_epoca(epocas @ R.T, fs=32.0)
    for i, f in enumerate(NOMES_FEATURES):
        # As 6 intra-época são invariantes até o arredondamento (~1e-16 medido).
        # `inclinacao_rel` tem um resíduo maior, ~8,5e-7 grau. A causa NÃO é a
        # convergência do Weiszfeld, como parecia à primeira vista: é o
        # condicionamento do `arccos` perto de ±1 (dθ/dc = −1/√(1−c²)), que
        # transforma 1 ulp no produto interno em ~6e−7 grau no ângulo. A conta
        # e a medição estão em `test_angulo_entre_vetores_paralelos_nao_e_nan`,
        # onde dois vetores BIT A BIT IGUAIS dão o mesmo 8,5e−7 — sem Weiszfeld
        # nenhum no caminho. 1e-5 grau dá folga sobre esse piso e continua
        # 100 000× abaixo da fronteira de decisão de 1 grau.
        assert np.allclose(X0[:, i], X1[:, i], atol=1e-5, rtol=1e-5), (
            f"[{nome}] {f} mudou sob rotação do referencial em "
            f"{np.abs(X0[:, i] - X1[:, i]).max():.2e}"
        )
