"""Testes de `src/avaliar.py`, com foco em `avaliar_por_sujeito`.

Por que este arquivo existe
---------------------------
`avaliar_por_sujeito` é a peça nova que separa "o modelo é assim" de "deu
azar na amostra": em vez de uma métrica pooled sobre todas as épocas, calcula
por sujeito e agrega com desvio-padrão ENTRE sujeitos e IC 95% por bootstrap.
Errar a agregação (por exemplo, tratar NaN de especificidade como zero, ou
deixar o bootstrap extrapolar além do intervalo observado) produz um número
que parece uma estatística e não é — e ninguém pega isso olhando a saída.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.avaliar import avaliar_epoca, avaliar_por_sujeito


def test_previsao_perfeita_da_media_1_e_desvio_0():
    rng = np.random.default_rng(0)
    ids = np.repeat(["s1", "s2", "s3"], 40)
    y = rng.integers(0, 2, ids.shape[0])
    pred = y.copy()  # perfeito

    m = avaliar_por_sujeito(y, pred, ids)
    assert m.n_sujeitos == 3
    assert m.media["kappa"] == pytest.approx(1.0)
    assert m.desvio_padrao["kappa"] == pytest.approx(0.0, abs=1e-9)
    assert m.ic95_baixo["kappa"] == pytest.approx(1.0, abs=1e-9)
    assert m.ic95_alto["kappa"] == pytest.approx(1.0, abs=1e-9)


def test_media_e_desvio_batem_com_calculo_manual():
    """Três sujeitos com acurácias BEM diferentes, construídas à mão."""
    ids = np.repeat(["a", "b", "c"], 100)
    y = np.ones(300, dtype=int)  # tudo sono -- kappa não importa aqui, só acurácia
    pred = np.ones(300, dtype=int)
    # sujeito b: 10% de erro; sujeito c: 30% de erro
    pred[100:110] = 0
    pred[210:240] = 0

    m = avaliar_por_sujeito(y, pred, ids, metricas=("acuracia",))
    esperado = np.array([1.0, 0.90, 0.70])
    assert np.allclose(sorted(m.por_sujeito["acuracia"]), sorted(esperado), atol=1e-9)
    assert m.media["acuracia"] == pytest.approx(esperado.mean(), abs=1e-9)
    assert m.desvio_padrao["acuracia"] == pytest.approx(esperado.std(ddof=1), abs=1e-9)


def test_nan_e_excluido_da_media_e_contado_em_n_valido():
    """Um sujeito sem nenhuma época de vigília dá especificidade NaN --
    tem de sair da média, não virar zero disfarçado."""
    ids = np.array(["a"] * 10 + ["b"] * 10)
    y = np.array([1] * 10 + [1, 1, 1, 1, 1, 0, 0, 0, 0, 0])  # a: só sono; b: metade
    pred = y.copy()

    m = avaliar_por_sujeito(y, pred, ids, metricas=("especificidade",))
    assert np.isnan(m.por_sujeito["especificidade"][list(m.sujeitos).index("a")])
    assert m.n_valido["especificidade"] == 1          # só "b" conta
    assert m.media["especificidade"] == pytest.approx(1.0, abs=1e-9)  # só o de "b"


def test_bootstrap_nao_extrapola_alem_do_observado():
    """IC 95% por bootstrap percentil de uma média nunca pode passar dos
    extremos dos valores por sujeito -- é uma propriedade matemática do
    método (toda reamostra é uma média de um subconjunto dos mesmos valores)."""
    rng = np.random.default_rng(1)
    ids = np.repeat([f"s{i}" for i in range(8)], 30)
    y = rng.integers(0, 2, ids.shape[0])
    pred = y.copy()
    # perturba por sujeito com taxas de erro bem diferentes, sem previsível
    for i in range(8):
        mask = ids == f"s{i}"
        idx = np.flatnonzero(mask)
        n_err = int(len(idx) * (i / 16))
        pred[idx[:n_err]] = 1 - pred[idx[:n_err]]

    m = avaliar_por_sujeito(y, pred, ids, metricas=("acuracia",), n_bootstrap=3000)
    vals = m.por_sujeito["acuracia"]
    assert m.ic95_baixo["acuracia"] >= vals.min() - 1e-9
    assert m.ic95_alto["acuracia"] <= vals.max() + 1e-9
    assert m.ic95_baixo["acuracia"] <= m.media["acuracia"] <= m.ic95_alto["acuracia"]


def test_um_unico_sujeito_da_ic_degenerado_no_proprio_valor():
    ids = np.array(["a"] * 20)
    y = np.array([1, 0] * 10)
    pred = y.copy()
    m = avaliar_por_sujeito(y, pred, ids, metricas=("acuracia",))
    assert m.n_sujeitos == 1
    assert m.desvio_padrao["acuracia"] == 0.0
    assert m.ic95_baixo["acuracia"] == m.ic95_alto["acuracia"] == m.media["acuracia"]


def test_resumo_formata_com_as_quatro_grandezas():
    ids = np.repeat(["a", "b", "c"], 20)
    rng = np.random.default_rng(2)
    y = rng.integers(0, 2, ids.shape[0])
    pred = rng.integers(0, 2, ids.shape[0])
    m = avaliar_por_sujeito(y, pred, ids, metricas=("kappa",))
    texto = m.resumo("kappa")
    assert "[" in texto and "]" in texto and "dp=" in texto and "n=" in texto


def test_agrega_bate_com_avaliar_epoca_por_sujeito_isolado():
    """Não é uma reimplementação paralela: cada valor por sujeito tem que ser
    exatamente o que `avaliar_epoca` calcularia isolando aquele sujeito."""
    rng = np.random.default_rng(3)
    ids = np.repeat(["x", "y"], 50)
    y = rng.integers(0, 2, 100)
    pred = rng.integers(0, 2, 100)

    m = avaliar_por_sujeito(y, pred, ids, metricas=("acuracia", "kappa"))
    for i, s in enumerate(m.sujeitos):
        mask = ids == s
        ref = avaliar_epoca(y[mask], pred[mask])
        assert m.por_sujeito["acuracia"][i] == pytest.approx(ref.acuracia, abs=1e-12)
        assert np.isclose(m.por_sujeito["kappa"][i], ref.kappa, atol=1e-12, equal_nan=True)
