from types import SimpleNamespace

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
    ids_cabeca = ml18.identidades("wearanize/cabeca", {"id": np.array(["1", "2"])})
    ids_pulso = ml18.identidades("wearanize/pulso", {"id": np.array(["1"])})
    with pytest.raises(ValueError, match="participante"):
        ml18.conferir_separacao(ids_cabeca, ids_pulso)
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


@pytest.mark.parametrize("base", ["wearanize/cabeca", "wearanize/pulso"])
def test_referencia_loso_exclui_a_pessoa_avaliada(base):
    # Cada pessoa tem uma assinatura diferente para separar sono e vigília.
    cabeca = {"id": np.repeat(["a", "b"], 2), "y": np.tile([0, 1], 2)}
    x_cabeca = np.array([[-1, 0], [1, 0], [0, -1], [0, 1]], dtype=float)
    x = x_cabeca if base == "wearanize/cabeca" else x_cabeca * .7
    ref = ml18.prever_referencia(base, {"id": cabeca["id"]}, x, None, cabeca, x_cabeca)
    np.testing.assert_allclose(ref, np.full(4, .5))


def test_classes_classifica_empate_como_vigilia():
    prob = np.array([np.nextafter(.5, 0), .5, np.nextafter(.5, 1)])
    assert ml18.classes(prob).tolist() == [0, 0, 1]


def test_execucao_calcula_media_e_intervalo_so_das_tres_externas(monkeypatch, tmp_path):
    modelo = tmp_path / "modelo.json"
    modelo.write_text("{}", encoding="utf-8")
    saida = tmp_path / "experimentos/saida/ml13"
    saida.mkdir(parents=True)
    (saida / "agregados.json").write_text(
        '{"sha256_manifesto_dreamt": "hash", "qualidade": {}}', encoding="utf-8",
    )
    monkeypatch.setattr(ml18, "ML", tmp_path)
    monkeypatch.setattr(ml18, "MODELO", modelo)
    monkeypatch.setattr(ml18, "sha256", lambda _: "hash")
    monkeypatch.setattr(ml18.subprocess, "check_output", lambda *args, **kwargs: "commit")
    cfg = SimpleNamespace(hash="aec203907e6f", seed=ml18.SEED_MODELO, taxa_comum_hz=32, epoca_s=30)
    monkeypatch.setattr(ml18, "carregar_config", lambda: cfg)
    deltas = {
        "wearanize/cabeca": (-.5, -.5, -.5),
        "wearanize/pulso": (-.5, -.5, -.5),
        "walch_principal": (.04, .01, -.02),
        "dreamt": (.06, .02, .01),
        "newcastle": (.08, .03, -.02),
    }
    monkeypatch.setattr(ml18, "dados_ml17", lambda *args, **kwargs: (dict.fromkeys(deltas), None))
    monkeypatch.setattr(ml18, "carregar_features_dreamt", lambda *_: (None, {}, None))
    monkeypatch.setattr(ml18, "preparar_historico", lambda _: (None,))

    def comparar(base, *_):
        delta = deltas[base]
        return {"delta_por_epoca": dict(zip(ml18.CRITERIO, delta))}, np.tile(delta, (2, 1))

    monkeypatch.setattr(ml18, "comparar", comparar)
    media = ml18.executar(tmp_path, tmp_path)["media_externa"]
    assert media["bases"] == ["walch_principal", "dreamt", "newcastle"]
    assert media["melhorou"]
    assert media["delta"] == pytest.approx({"especificidade": .06, "kappa": .02, "sensibilidade": -.01})
    for metrica, esperado in {"especificidade": .06, "kappa": .02, "sensibilidade": -.01}.items():
        assert media["ic_delta"][metrica]["ic95"] == pytest.approx([esperado, esperado])


def test_bootstrap_subtrai_a_referencia_do_conjunto():
    y = np.tile([0, 1], 3)
    pessoas = np.repeat(["a", "b", "c"], 2)
    conjunto = np.tile([.1, .9], 3)
    delta = ml18.bootstrap_epocas(y, 1 - conjunto, conjunto, pessoas, 0, repeticoes=20)
    np.testing.assert_allclose(delta, np.tile([1, 2, 1, 1, 1], (20, 1)))


def test_bootstrap_reamostra_a_pessoa_inteira():
    # Sorteiam-se duas pessoas. A primeira tem uma noite e a segunda tem três.
    # Só na primeira o conjunto corrige a classificação da vigília.
    y = np.tile([0, 1], 4)
    pessoas = np.repeat(["a", "b"], [2, 6])
    ref = np.full(8, .9)
    conjunto = ref.copy()
    conjunto[0] = .1
    delta = ml18.bootstrap_epocas(y, ref, conjunto, pessoas, 0, repeticoes=64)
    assert set(delta[:, 0]) == {0, .25, 1}


def test_delta_noturno_subtrai_a_referencia_do_conjunto():
    ref = dict(vies_tst_min=-20, fracao_erro_acima_60_min=.25,
               correlacao_vigilia_entre_noites=.75, limites_95_min=[-70, 30])
    conjunto = dict(vies_tst_min=-50, fracao_erro_acima_60_min=.50,
                    correlacao_vigilia_entre_noites=.50, limites_95_min=[-110, 10])
    assert ml18.delta_noite(ref, conjunto) == {
        "vies_tst_min": -30, "fracao_erro_acima_60_min": .25,
        "correlacao_vigilia_entre_noites": -.25, "limites_95_min": [-40, -20],
    }
