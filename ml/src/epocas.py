"""Janelamento em épocas de 30 s e alinhamento com o rótulo de PSG.

Regra que não se negocia: **época de 30 s**. É a resolução dos rótulos de PSG
em todas as bases (Newcastle, Walch, Wearanize+). Época diferente exigiria
reamostrar o rótulo — e reamostrar rótulo inventa informação.

O alinhamento é o ponto onde datasets multi-dispositivo costumam falhar em
silêncio. Aqui a regra é: **o rótulo manda**. As épocas são construídas a partir
do instante do primeiro rótulo, e amostras fora da cobertura de rótulo são
descartadas — nunca o contrário.
"""

from __future__ import annotations

import numpy as np

__all__ = ["fatiar_epocas", "empilhar_contexto"]


def fatiar_epocas(
    t: np.ndarray,
    a: np.ndarray,
    t0_rotulo: float,
    n_rotulos: int,
    epoca_s: float,
    fs: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Fatia (t, a) em épocas alinhadas ao rótulo.

    Returns
    -------
    a_epocas : (n_validas, n_amostras, 3)
    indices  : (n_validas,) índice do rótulo correspondente a cada época.
               Nem toda época de rótulo sobrevive: as que não têm cobertura
               completa de sinal são descartadas, e este vetor diz quais foram.
    """
    t = np.asarray(t, dtype=float)
    a = np.asarray(a, dtype=float)
    n_am = int(round(epoca_s * fs))
    if n_am < 2:
        raise ValueError("época curta demais para a taxa dada")

    blocos, indices = [], []
    for k in range(n_rotulos):
        ini = t0_rotulo + k * epoca_s
        i0 = int(np.searchsorted(t, ini, side="left"))
        i1 = i0 + n_am
        if i0 < 0 or i1 > t.shape[0]:
            continue
        # Guarda contra lacuna interna: se o trecho não for contíguo na grade,
        # a época não é confiável. Tolerância de meia amostra.
        if abs((t[i1 - 1] - t[i0]) - (n_am - 1) / fs) > 0.5 / fs:
            continue
        blocos.append(a[i0:i1])
        indices.append(k)

    if not blocos:
        return np.zeros((0, n_am, 3)), np.zeros((0,), dtype=int)
    return np.stack(blocos), np.asarray(indices, dtype=int)


def empilhar_contexto(X: np.ndarray, n_vizinhas: int) -> np.ndarray:
    """Concatena as features das ±n épocas vizinhas a cada época.

    A literatura de actigrafia é unânime em que a vizinhança importa: uma época
    quieta cercada de movimento é uma coisa; cercada de quietude, outra. Todos
    os algoritmos clássicos (Cole-Kripke, Sadeh) são janelas móveis por isso.

    Nas bordas, repete a época da ponta (padding por replicação). Alternativas
    — zeros ou descarte — ou inventam quietude que não existe, ou jogam fora as
    épocas de dormir e acordar, que são justamente as que interessam.

    (n, f) -> (n, f * (2*n_vizinhas + 1))
    """
    X = np.asarray(X, dtype=float)
    if n_vizinhas <= 0:
        return X.copy()
    n = X.shape[0]
    partes = []
    for d in range(-n_vizinhas, n_vizinhas + 1):
        idx = np.clip(np.arange(n) + d, 0, n - 1)
        partes.append(X[idx])
    return np.concatenate(partes, axis=1)
