"""Modelos aprendidos — passos 2 a 4 da escada do §7.

⚠️ **Nada aqui vale sem o `ML-02` medido ao lado.** A escada é, nesta ordem:

    0. "sempre dormindo"        -> baseline.py  ◄── SEMPRE reportar
    1. Cole-Kripke / Sadeh      -> baseline.py
    2. Regressão logística      -> aqui
    3. Random Forest / GB       -> aqui
    4. Suavização temporal      -> aqui
    5. CNN 1-D (opcional)       -> não implementado; só se vencer o 3 com folga

O passo 4 costuma render mais ganho que trocar de classificador: sono tem
estrutura temporal — não se alterna acordado/dormindo a cada 30 s.
"""

from __future__ import annotations

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

__all__ = ["regressao_logistica", "random_forest", "suavizar_mediana"]


def regressao_logistica(seed: int) -> Pipeline:
    """Interpretável: dá para dizer QUAL feature pesa. Numa banca isso vale
    mais que 2 pontos de acurácia.

    `class_weight="balanced"` de propósito: sem isso, com ~87% de sono, o
    otimizador converge para algo próximo do trivial e a especificidade morre.
    """
    return Pipeline([
        ("escala", StandardScaler()),
        ("clf", LogisticRegression(
            max_iter=2000, class_weight="balanced", random_state=seed)),
    ])


def random_forest(seed: int) -> RandomForestClassifier:
    return RandomForestClassifier(
        n_estimators=300, min_samples_leaf=5, class_weight="balanced_subsample",
        n_jobs=-1, random_state=seed,
    )


def suavizar_mediana(y: np.ndarray, janela: int = 5) -> np.ndarray:
    """Mediana móvel sobre a predição. Passo 4 da escada.

    Impõe a estrutura temporal que o sinal tem e o classificador por época
    ignora. ⚠️ Melhora kappa e acurácia, mas **tende a apagar despertares
    curtos** — que são justamente uma das saídas úteis do produto (§6). Reportar
    o efeito sobre o número de despertares, não só sobre o kappa.
    """
    y = np.asarray(y, dtype=int)
    if janela <= 1 or y.shape[0] < janela:
        return y.copy()
    if janela % 2 == 0:
        janela += 1
    meio = janela // 2
    estendido = np.pad(y, meio, mode="edge")
    janelas = np.lib.stride_tricks.sliding_window_view(estendido, janela)
    return (np.median(janelas, axis=1) >= 0.5).astype(int)
