import numpy as np
import pytest
from sklearn.metrics import roc_auc_score

from experimentos import ml18
from experimentos.ml_inf_v2 import ajustar


def test_pessoa_vazada_entre_bracos_e_bloqueada_e_inflaria_auc():
    # O segundo atributo só distingue as classes da pessoa que está no pulso.
    x = np.array([[-1, 0], [1, 0], [-1, 0], [1, 0]], dtype=float)
    y = np.array([0, 1, 0, 1])
    pulso = np.array([[0, -1], [0, 1]], dtype=float)
    y_pulso = np.array([0, 1])
    p = ajustar(x, y, ml18.SEED_MODELO).predict_proba(pulso)[:, 1]
    with pytest.raises(ValueError, match="participante"):
        ml18.conferir_separacao({("wearanize", "1")}, {("wearanize", "1")})
    cabeca_da_mesma_pessoa = np.array([[0, -.7], [0, .7]], dtype=float)
    vazado = ajustar(np.vstack((x, cabeca_da_mesma_pessoa)), np.r_[y, y_pulso], ml18.SEED_MODELO)
    assert roc_auc_score(y_pulso, p) == 0.5
    assert roc_auc_score(y_pulso, vazado.predict_proba(pulso)[:, 1]) == 1


def test_plano_exclui_os_dois_bracos_wearanize():
    for base in ("wearanize/cabeca", "wearanize/pulso"):
        treino = ml18.bases_de_treino(base)
        assert treino == ("walch_principal", "dreamt", "newcastle")
    for base in ("walch_principal", "dreamt", "newcastle"):
        assert base not in ml18.bases_de_treino(base)
        assert len(ml18.bases_de_treino(base)) == 4


def test_controle_embaralhado_preserva_classes_e_destroi_sinal_sintetico():
    rng = np.random.default_rng(121)
    x = rng.normal(size=(2000, 8))
    y = (x[:, 0] > 0).astype(int)
    grupos = np.array_split(y, 2)
    xt = rng.normal(size=(2000, 8))
    yt = (xt[:, 0] > 0).astype(int)
    assert roc_auc_score(yt, ajustar(x, y, ml18.SEED_MODELO).predict_proba(xt)[:, 1]) > .95
    aucs = []
    for i in range(20):
        permutado = ml18.embaralhar(grupos, divisao=0, rodada=i)
        for a, b in zip(grupos, np.array_split(permutado, 2)):
            assert np.array_equal(np.bincount(a), np.bincount(b))
        prob = ajustar(x, permutado, ml18.SEED_MODELO).predict_proba(xt)[:, 1]
        aucs.append(roc_auc_score(yt, prob))
    assert abs(np.mean(aucs) - .5) < .06


@pytest.mark.parametrize(("delta", "melhorou"), [
    ((.05, .0, -.02), True),
    ((.049, .1, .01), False),
    ((.051, -.001, .0), False),
    ((.06, .1, -.021), False),
])
def test_veredito_usa_delta_central(delta, melhorou):
    assert ml18.melhorou(dict(zip(ml18.CRITERIO, delta))) is melhorou


def test_bootstrap_conserva_noites_e_pareamento():
    y = np.tile([0, 1], 6)
    pessoas = np.repeat(["a", "b", "c"], 4)
    prob = np.tile([.1, .9], 6)
    ic = ml18.bootstrap_epocas(y, prob, prob, pessoas, 0, repeticoes=20)
    assert np.array_equal(ic, np.zeros((20, len(ml18.METRICAS))))
    assert ml18.resumir(y, prob, np.repeat(np.arange(6), 2))["por_noite"]["noites"] == 6


def test_auc_ponderada_equivale_a_repetir_as_pessoas_inteiras():
    y = np.array([0, 1, 0, 1, 0, 1])
    prob = np.array([.2, .7, .7, .8, .4, .4])
    pessoas = np.repeat(np.arange(3), 2)
    pesos = np.array([[1, 1, 1], [2, 0, 1], [0, 1, 2]])
    esperado = [
        roc_auc_score(np.repeat(y, w[pessoas]), np.repeat(prob, w[pessoas]))
        for w in pesos
    ]
    np.testing.assert_allclose(ml18.auc_ponderada(y, prob, pessoas, pesos), esperado)


def test_gravacoes_de_uma_pessoa_contam_como_noites_distintas():
    dados = {
        "id": np.repeat(["a", "b"], [4, 2]),
        "gravacao": np.repeat(["g1", "g2", "g1"], 2),
    }
    assert ml18.noite_ids(dados).tolist() == [0, 0, 1, 1, 2, 2]
