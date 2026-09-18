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

__all__ = [
    "regressao_logistica", "random_forest", "suavizar_mediana",
    "transicoes_hmm", "suavizar_hmm",
]


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


def transicoes_hmm(y: np.ndarray, id_sujeito: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Matriz de transição 2×2 e prior, contados nos rótulos VERDADEIROS.

    ⚠️ Só pode ser chamada sobre o fold de TREINO. A matriz de transição é um
    parâmetro aprendido como qualquer outro: estimá-la sobre os rótulos do
    sujeito de teste é vazamento, e um vazamento particularmente eficaz —
    a transição carrega quase toda a informação de quanto o sujeito acordou.

    As transições são contadas DENTRO de cada sujeito: o par (última época do
    sujeito A, primeira do sujeito B) não é uma transição, é uma emenda.

    Devolve `(A, pi)` com `A[i, j] = P(estado_t = j | estado_{t-1} = i)` e
    `pi[i] = P(estado_0 = i)`. Convenção do projeto: 0 = vigília, 1 = sono.
    """
    y = np.asarray(y, dtype=int)
    ids = np.asarray(id_sujeito, dtype=object)
    contagem = np.ones((2, 2), dtype=float)   # Laplace: nenhuma transição é impossível
    for s in sorted(set(ids.tolist())):
        seq = y[ids == s]
        if seq.size < 2:
            continue
        np.add.at(contagem, (seq[:-1], seq[1:]), 1.0)
    A = contagem / contagem.sum(axis=1, keepdims=True)
    prior = np.array([np.count_nonzero(y == 0), np.count_nonzero(y == 1)], dtype=float)
    prior = np.clip(prior, 1.0, None)
    return A, prior / prior.sum()


def _estacionaria(A: np.ndarray) -> np.ndarray:
    """Distribuição estacionária da cadeia 2×2 — forma fechada, sem autovetor.

    Para `A = [[1-a, a], [b, 1-b]]`, π ∝ (b, a). É a distribuição inicial
    coerente com a própria matriz de transição, em vez de um prior avulso.
    """
    a, b = float(A[0, 1]), float(A[1, 0])
    if a + b <= 0:
        return np.array([0.5, 0.5])
    return np.array([b, a]) / (a + b)


def suavizar_hmm(
    prob_sono: np.ndarray,
    A: np.ndarray,
    prior_implicito: np.ndarray | None = None,
    pi: np.ndarray | None = None,
) -> np.ndarray:
    """Viterbi sobre um HMM de 2 estados (vigília/sono). Passo 4, versão forte.

    A mediana móvel impõe estrutura temporal por força bruta e com uma janela
    fixa. O HMM impõe a mesma estrutura, mas com o custo de trocar de estado
    calibrado nos dados (a matriz de transição) em vez de arbitrado — e por
    isso preserva um despertar longo enquanto apaga um isolado, que é
    exatamente o comportamento que a mediana não sabe distinguir.

    A emissão vem do classificador por época, via Bayes invertido:
    `P(x | estado) ∝ P(estado | x) / P(estado)`. O termo `P(x)` é constante
    ao longo dos estados e some no argmax.

    ⚠️ **`prior_implicito` é o prior embutido em `prob_sono`, não o prior do
    dataset.** É a pegadinha desta função, e ela custa ~40 pontos de acurácia
    quando erra. Com `class_weight="balanced"` o classificador já devolve a
    probabilidade sob prior uniforme — dividir de novo pela prevalência real
    (~85% de sono) aplica a correção DUAS vezes e o Viterbi despenca para
    vigília. Por isso o padrão é `None` = uniforme = não dividir. Passe a
    prevalência do treino só se `prob_sono` vier de um classificador SEM
    reponderação de classe.

    `prob_sono` é UMA sequência contígua de um único sujeito, em ordem
    temporal. `pi` é a distribuição inicial; se `None`, usa a distribuição
    estacionária de `A`.
    """
    p1 = np.clip(np.asarray(prob_sono, dtype=float), 1e-12, 1 - 1e-12)
    n = p1.shape[0]
    if n == 0:
        return np.zeros(0, dtype=int)

    A = np.asarray(A, dtype=float)
    posterior = np.column_stack([1.0 - p1, p1])              # (n, 2): [vigilia, sono]
    log_emissao = np.log(posterior)
    if prior_implicito is not None:
        log_emissao = log_emissao - np.log(np.clip(prior_implicito, 1e-12, None))
    log_A = np.log(np.clip(A, 1e-12, None))
    if pi is None:
        pi = _estacionaria(A)
    log_pi = np.log(np.clip(np.asarray(pi, dtype=float), 1e-12, None))

    delta = np.empty((n, 2), dtype=float)
    psi = np.zeros((n, 2), dtype=int)
    delta[0] = log_pi + log_emissao[0]
    for t in range(1, n):
        candidatos = delta[t - 1][:, None] + log_A          # (2 anterior, 2 atual)
        psi[t] = np.argmax(candidatos, axis=0)
        delta[t] = candidatos[psi[t], [0, 1]] + log_emissao[t]

    caminho = np.empty(n, dtype=int)
    caminho[-1] = int(np.argmax(delta[-1]))
    for t in range(n - 1, 0, -1):
        caminho[t - 1] = psi[t, caminho[t]]
    return caminho
