"""Exercita consumidores reais, além da primitiva de contexto."""
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from src.configuracao import carregar_config
from src.cache_temporal import segmentos_de
from src.epocas import empilhar_contexto


def test_ml04_usa_segmentos_no_treino_e_no_destino(monkeypatch, tmp_path):
    import experimentos.ml04_validacao_externa as e
    from experimentos.ml03b_ablacao import normalizar_por_sujeito
    b = dict(X=np.array([[1.], [3.], [10.], [80.], [100.], [900.]]),
             y=np.array([0, 1, 0, 1, 0, 1]), id=np.array(['a']*3 + ['b']*3),
             gravacao=np.array(['n1']*3 + ['n2']*3), indice_epoca=np.array([0, 1, 5, 0, 1, 5]))
    seg = segmentos_de(b)
    esperado = empilhar_contexto(normalizar_por_sujeito(b['X'], b['id']), 11, segmentos=seg)
    class Clf:
        def __init__(self, **kw): pass
        def fit(self, X, y):
            np.testing.assert_array_equal(X, esperado)
            return self
        def predict(self, X):
            np.testing.assert_array_equal(X, esperado)
            return b['y']
    met = SimpleNamespace(media={k: .5 for k in e.METRICAS},
                          ic95_baixo={k: 0. for k in e.METRICAS},
                          ic95_alto={k: 1. for k in e.METRICAS}, dict=lambda: {})
    monkeypatch.setattr(e, 'LogisticRegression', Clf)
    monkeypatch.setattr(e, 'sujeitos_com_posicoes', lambda *a, **kw: ['a', 'b'])
    monkeypatch.setattr(e, '_base_wearanize', lambda *a: {'pulso': b})
    monkeypatch.setattr(e, 'carregar_features_newcastle', lambda *a: (b['X'], b['y'], b['id'], seg))
    monkeypatch.setattr(e, 'avaliar_por_sujeito', lambda *a, **kw: met)
    monkeypatch.setattr(e, '_trivial', lambda *a: met)
    monkeypatch.setattr(e, 'NOMES_BRACOS', ['pulso'])
    monkeypatch.setattr(e, 'CONFIGS', {'teste': dict(contexto=11, hmm=False)})
    # RAIZ só interfere na mensagem final, não nos dados deste teste.
    monkeypatch.setattr(e, 'RAIZ', tmp_path)
    e.rodar(carregar_config(), 20260910, 'esquerdo', tmp_path / 'resultado.json')


def test_ml04_cache_preserva_indice_apos_filtro(monkeypatch, tmp_path):
    import experimentos.ml04_validacao_externa as e
    import src.carregar.newcastle as n
    from src.carregar.base import Gravacao
    cfg = replace(carregar_config(), taxa_comum_hz=2.)
    gr = Gravacao('artificial', np.arange(180)/2, np.ones((180, 3)),
                  np.array([0, -1, 1]), 0., meta={'arquivo': 'artificial_left.bin'})
    def carregar(**kw):
        assert kw['aceitar'](Path('artificial_left.bin'), gr.id_sujeito)
        yield gr
    monkeypatch.setattr(n, 'carregar_newcastle', carregar)
    monkeypatch.setattr(e, 'PASTA_FEATURES', tmp_path)
    monkeypatch.setattr(e, 'reamostrar', lambda t, a, *args: (t, a))
    monkeypatch.setattr(e, 'features_de_epoca', lambda a, **kw: (np.arange(3.)[:, None], ['x']))
    assert e.preparar(cfg, 100, 'esquerdo')[0] == 1
    X, y, ids, segmentos = e.carregar_features_newcastle(cfg, 'esquerdo')
    np.testing.assert_array_equal(X[:, 0], [0., 2.])
    assert segmentos[0] != segmentos[1]


def test_retomada_entrega_segmentos_a_dobra(tmp_path):
    from experimentos._retomada import loso_com_retomada
    X = np.arange(6.)[:, None]
    ids = np.array(['a']*3 + ['b']*3)
    seg = np.array([0, 0, 1, 2, 2, 3])
    def prever(Xtr, ytr, Xte, idtr, seed, *, segmentos_tr, segmentos_te):
        np.testing.assert_array_equal(segmentos_tr, seg[Xtr[:, 0].astype(int)])
        np.testing.assert_array_equal(segmentos_te, seg[Xte[:, 0].astype(int)])
        return np.zeros(len(Xte), int)
    assert loso_com_retomada('teste', X, np.zeros(6, int), ids, prever, 1,
                            segmentos=seg, pasta=tmp_path)[1]
