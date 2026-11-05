"""Executa os controles sobre as verificações reais da ML-17."""
import numpy as np
import pytest

import test_fronteiras_contexto as fronteiras
import test_cache_temporal as cache


def test_controle_reintroduzir_janela_global_e_detectado(monkeypatch):
    import experimentos.ml03b_ablacao as a
    real = a.empilhar_contexto
    monkeypatch.setattr(a, 'empilhar_contexto', lambda X, n, **kw: real(X, n))
    with pytest.raises(AssertionError):
        fronteiras.test_defeito_janela_nao_atravessa_participantes(11)


def test_controle_apagar_lacuna_e_detectado(monkeypatch):
    import src.carregar as c
    real = c.segmentos_epocas
    monkeypatch.setattr(c, 'segmentos_epocas', lambda ids, gr, idx: real(ids, gr, np.arange(len(idx))))
    with pytest.raises(AssertionError):
        fronteiras.test_defeito_lacuna_nao_encosta_epocas_filtradas(monkeypatch, 11)


def test_controle_permitir_cache_antigo_e_detectado(monkeypatch, tmp_path):
    monkeypatch.setattr(cache, 'ler_features', lambda p, cfg: {})
    with pytest.raises(pytest.fail.Exception, match='DID NOT RAISE'):
        cache.test_cache_antigo_sem_indices_nao_entra(tmp_path)


def test_controle_juntar_hmm_entre_participantes_e_detectado(monkeypatch):
    from src.modelos import transicoes_hmm
    monkeypatch.setattr(fronteiras, 'transicoes_hmm',
                        lambda y, ids: transicoes_hmm(y, np.repeat('um', len(y))))
    with pytest.raises(AssertionError):
        fronteiras.test_regressao_hmm_transicoes_ja_separam_participantes()


def test_controle_juntar_viterbi_entre_participantes_e_detectado(monkeypatch):
    from src.modelos import suavizar_hmm
    monkeypatch.setattr(fronteiras, '_prever', lambda clf, X, y, ids, hmm, A:
                        suavizar_hmm(clf.predict_proba(X)[:, 1], A))
    with pytest.raises(AssertionError):
        fronteiras.test_regressao_ml04_viterbi_ja_separa_participantes()
