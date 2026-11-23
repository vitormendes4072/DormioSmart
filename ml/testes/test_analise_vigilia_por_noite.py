"""A análise de vigília por noite (23/11): as contas batem com o scikit-learn e com casos feitos à mão."""
import numpy as np
import pytest
from sklearn.metrics import confusion_matrix, recall_score

from experimentos.analise_vigilia_por_noite import (
    analisar,
    especificidade_com_sensibilidade,
    metricas_por_epoca,
    por_noite,
)


def test_metricas_por_epoca_batem_com_o_scikit_learn():
    gerador = np.random.default_rng(7)
    y = gerador.integers(0, 2, 500)
    pred = np.where(gerador.random(500) < 0.8, y, 1 - y)
    m = metricas_por_epoca(y, pred)
    vn, fp, fn, vp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    assert (m["vp"], m["vn"], m["fp"], m["fn"]) == (vp, vn, fp, fn)
    assert m["sensibilidade"] == pytest.approx(recall_score(y, pred, pos_label=1))
    assert m["especificidade"] == pytest.approx(recall_score(y, pred, pos_label=0))


def test_sempre_sono_tem_especificidade_zero_e_acuracia_alta():
    y = np.array([1] * 90 + [0] * 10)
    m = metricas_por_epoca(y, np.ones_like(y))
    assert m["especificidade"] == 0 and m["acuracia"] == pytest.approx(0.9)
    assert m["f1_vigilia"] == 0


def test_por_noite_em_minutos_e_com_sinal():
    # Noite A: 10 épocas de vigília real, o modelo diz 4 -> +3 min de sono a mais.
    # Noite B: 2 de vigília real, o modelo diz 6 -> −2 min.
    y = np.array([0] * 10 + [1] * 30 + [0] * 2 + [1] * 38)
    pred = np.array([0] * 4 + [1] * 36 + [0] * 6 + [1] * 34)
    ids = np.array(["a"] * 40 + ["b"] * 40)
    r = por_noite(y, pred, ids)
    assert r["noites"] == 2
    assert r["vies_tst_min"] == pytest.approx((3 - 2) / 2)
    assert r["vigilia_real_media_min"] == pytest.approx((5 + 1) / 2)
    assert r["vigilia_prevista_media_min"] == pytest.approx((2 + 3) / 2)
    assert r["correlacao_vigilia_entre_noites"] == pytest.approx(-1.0)


def test_especificidade_cresce_quando_se_aceita_menos_sensibilidade():
    gerador = np.random.default_rng(3)
    y = np.array([1] * 400 + [0] * 100)
    prob = np.where(y == 1, gerador.beta(5, 2, 500), gerador.beta(2, 3, 500))
    assert especificidade_com_sensibilidade(y, prob, 0.80) > especificidade_com_sensibilidade(y, prob, 0.95)


def test_o_corte_e_escolhido_so_na_wearanize():
    gerador = np.random.default_rng(11)
    def coorte(n):
        y = (gerador.random(n) < 0.85).astype(int)
        prob = np.clip(np.where(y == 1, 0.7, 0.3) + gerador.normal(0, 0.15, n), 0, 1)
        return y, (prob > 0.5).astype(int), prob, np.repeat(np.arange(n // 100), 100)
    base = coorte(1000)
    dados = {"wearanize-cabeca": base, "dreamt": coorte(1000)}
    referencia = analisar(dados)["corte_de_maior_kappa_na_wearanize"]
    # Trocar a coorte externa não pode mudar o corte escolhido.
    dados["dreamt"] = coorte(1000)
    assert analisar(dados)["corte_de_maior_kappa_na_wearanize"] == referencia
