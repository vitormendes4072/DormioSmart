"""A cadeia C2 do firmware, em Python: da FIFO do MPU6050 à grade de 32 Hz.

O que esta cadeia faz, e por que ela existe
-------------------------------------------
Na arquitetura C2 (`ARQ-01`, decidida em 30/10) o ESP32 dorme em sono leve e
acorda a cada ~1,7 s para esvaziar a FIFO do sensor, que amostra a 50 Hz
**nominais**. Três coisas separam esse fluxo da entrada que o pipeline de ML
espera (960 amostras numa grade de 32 Hz por época de 30 s):

1. **A FIFO não tem carimbo de tempo.** Só se sabe quantas amostras havia em
   cada drenagem e quando a drenagem aconteceu, no relógio do ESP32.
2. **A taxa real não é 50 Hz.** O oscilador interno do MPU6050 tem ±5 % a
   25 °C e −15/+10 % na faixa de temperatura (folha de produto). A taxa é
   MEDIDA, não assumida — o sabotador `taxa_nominal` mostra o que acontece se
   for assumida.
3. **De ~50 Hz para 32 Hz é decimação.** Sem anti-aliasing, o que está entre
   12,8 e 25 Hz dobra para dentro da banda. É a mesma cadeia de
   `src/sinal.py::reamostrar` (Butterworth de 4ª ordem a 12,8 Hz, fase zero,
   na taxa de origem; depois interpolação linear), aplicada por época.

As duas referências deste módulo
--------------------------------
* `esperado_pelo_pipeline` — o que o `ml/` faria com o mesmo sinal, tendo os
  **tempos verdadeiros** e a noite inteira: `reamostrar` no registro todo,
  depois `features_de_epoca` em cada fatia. É a referência de VALIDADE.
* `cadeia_estilo_firmware` — o que o firmware faz, em laços escalares, com o
  que o firmware sabe (drenagens e contagens). É a referência de EXATIDÃO: o
  C++ (`firmware/nucleo/cadeia_c2.cpp`) a copia linha por linha, e onde
  divergir dela é o C++ que está errado.

A distância entre as duas é o PISO da paridade, medido em
`test_dourado_cadeia_c2.py`. O que a domina não é filtro nem float: é **o
instante de cada amostra**, que o firmware estima e o pipeline conhece. Com o
tempo verdadeiro (o "oráculo"), a cadeia por época com 0,5 s de margem bate com
a noite inteira em ~1e-6 g — medido em 30/10 —, então a margem resolve as bordas
e o que sobra é o relógio.
"""

from __future__ import annotations

import math

import numpy as np

# --------------------------------------------------------------------------
# Constantes. Cada uma tem par em C++ (`fifo_mpu.h`, `reamostragem.h`,
# `cadeia_c2.h`), e o teste em C++ confere que os valores do JSON batem com os
# compilados — em vez de assumir.
# --------------------------------------------------------------------------

#: ±8 g no MPU6050 (`setAccelerometerRange(MPU6050_RANGE_8_G)` nos sketches).
LSB_POR_G = 4096.0

#: Taxa nominal da C2: 1 kHz / (1 + SMPLRT_DIV), com SMPLRT_DIV = 19.
TAXA_NOMINAL_HZ = 50.0

#: A grade do pipeline (`ml/config.yaml: taxa_comum_hz`).
TAXA_DA_GRADE_HZ = 32.0

#: 0,8 × Nyquist da grade (`ml/config.yaml: corte_antialiasing_frac_nyquist`).
CORTE_ANTIALIASING_HZ = 0.8 * TAXA_DA_GRADE_HZ / 2.0

DURACAO_EPOCA_S = 30.0
AMOSTRAS_NA_GRADE = int(DURACAO_EPOCA_S * TAXA_DA_GRADE_HZ)  # 960

#: Amostras de cada lado da época que entram no filtro e saem antes da grade.
#: Medido em 30/10, 30 sementes × 4 taxas, com o tempo verdadeiro: sem margem a
#: borda do filtro move `mag_din_media` em até 1,0 %; com 0,5 s, a cadeia por
#: época bate com a noite inteira em 1,5e-6 g. 1,0 s não melhora nada.
MARGEM_S = 0.5

#: Quanto além da janela as drenagens entram no ajuste da linha do tempo.
#: É também a LATÊNCIA: a época k só fecha quando chega uma drenagem depois de
#: `fim + margem + folga`. 2 s ≈ uma drenagem a mais de cada lado.
FOLGA_DO_AJUSTE_S = 2.0

#: Menos que isto e a regressão não tem com o que se apoiar. Numa janela de
#: 31 s + 2 × 2 s cabem ~20 drenagens; 8 aceita perder mais da metade.
MINIMO_DE_DRENAGENS = 8

#: Faixa plausível da taxa estimada, como fração da nominal. O oscilador
#: promete −15/+10 %; fora de ±20 % a estimativa está medindo outra coisa
#: (FIFO resetada no meio, contagem corrompida), não o oscilador.
TAXA_MINIMA_FRAC = 0.8
TAXA_MAXIMA_FRAC = 1.2

#: Intervalo entre drenagens: metade da FIFO (85 amostras a 50 Hz = 1,7 s).
INTERVALO_DE_DRENAGEM_S = 1.7

#: Variação deliberada do intervalo, em [0, 20 ms). Sem ela, a 50 Hz exatos
#: o despertar trava em fase com a amostragem (85 amostras = 1,7 s): toda
#: drenagem cai no mesmo ponto entre duas amostras, e a regressão herda esse
#: deslocamento inteiro em vez de tirar a média dele. Medido em 30/10: o erro
#: de tempo no centro da época cai de 8,1 ms para 4,7 ms no pior caso.
VARIACAO_DA_DRENAGEM_S = 0.020

#: Q das duas seções de segunda ordem de um Butterworth de 4ª ordem:
#: 1 / (2 cos(π/8)) e 1 / (2 cos(3π/8)). Em cascata, com os mesmos `k` da
#: transformada bilinear, dão exatamente `butter(4, ...)`.
Q_DAS_SECOES = (1.0 / (2.0 * math.cos(math.pi / 8.0)),
                1.0 / (2.0 * math.cos(3.0 * math.pi / 8.0)))


# ==========================================================================
# O gerador de casos
# ==========================================================================
def gerar_caso(seed: int, fs_real: float, n_epocas: int = 2,
               inicio_s: float = -2.0, origem_us: int = 100_000_000) -> dict:
    """Um registro de FIFO sintético, com a taxa real `fs_real`.

    O tempo é relativo ao início da primeira época (t = 0 ↔ `origem_us` no
    relógio do ESP32). O registro começa em `inicio_s` = −2 s, um múltiplo
    exato do passo da grade, para que a grade do `reamostrar` (que nasce na
    primeira amostra) caia exatamente sobre o início de cada época.

    O sinal é o da geradora histórica (`dourado_casos.epoca_sintetica`):
    gravidade em direção aleatória, três senoides lentas, ruído — **mais uma
    componente entre 14 e 20 Hz**. É ela que exercita o anti-aliasing: acima
    dos 12,8 Hz da grade, abaixo do DLPF de 21 Hz, e que sem filtro dobraria
    para 12 a 18 Hz.
    """
    rng = np.random.default_rng(seed)
    # Até onde o registro vai: a última janela, a folga do ajuste e mais duas
    # drenagens. Com só +2 s, a 42,5 Hz a última drenagem caía antes do fim da
    # janela e a época 1 saía recusada — o firmware espera, o gerador não.
    fim_s = n_epocas * DURACAO_EPOCA_S + MARGEM_S + FOLGA_DO_AJUSTE_S + 2 * INTERVALO_DE_DRENAGEM_S
    n = int(math.floor((fim_s - inicio_s) * fs_real)) + 1
    t = inicio_s + np.arange(n) / fs_real

    g = rng.normal(size=3)
    g /= np.linalg.norm(g)
    mov = np.zeros((n, 3))
    for _ in range(3):
        d = rng.normal(size=3)
        d /= np.linalg.norm(d)
        mov += np.outer(np.sin(2 * np.pi * rng.uniform(0.3, 3.5) * t + rng.uniform(0, 6.28)), d)
    a = g + mov * rng.uniform(0.005, 0.08) + rng.normal(0, 0.003, (n, 3))
    d = rng.normal(size=3)
    d /= np.linalg.norm(d)
    a += np.outer(np.sin(2 * np.pi * rng.uniform(14.0, 20.0) * t + rng.uniform(0, 6.28)), d) \
        * rng.uniform(0.01, 0.05)

    # O que o sensor entrega: inteiros de 16 bits. As duas referências partem
    # destes MESMOS inteiros, então a quantização é modo-comum.
    lsb = np.clip(np.round(a * LSB_POR_G), -32768, 32767).astype(np.int64)

    # As drenagens, no relógio do ESP32 (aqui tomado como verdadeiro: o erro
    # dele é a parte (c) do ARQ-01, que só a placa mede). Cada uma lê tudo o
    # que a FIFO acumulou até aquele instante, com 0–3 ms de latência de
    # despertar por cima do intervalo variado.
    drenagens = []
    agenda = inicio_s + rng.uniform(0.2, INTERVALO_DE_DRENAGEM_S)
    lidas = 0
    while agenda < fim_s:
        instante = agenda + rng.uniform(0.0, 0.003)
        acumulado = int(np.searchsorted(t, instante, side="right"))
        drenagens.append([origem_us + int(round(instante * 1e6)), acumulado - lidas])
        lidas = acumulado
        agenda += INTERVALO_DE_DRENAGEM_S + rng.uniform(0.0, VARIACAO_DA_DRENAGEM_S)

    return {
        "seed": seed,
        "fs_real_hz": fs_real,
        "origem_us": origem_us,
        "inicio_do_registro_s": inicio_s,
        "n_epocas": n_epocas,
        "t_verdadeiro_s": t,          # NÃO vai para o JSON: o firmware não o tem
        "amostras_lsb": lsb,
        "drenagens": drenagens,       # [t_us, quantas amostras vieram]
    }


# ==========================================================================
# Referência de VALIDADE: o pipeline do ml/, com o tempo verdadeiro
# ==========================================================================
def esperado_pelo_pipeline(caso: dict) -> list[dict]:
    from src.features import NOMES_FEATURES, features_de_epoca, unitario
    from src.sinal import reamostrar

    t = caso["t_verdadeiro_s"]
    a = caso["amostras_lsb"] / LSB_POR_G
    tg, ag = reamostrar(t, a, TAXA_DA_GRADE_HZ, CORTE_ANTIALIASING_HZ / (TAXA_DA_GRADE_HZ / 2))
    saida = []
    for k in range(caso["n_epocas"]):
        i0 = int(round((k * DURACAO_EPOCA_S - tg[0]) * TAXA_DA_GRADE_HZ))
        assert abs(tg[i0] - k * DURACAO_EPOCA_S) < 1e-9, "a grade não caiu no início da época"
        fatia = ag[i0:i0 + AMOSTRAS_NA_GRADE]
        X, g_media = features_de_epoca(fatia[None, :, :], fs=TAXA_DA_GRADE_HZ)
        esperado = {n: float(X[0, i]) for i, n in enumerate(NOMES_FEATURES)}
        esperado["g"] = [float(v) for v in unitario(g_media[0])]
        saida.append({"esperado": esperado, "grade": fatia})
    return saida


# ==========================================================================
# Referência de EXATIDÃO: o que o firmware faz, em laços escalares
# ==========================================================================
def ajustar_linha_do_tempo(drenagens_acumuladas, origem_us: int, inicio_s: float, fim_s: float):
    """Regressão de mínimos quadrados do instante da drenagem pela contagem.

    `drenagens_acumuladas`: [(t_us, contagem acumulada depois da drenagem)].
    Devolve `(a, b, n)` com o instante da amostra de índice global `k` dado por
    `t_k = a + b·(k + 0,5)`, em segundos relativos a `origem_us`, ou `None`.

    Por que `k + 0,5`: a drenagem que deixa a contagem em `C` acontece depois da
    amostra `C − 1`, num ponto uniforme do intervalo entre ela e a próxima. Em
    média, a amostra `C − 1` está meio passo antes da drenagem. Sem o meio
    passo, toda a linha do tempo fica 10 ms atrasada — o sabotador
    `sem_meio_passo` mede isso.

    Duas passagens (médias, depois somas centradas) e não a fórmula de uma
    passagem: com `x` na casa dos milhares e `y` em segundos, `Σx² − n·x̄²`
    cancela catastroficamente em float e o C++ não teria como acompanhar.
    """
    xs, ys = [], []
    for t_us, acumulado in drenagens_acumuladas:
        t = (t_us - origem_us) / 1e6
        if inicio_s - FOLGA_DO_AJUSTE_S <= t <= fim_s + FOLGA_DO_AJUSTE_S:
            xs.append(float(acumulado))
            ys.append(t)
    n = len(xs)
    if n < MINIMO_DE_DRENAGENS:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sxy = 0.0
    for x, y in zip(xs, ys):
        sxx += (x - mx) * (x - mx)
        sxy += (x - mx) * (y - my)
    if sxx <= 0.0:
        return None
    b = sxy / sxx
    a = my - b * mx
    return a, b, n


def _secao(fs: float, corte_hz: float, q: float) -> tuple[float, float, float, float, float]:
    k = math.tan(math.pi * corte_hz / fs)
    norma = 1.0 / (1.0 + k / q + k * k)
    b0 = k * k * norma
    return b0, 2.0 * b0, b0, 2.0 * (k * k - 1.0) * norma, (1.0 - k / q + k * k) * norma


def _passagem(v: list[float], c) -> list[float]:
    b0, b1, b2, a1, a2 = c
    x1 = x2 = y1 = y2 = v[0]          # regime permanente, como em filtro.cpp
    saida = [0.0] * len(v)
    for i, amostra in enumerate(v):
        y = b0 * amostra + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        x2, x1 = x1, amostra
        y2, y1 = y1, y
        saida[i] = y
    return saida


def filtrar_antialiasing(v: list[float], fs: float, ordem: int = 4) -> list[float]:
    """Butterworth de `ordem` 4 a 12,8 Hz, ida e volta (fase zero).

    As duas seções em cascata na ida, as duas na volta. `ordem` existe só para
    o sabotador `ordem_2` poder pedir uma seção.
    """
    secoes = [_secao(fs, CORTE_ANTIALIASING_HZ, q) for q in Q_DAS_SECOES]
    if ordem == 2:
        secoes = [_secao(fs, CORTE_ANTIALIASING_HZ, math.sqrt(0.5))]
    for c in secoes:
        v = _passagem(v, c)
    v = v[::-1]
    for c in secoes:
        v = _passagem(v, c)
    return v[::-1]


def cadeia_estilo_firmware(caso: dict, sabotagem: str | None = None) -> list[dict]:
    """A cadeia inteira, época por época, com o que o firmware sabe.

    `sabotagem` só existe para os testes medirem o efeito de cada erro
    plausível — nunca para uso. Valores: `taxa_nominal`, `sem_antialiasing`,
    `ordem_2`, `sem_meio_passo`, `sem_margem`, `grade_deslocada`.
    """
    origem = caso["origem_us"]
    lsb = caso["amostras_lsb"]
    acumulado = 0
    acumuladas = []
    for t_us, n in caso["drenagens"]:
        acumulado += n
        acumuladas.append((t_us, acumulado))
    total = acumulado

    margem = 0.0 if sabotagem == "sem_margem" else MARGEM_S
    saida = []
    for k in range(caso["n_epocas"]):
        e0 = k * DURACAO_EPOCA_S
        jan_ini, jan_fim = e0 - margem, e0 + DURACAO_EPOCA_S + margem
        ajuste = ajustar_linha_do_tempo(acumuladas, origem, jan_ini, jan_fim)
        if ajuste is None:
            saida.append(None)
            continue
        a, b, n_ajuste = ajuste
        if sabotagem == "taxa_nominal":
            b = 1.0 / TAXA_NOMINAL_HZ
        meio = 0.0 if sabotagem == "sem_meio_passo" else 0.5
        fs = 1.0 / b
        if not (TAXA_MINIMA_FRAC * TAXA_NOMINAL_HZ <= fs <= TAXA_MAXIMA_FRAC * TAXA_NOMINAL_HZ):
            saida.append(None)
            continue

        k_ini = int(math.floor((jan_ini - a) / b - meio))
        k_fim = int(math.ceil((jan_fim - a) / b - meio))
        if k_ini < 0 or k_fim + 1 > total:
            saida.append(None)
            continue

        deslocamento = 1.0 / TAXA_DA_GRADE_HZ if sabotagem == "grade_deslocada" else 0.0
        grade = [[0.0, 0.0, 0.0] for _ in range(AMOSTRAS_NA_GRADE)]
        for eixo in range(3):
            v = [float(lsb[i, eixo]) / LSB_POR_G for i in range(k_ini, k_fim + 1)]
            if sabotagem != "sem_antialiasing":
                v = filtrar_antialiasing(v, fs, ordem=2 if sabotagem == "ordem_2" else 4)
            for j in range(AMOSTRAS_NA_GRADE):
                t = e0 + j / TAXA_DA_GRADE_HZ + deslocamento
                x = (t - a) / b - meio - k_ini
                i = int(math.floor(x))
                fr = x - i
                if i < 0 or i + 1 >= len(v):     # não acontece com a margem; guarda
                    i, fr = (0, 0.0) if i < 0 else (len(v) - 2, 1.0)
                grade[j][eixo] = v[i] + (v[i + 1] - v[i]) * fr
        saida.append({
            "a_s": a, "b_s": b, "n_drenagens": n_ajuste,
            "k_ini": k_ini, "k_fim": k_fim,
            "grade": np.asarray(grade),
        })
    return saida
