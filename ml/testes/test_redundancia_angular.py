"""Trava a decisão de guardar `ĝ` em vez dos dois ângulos.

Ver `docs/DECISAO-BUFFER-E-FEATURES.md`, Saída 2.

O firmware vai guardar, por época, o **vetor gravidade unitário** `ĝ` — e não
`inclinacao_rel` e `d_angulo`. A justificativa tem duas metades, e este arquivo
testa as duas, porque se qualquer uma cair a decisão muda:

1. **A alternativa barata NÃO funciona.** `d_angulo` não é recuperável de
   `inclinacao_rel`: são ângulos numa esfera e o que vale entre eles é a
   desigualdade triangular esférica, não uma igualdade. A aproximação erra
   pouco em repouso e MUITO nas viradas — exatamente onde a feature importa.

2. **Guardar `ĝ` funciona, e exatamente.** As duas features são funções de `ĝ`,
   então derivá-las na drenagem reproduz os valores sem erro nenhum. É isso que
   permite calcular `ĝ_ref` com o MESMO Weiszfeld do Python, em vez de um
   acumulador incremental que seria outro estimador e divergiria em silêncio.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.features import (
    NOMES_FEATURES, _angulo_entre, _unitario, direcao_referencia, features_de_epoca,
)


def _epoca_sintetica(seed: int, fs: float = 32.0, dur_s: float = 30.0) -> np.ndarray:
    """Mesma geradora do vetor dourado, para as duas suítes falarem do mesmo sinal."""
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


@pytest.fixture(scope="module")
def sequencia():
    """Uma sequência de 40 épocas — o mínimo para as features inter-época existirem."""
    a = np.stack([_epoca_sintetica(s) for s in range(1, 41)])
    X, g_media = features_de_epoca(a, fs=32.0)
    return X, g_media


def test_g_reconstroi_as_duas_features_exatamente(sequencia):
    """Guardar `ĝ` por época basta: os dois ângulos saem dele sem erro."""
    X, g_media = sequencia
    u = _unitario(g_media)
    u_ref = direcao_referencia(g_media)

    inc = _angulo_entre(u, np.broadcast_to(u_ref, u.shape))
    dang = np.zeros(len(u))
    if len(u) > 1:
        dang[1:] = _angulo_entre(u[1:], u[:-1])

    i_inc = NOMES_FEATURES.index("inclinacao_rel")
    i_dang = NOMES_FEATURES.index("d_angulo")

    assert np.allclose(inc, X[:, i_inc], atol=1e-12, rtol=0), (
        "inclinacao_rel deixou de ser função de ĝ — a decisão de guardar ĝ "
        "em vez do ângulo depende disto."
    )
    assert np.allclose(dang, X[:, i_dang], atol=1e-12, rtol=0), (
        "d_angulo deixou de ser função de ĝ — ver DECISAO-BUFFER-E-FEATURES.md."
    )


def test_d_angulo_nao_e_a_diferenca_de_inclinacao(sequencia):
    """A alternativa barata falha, e falha GRANDE. Este teste existe para que
    ninguém a reintroduza achando que economiza 2 bytes por época."""
    X, _ = sequencia
    inc = X[:, NOMES_FEATURES.index("inclinacao_rel")]
    dang = X[:, NOMES_FEATURES.index("d_angulo")]

    aprox = np.zeros(len(inc))
    aprox[1:] = np.abs(np.diff(inc))
    erro = np.abs(aprox - dang)

    assert erro.max() > 5.0, (
        "a aproximação |Δinclinacao_rel| passou a acertar d_angulo neste sinal. "
        "Isso é suspeito: geometricamente ela só acerta se ĝ_ref, ĝ_{t-1} e ĝ_t "
        "caírem no mesmo grande círculo. Confira a geradora do sinal antes de "
        "concluir que a aproximação serve."
    )


def test_desigualdade_triangular_esferica(sequencia):
    """O que REALMENTE vale entre as duas features — e é uma desigualdade.

    |θ_t − θ_{t−1}| ≤ d_angulo ≤ θ_t + θ_{t−1}

    É esta a razão de `d_angulo` não ser derivável de `inclinacao_rel`: a
    desigualdade deixa um grau de liberdade que só `ĝ` fecha.
    """
    X, _ = sequencia
    inc = X[:, NOMES_FEATURES.index("inclinacao_rel")]
    dang = X[:, NOMES_FEATURES.index("d_angulo")]

    inferior = np.abs(inc[1:] - inc[:-1])
    superior = inc[1:] + inc[:-1]
    d = dang[1:]

    assert np.all(d >= inferior - 1e-9), "violou o limite inferior da desigualdade esférica"
    assert np.all(d <= superior + 1e-9), "violou o limite superior da desigualdade esférica"


def test_g_e_unitario_cabe_em_int16(sequencia):
    """O layout de 40 B guarda ĝ como 3 × int16 em [-1, 1]. Isso só vale se ĝ
    for de fato unitário — caso contrário o fundo de escala satura."""
    _, g_media = sequencia
    u = _unitario(g_media)
    normas = np.linalg.norm(u, axis=1)
    assert np.allclose(normas, 1.0, atol=1e-12)
    assert np.all(np.abs(u) <= 1.0 + 1e-12), "componente de ĝ fora de [-1, 1]"

    # Passo do int16 sobre [-1, 1], e o erro angular que ele introduz.
    passo = 2.0 / 65535
    uq = np.round(u / passo) * passo
    uq = _unitario(uq)
    erro_graus = _angulo_entre(u, uq)
    assert erro_graus.max() < 0.01, (
        f"quantizar ĝ em int16 custou {erro_graus.max():.4f} grau — "
        f"esperado bem abaixo de 0,01"
    )
