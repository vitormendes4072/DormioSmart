"""Contrato de cache e segmentos sem dados clínicos."""
import json
import pickle

import numpy as np
import pytest

from src.cache_temporal import (ler_features, salvar_features, segmentos_de,
                               ler_base, salvar_base, caminho_base)
from src.configuracao import carregar_config
from src.epocas import segmentos_epocas, empilhar_contexto, aplicar_por_segmento
from src.modelos import transicoes_hmm, suavizar_hmm, suavizar_mediana


def exemplo():
    return dict(X=np.arange(8.).reshape(4, 2), y=np.array([0, 0, 1, 1]),
                id=np.array(['a'] * 4), gravacao=np.array(['noite'] * 4),
                indice_epoca=np.array([0, 1, 5, 6]))


def test_cache_temporal_roundtrip_e_fonte_adulterada(tmp_path):
    cfg = carregar_config()
    f = tmp_path / 'cache.npz'
    b = exemplo()
    salvar_features(f, cfg, **b)
    lido = ler_features(f, cfg)
    for k in b:
        np.testing.assert_array_equal(b[k], lido[k])
    with np.load(f) as d:
        v = dict(d)
    meta = json.loads(str(v['identidade']))
    meta['fontes']['src/epocas.py'] = '0' * 64
    v['identidade'] = json.dumps(meta)
    np.savez(f, **v)
    with pytest.raises(ValueError, match='incompatível'):
        ler_features(f, cfg)


def test_cache_antigo_sem_indices_nao_entra(tmp_path):
    cfg = carregar_config()
    f = tmp_path / 'antigo.npz'
    b = exemplo()
    del b['indice_epoca']
    np.savez(f, **b)
    with pytest.raises(ValueError, match='incompatível'):
        ler_features(f, cfg)
    with pytest.raises(ValueError, match='identidade temporal'):
        segmentos_de(b)


def test_cache_base_selecao_e_contrato(tmp_path):
    cfg = carregar_config()
    b = {'pulso': exemplo()}
    f = caminho_base(['a'], cfg, tmp_path)
    salvar_base(f, b, ['a'], cfg)
    np.testing.assert_array_equal(ler_base(f, ['a'], cfg)['pulso']['indice_epoca'], [0, 1, 5, 6])
    with pytest.raises(ValueError, match='incompatível'):
        ler_base(f, ['b'], cfg)
    f.write_bytes(pickle.dumps(b))
    with pytest.raises(ValueError, match='incompatível'):
        ler_base(f, ['a'], cfg)


def test_segmentos_nao_juntam_mesmo_id_apos_outra_gravacao():
    ids = np.array(['a', 'a', 'a', 'a', 'b', 'a'])
    g = np.array(['n1', 'n1', 'n2', 'n2', 'n1', 'n1'])
    np.testing.assert_array_equal(segmentos_epocas(ids, g, np.array([0, 1, 0, 4, 0, 2])),
                                  [0, 0, 1, 2, 3, 4])


@pytest.mark.parametrize('n', [0, 1, 2, 11])
def test_contexto_isolado_invariante_a_outros_segmentos(n):
    b = exemplo()
    seg = segmentos_de(b)
    isolado = empilhar_contexto(b['X'][:2], n)
    completo = empilhar_contexto(b['X'], n, segmentos=seg)
    np.testing.assert_array_equal(completo[:2], isolado)
    X = np.vstack([b['X'], [[999., 888.]]])
    outro = empilhar_contexto(X, n, segmentos=np.r_[seg, 2])
    np.testing.assert_array_equal(outro[:4], completo)


def test_segmento_vazio_unitario_e_metadados_invalidos():
    assert empilhar_contexto(np.empty((0, 2)), 11, segmentos=[]).shape == (0, 46)
    np.testing.assert_array_equal(empilhar_contexto([[2., 3.]], 2, segmentos=[0]),
                                  [[2., 3.] * 5])
    with pytest.raises(ValueError):
        segmentos_epocas(['a'], ['n'], np.array([.5]))
    with pytest.raises(ValueError):
        segmentos_epocas(['a'], [], np.array([0]))
    with pytest.raises(ValueError):
        empilhar_contexto([[1.]], 2, segmentos=[])


def test_lacuna_separa_transicoes_viterbi_e_mediana():
    b = exemplo()
    seg = segmentos_de(b)
    A, _ = transicoes_hmm(b['y'], b['id'], segmentos=seg)
    np.testing.assert_allclose(A, [[2/3, 1/3], [1/3, 2/3]])
    p = np.array([.01, .01, .99, .99])
    esperado = np.r_[suavizar_hmm(p[:2], A), suavizar_hmm(p[2:], A)]
    np.testing.assert_array_equal(aplicar_por_segmento(p, seg, lambda v: suavizar_hmm(v, A)), esperado)
    np.testing.assert_array_equal(aplicar_por_segmento(b['y'], seg, suavizar_mediana), b['y'])


def test_ml04_viterbi_respeita_lacuna_mesmo_participante():
    from experimentos.ml04_validacao_externa import _prever
    class Clf:
        def predict_proba(self, X):
            return np.c_[1-X[:, 0], X[:, 0]]
    b = exemplo()
    X = np.array([[.1], [.3], [.6], [.9]])
    A = np.array([[.99, .01], [.01, .99]])
    esperado = np.r_[suavizar_hmm(X[:2, 0], A), suavizar_hmm(X[2:, 0], A)]
    np.testing.assert_array_equal(_prever(Clf(), X, b['y'], b['id'], True, A,
                                         segmentos=segmentos_de(b)), esperado)
