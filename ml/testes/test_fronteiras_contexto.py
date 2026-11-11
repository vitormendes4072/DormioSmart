"""Defeitos de janela e proteções já satisfeitas pelo HMM do develop."""
from dataclasses import replace

import numpy as np
import pytest

from experimentos.ml03b_ablacao import montar_X
from experimentos.ml04_validacao_externa import _prever
from src.carregar import processar_gravacoes
from src.carregar.base import Gravacao
from src.configuracao import carregar_config
from src.epocas import empilhar_contexto
from src.modelos import suavizar_hmm, transicoes_hmm


@pytest.mark.parametrize("janela", [2, 11])
def test_defeito_janela_nao_atravessa_participantes(janela):
    X = np.array([[1.], [2.], [100.], [200.]])
    b = dict(X=X, y=np.array([0, 1, 0, 1]), id=np.array(['a', 'a', 'b', 'b']),
             gravacao=np.array(['a1', 'a1', 'b1', 'b1']), indice_epoca=np.array([0, 1, 0, 1]))
    esperado = np.vstack([empilhar_contexto(X[:2], janela), empilhar_contexto(X[2:], janela)])
    np.testing.assert_array_equal(montar_X({'pulso': b}, 'pulso', janela), esperado)


@pytest.mark.parametrize("janela", [2, 11])
def test_defeito_lacuna_nao_encosta_epocas_filtradas(monkeypatch, janela):
    import src.carregar as c
    cfg = replace(carregar_config(), taxa_comum_hz=2., contexto_epocas=janela)
    t = np.arange(180) / 2
    a = np.repeat(np.array([1., 50., 100.]), 60)[:, None] * np.ones((1, 3))
    gr = Gravacao('a', t, a, np.array([0, -1, 1]), 0.)
    monkeypatch.setattr(c, 'reamostrar', lambda t, a, *args, **kw: (t, a))
    monkeypatch.setattr(c, 'features_de_epoca', lambda a, **kw: (a[:, 0, :1], ['artificial']))
    resultado = processar_gravacoes([gr], cfg)
    np.testing.assert_array_equal(resultado.X[0], np.repeat(1., 2 * janela + 1))
    np.testing.assert_array_equal(resultado.X[1], np.repeat(100., 2 * janela + 1))


def test_regressao_hmm_transicoes_ja_separam_participantes():
    # Não existem transições 0->1: há duas pessoas constantes diferentes.
    A, _ = transicoes_hmm(np.array([0, 0, 1, 1]), np.array(['a', 'a', 'b', 'b']))
    np.testing.assert_allclose(A, [[2/3, 1/3], [1/3, 2/3]])


def test_regressao_ml04_viterbi_ja_separa_participantes():
    class Clf:
        def predict_proba(self, X):
            return np.column_stack([1-X[:, 0], X[:, 0]])
    X = np.array([[.1], [.2], [.8], [.9]])
    ids = np.array(['a', 'a', 'b', 'b'])
    A = np.array([[.99, .01], [.01, .99]])
    esperado = np.r_[suavizar_hmm(X[:2, 0], A), suavizar_hmm(X[2:, 0], A)]
    np.testing.assert_array_equal(_prever(Clf(), X, np.zeros(4, int), ids, True, A), esperado)
