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
    vazado = ajustar(np.vstack((x, pulso)), np.r_[y, y_pulso], ml18.SEED_MODELO)
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
    assert roc_auc_score(y, ajustar(x, y, ml18.SEED_MODELO).predict_proba(x)[:, 1]) > .95
    aucs = []
    for i in range(20):
        permutado = ml18.embaralhar(grupos, divisao=0, rodada=i)
        for a, b in zip(grupos, np.array_split(permutado, 2)):
            assert np.array_equal(np.bincount(a), np.bincount(b))
        prob = ajustar(x, permutado, ml18.SEED_MODELO).predict_proba(x)[:, 1]
        aucs.append(roc_auc_score(y, prob))
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

