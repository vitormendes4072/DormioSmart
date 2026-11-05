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

# ML-14: falha completa tem F1 zero; so denominador nulo e indefinido.
@pytest.mark.parametrize("y,p,sono,vigilia", [
    ([0, 1], [1, 0], 0.0, 0.0),
    ([1, 1], [0, 0], 0.0, 0.0),
    ([0, 0], [1, 1], 0.0, 0.0),
    ([1, 1, 0, 0], [1, 0, 0, 0], 2 / 3, 4 / 5),
    ([0, 1], [0, 1], 1.0, 1.0),
    ([], [], np.nan, np.nan),
    ([1, 1], [1, 1], 1.0, np.nan),
    ([0, 0], [0, 0], np.nan, 1.0),
])
def test_f1_por_contagens_inclui_falhas_e_distingue_ausencia(y, p, sono, vigilia):
    m = avaliar_epoca(np.array(y), np.array(p))
    assert np.isclose(m.f1_sono, sono, equal_nan=True)
    assert np.isclose(m.f1_vigilia, vigilia, equal_nan=True)


def test_f1_bate_com_sklearn_em_todas_as_sequencias_binarias_de_tres_epocas():
    from itertools import product
    from sklearn.metrics import f1_score
    sequencias = list(product((0, 1), repeat=3))
    for y in sequencias:
        for p in sequencias:
            m = avaliar_epoca(np.array(y), np.array(p))
            for classe, valor in ((1, m.f1_sono), (0, m.f1_vigilia)):
                ref = f1_score(y, p, pos_label=classe, zero_division=np.nan)
                assert np.isclose(valor, ref, equal_nan=True), (y, p, classe)


def test_f1_zero_entra_na_media_desvio_e_bootstrap():
    y = np.array([0, 1, 0, 1, 1, 1])
    p = np.array([0, 1, 1, 0, 1, 1])
    ids = np.array(["a", "a", "b", "b", "c", "c"])
    m = avaliar_por_sujeito(y, p, ids, metricas=("f1_vigilia",), seed=0)
    assert np.allclose(m.por_sujeito["f1_vigilia"], [1, 0, np.nan], equal_nan=True)
    assert m.n_valido["f1_vigilia"] == 2
    assert m.media["f1_vigilia"] == pytest.approx(0.5)
    assert m.desvio_padrao["f1_vigilia"] == pytest.approx(np.sqrt(0.5))
    reamostras = np.random.default_rng(0).choice([1.0, 0.0], size=(2000, 2), replace=True)
    ic = np.percentile(reamostras.mean(axis=1), [2.5, 97.5])
    assert m.ic95_baixo["f1_vigilia"] == pytest.approx(ic[0])
    assert m.ic95_alto["f1_vigilia"] == pytest.approx(ic[1])


def test_falha_completa_de_todos_os_sujeitos_tem_media_e_ic_zero():
    m = avaliar_por_sujeito(np.array([0, 1, 0, 1]), np.array([1, 0, 1, 0]),
                           np.array(["a", "a", "b", "b"]))
    for metrica in ("f1_sono", "f1_vigilia"):
        assert m.n_valido[metrica] == 2
        assert m.media[metrica] == m.desvio_padrao[metrica] == 0
        assert m.ic95_baixo[metrica] == m.ic95_alto[metrica] == 0
