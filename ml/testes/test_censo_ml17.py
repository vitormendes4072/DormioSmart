import numpy as np
import pytest

from ferramentas.censo_contexto_ml17 import contar, conferir_entrada


def test_censo_conta_epocas_nao_celulas_e_confere_identidade():
    b = dict(X=np.arange(8.).reshape(4, 2), y=np.array([0, 1, 0, 1]),
             id=np.array(['a']*4), gravacao=np.array(['n']*4), indice_epoca=np.array([0, 1, 5, 6]))
    assert conferir_entrada(b, b) is None
    for janela in (2, 11):
        r = contar(b, janela)
        assert r['n_epocas'] == r['vizinhanca_alterada'] == r['vetor_alterado'] == 4
        assert r['n_segmentos'] == 2
        assert r['maior_por_sujeito'] == 4
    assert contar(b, 0)['vetor_alterado'] == 0
    with pytest.raises(ValueError, match='difere em y'):
        conferir_entrada(b, dict(b, y=1-b['y']))
