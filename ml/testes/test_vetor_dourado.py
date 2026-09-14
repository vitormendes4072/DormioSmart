"""Teste do vetor dourado: o Python e o firmware calculam a MESMA feature.

Por que este teste é o mais importante dos três
-----------------------------------------------
O `DATA-07` manda o dispositivo enviar o vetor de features por época, não o
sinal bruto. Isso significa que existem **duas implementações** da mesma
fórmula: a de Python (aqui) e a de C++ (no ESP32). Duas implementações da mesma
fórmula divergem — é quase certo — e a divergência é **silenciosa**: o modelo
treina numa definição de `enmo_media` e roda sobre outra, e ninguém vê.

Este teste fixa uma referência escalar, escrita em laços simples no estilo do
firmware (sem vetorização), e exige que a versão de produção bata com ela. O
JSON gerado em `testes/vetor_dourado.json` é para o **outro lado**: o teste em
C++ lê o mesmo arquivo e compara os mesmos números.

⚠️ Enquanto o firmware não consumir este JSON, a paridade está garantida só de
um lado. O item fica registrado no `DATA-07`.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from src.features import (
    CORTE_GRAVIDADE_HZ, FEATURES_DEPENDENTES_DO_FILTRO, LIMIAR_P_FRAC_G,
    NOMES_FEATURES, features_de_epoca,
)

RAIZ = Path(__file__).resolve().parents[1]
CAMINHO_DOURADO = RAIZ / "testes" / "vetor_dourado.json"


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
    """As 6 features intra-época, em laços escalares. `a` em g, (n, 3).

    É esta a especificação que o C++ implementa. Nada de numpy, nada de
    vetorização: só o que roda num ESP32 em ponto flutuante simples.
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

    return {
        "enmo_media": media,
        "enmo_desvio": desvio,
        "enmo_max": maximo,
        "mag_din_media": soma_mag_din / n,
        "zcr": cruz / (n - 1),
        "p_frac": acima / n,
    }


def _epoca_sintetica(seed: int, fs: float = 32.0, dur_s: float = 30.0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(fs * dur_s)
    t = np.arange(n) / fs
    g = rng.normal(size=3)
    g /= np.linalg.norm(g)
    mov = np.zeros((n, 3))
    for _ in range(3):
        d = rng.normal(size=3)
        d /= np.linalg.norm(d)
        mov += np.outer(np.sin(2 * np.pi * rng.uniform(0.3, 3.5) * t + rng.uniform(0, 6.28)), d)
    return g + mov * rng.uniform(0.005, 0.08) + rng.normal(0, 0.003, (n, 3))


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
def test_paridade_python_firmware(seed):
    """As 6 features intra-época batem entre as duas implementações."""
    fs = 32.0
    a = _epoca_sintetica(seed, fs)
    X, _ = features_de_epoca(a[None, :, :], fs=fs)
    ref = features_estilo_firmware(a, fs)

    # Features que NÃO passam pelo filtro de gravidade: têm de bater
    # exatamente. Qualquer divergência aqui é bug de implementação.
    for nome in ("enmo_media", "enmo_desvio", "enmo_max", "zcr"):
        i = NOMES_FEATURES.index(nome)
        assert X[0, i] == pytest.approx(ref[nome], abs=1e-9, rel=1e-6), (
            f"{nome} divergiu e NÃO depende do filtro — é bug: "
            f"Python {X[0, i]!r} vs firmware {ref[nome]!r}"
        )

    # Features que dependem da gravidade estimada. O firmware usa o mesmo
    # Butterworth de ordem 2 ida-e-volta, mas o `filtfilt` do scipy ainda faz
    # preenchimento por reflexão ímpar nas bordas, que o firmware não faz.
    # A tolerância cobre só esse resíduo de borda — e está declarada, não
    # escondida. Se estourar, o filtro do firmware saiu de sincronia com o da
    # referência, e é isso que o teste existe para avisar.
    n_amostras = a.shape[0]
    for nome in sorted(FEATURES_DEPENDENTES_DO_FILTRO):
        i = NOMES_FEATURES.index(nome)
        if nome == "p_frac":
            # `p_frac` é uma fração de amostras acima de um limiar RÍGIDO, não
            # uma quantidade contínua: o resíduo de borda entre `filtfilt`
            # (scipy) e o filtro causal ida-e-volta do firmware pode bastar
            # para empurrar uma amostra que caiu bem em cima do limiar para o
            # lado oposto. Isso muda a contagem em ±1 amostra, não o valor —
            # por isso a tolerância certa é absoluta, do tamanho de ~2
            # amostras em `n_amostras`, e não um percentual do valor de
            # referência (que falha exatamente quando p_frac é pequeno, como
            # em noites paradas — ver seed=5, onde 17 vs 18 em 960 amostras
            # já excede 5% de um valor de ~0,018).
            tol_abs = 2.5 / n_amostras
            assert X[0, i] == pytest.approx(ref[nome], abs=tol_abs), (
                f"p_frac divergiu além de ±2 amostras (de {n_amostras}, "
                f"tolerância de resíduo de borda do filtro): "
                f"Python {X[0, i]!r} vs firmware {ref[nome]!r}. "
                f"Verifique se o biquad do firmware ainda é butter(2, "
                f"{CORTE_GRAVIDADE_HZ} Hz) aplicado nos dois sentidos."
            )
        else:
            assert X[0, i] == pytest.approx(ref[nome], rel=0.05, abs=1e-4), (
                f"{nome} divergiu além do resíduo de borda esperado: "
                f"Python {X[0, i]!r} vs firmware {ref[nome]!r}. "
                f"Verifique se o biquad do firmware ainda é butter(2, "
                f"{CORTE_GRAVIDADE_HZ} Hz) aplicado nos dois sentidos."
            )


def test_gravar_vetor_dourado():
    """Grava a referência para o lado C++ consumir."""
    fs = 32.0
    casos = []
    for seed in (1, 2, 3, 4, 5):
        a = _epoca_sintetica(seed, fs)
        X, _ = features_de_epoca(a[None, :, :], fs=fs)
        casos.append({
            "seed": seed,
            "fs_hz": fs,
            "n_amostras": int(a.shape[0]),
            "entrada_g": np.round(a, 9).tolist(),
            "esperado": {n: float(X[0, i]) for i, n in enumerate(NOMES_FEATURES)},
        })
    CAMINHO_DOURADO.write_text(json.dumps({
        "descricao": ("Vetor dourado das features por época. O teste em C++ do "
                      "firmware deve ler este arquivo e reproduzir 'esperado'."),
        "limiar_p_frac_g": LIMIAR_P_FRAC_G,
        "corte_gravidade_hz": CORTE_GRAVIDADE_HZ,
        "ordem_features": list(NOMES_FEATURES),
        "nota": ("inclinacao_rel e d_angulo são INTER-época e valem 0 quando há "
                 "uma única época; a paridade delas exige uma sequência."),
        "casos": casos,
    }, indent=2), encoding="utf-8")
    assert CAMINHO_DOURADO.exists()


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
