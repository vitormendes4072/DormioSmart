"""O LOSO retomável tem de dar o MESMO resultado, cortado ou não.

É a única propriedade que justifica o mecanismo existir. Se rodar em vinte
chamadas produzisse um vetor diferente de rodar em uma, o checkpoint não
seria uma conveniência de infraestrutura — seria uma variável escondida no
experimento, e o número reportado dependeria de onde o shell cortou.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from experimentos._retomada import limpar_parcial, loso_com_retomada  # noqa: E402
from src.modelos import suavizar_hmm, transicoes_hmm                 # noqa: E402


def _dado(n_sujeitos: int = 7, n_epocas: int = 60, seed: int = 3):
    rng = np.random.default_rng(seed)
    X, y, ids = [], [], []
    for s in range(n_sujeitos):
        rotulos = np.concatenate([
            np.zeros(n_epocas // 6, dtype=int),
            np.ones(n_epocas - 2 * (n_epocas // 6), dtype=int),
            np.zeros(n_epocas // 6, dtype=int),
        ])
        X.append(rotulos[:, None] + rng.normal(0, 0.6, (rotulos.size, 3)))
        y.append(rotulos)
        ids.append(np.full(rotulos.size, f"sub-{s:02d}", dtype=object))
    return np.concatenate(X), np.concatenate(y), np.concatenate(ids)


def _dobra(X_tr, y_tr, X_te, ids_tr, seed):
    from sklearn.linear_model import LogisticRegression
    clf = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=seed)
    clf.fit(X_tr, y_tr)
    A, _ = transicoes_hmm(y_tr, ids_tr)
    return suavizar_hmm(clf.predict_proba(X_te)[:, 1], A)


def test_retomada_por_partes_da_o_mesmo_que_de_uma_vez(tmp_path):
    X, y, ids = _dado()

    limpar_parcial("teste-inteiro", tmp_path)
    inteiro, completo, feitas, total = loso_com_retomada(
        "teste-inteiro", X, y, ids, _dobra, seed=1, orcamento_s=10_000, pasta=tmp_path)
    assert completo and feitas == total == 7

    # Orçamento zero força exatamente UMA dobra por chamada (o laço sempre
    # roda ao menos uma antes de checar o relógio, senão nunca progrediria).
    limpar_parcial("teste-picado", tmp_path)
    chamadas = 0
    while True:
        picado, completo, feitas, total = loso_com_retomada(
            "teste-picado", X, y, ids, _dobra, seed=1, orcamento_s=0.0, pasta=tmp_path)
        chamadas += 1
        if completo:
            break
        assert chamadas <= total, "não progrediu: laço infinito"

    assert chamadas == total, "deveria ter levado uma chamada por dobra"
    np.testing.assert_array_equal(inteiro, picado)

    limpar_parcial("teste-inteiro", tmp_path)
    limpar_parcial("teste-picado", tmp_path)


def test_parcial_incompativel_falha_em_vez_de_misturar(tmp_path):
    X, y, ids = _dado(n_sujeitos=4)
    limpar_parcial("teste-colisao", tmp_path)
    loso_com_retomada("teste-colisao", X, y, ids, _dobra, seed=1, orcamento_s=0.0, pasta=tmp_path)

    X2, y2, ids2 = _dado(n_sujeitos=5)   # nº de épocas diferente, mesma chave
    with pytest.raises(RuntimeError, match="colidiu"):
        loso_com_retomada("teste-colisao", X2, y2, ids2, _dobra, seed=1, orcamento_s=0.0, pasta=tmp_path)

    limpar_parcial("teste-colisao", tmp_path)


def test_hmm_preserva_despertar_longo_e_apaga_isolado():
    """A razão de o HMM existir ao lado da mediana móvel.

    A mediana de janela 5 apaga qualquer bloco de até 2 épocas, sem olhar o
    quanto o classificador estava confiante. O HMM paga um custo de
    transição calibrado nos dados: um despertar isolado e duvidoso some, um
    despertar longo sobrevive.
    """
    rng = np.random.default_rng(0)
    y = np.concatenate([np.zeros(20, int), np.ones(80, int), np.zeros(1, int),
                        np.ones(40, int), np.zeros(10, int), np.ones(60, int)])
    ids = np.full(y.size, "s1", dtype=object)
    A, _ = transicoes_hmm(y, ids)
    prob = np.clip(np.where(y == 1, 0.65, 0.35) + rng.normal(0, 0.25, y.size), 0.01, 0.99)

    caminho = suavizar_hmm(prob, A)
    assert caminho[141:151].tolist() == [0] * 10, "apagou o despertar de 10 épocas"
    assert caminho[100] == 1, "manteve o despertar isolado de 1 época"
    assert np.mean(caminho == y) > np.mean((prob >= 0.5) == y), "não melhorou a predição bruta"


def test_transicoes_nao_atravessam_sujeito():
    """A emenda entre o fim de um sujeito e o começo do outro não é transição."""
    y = np.array([1, 1, 1, 0, 0, 0], dtype=int)
    ids = np.array(["a", "a", "a", "b", "b", "b"], dtype=object)
    A, _ = transicoes_hmm(y, ids)
    juntos = np.full(6, "a", dtype=object)
    A_junto, _ = transicoes_hmm(y, juntos)
    assert A[1, 0] < A_junto[1, 0], "contou a emenda entre sujeitos como transição"
