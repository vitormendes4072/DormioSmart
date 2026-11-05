"""Controles independentes da reconstrução por sujeito usada na ML-15."""
import json

import numpy as np
import pytest

from ferramentas.reconstruir_f1 import derivar, matriz, resumo
from src.avaliar import avaliar_epoca


def test_reconstroi_classificacoes_conhecidas():
    y = np.array([1, 1, 1, 0, 0])
    p = np.array([1, 1, 0, 1, 0])
    m = avaliar_epoca(y, p)
    assert matriz(m.acuracia, m.especificidade, m.kappa, 3, 2) == (2, 1, 1, 1)
    with pytest.raises(ValueError, match='kappa'):
        matriz(m.acuracia, m.especificidade, m.kappa + 0.1, 3, 2)
    with pytest.raises(ValueError, match='acurácia'):
        matriz(m.acuracia + 0.01, m.especificidade, m.kappa, 3, 2)


def test_zero_perdido_muda_media_e_intervalo():
    no = {'sujeitos': ['a', 'b'], 'n_bootstrap': 2000,
          'por_sujeito': {'acuracia': [0.5, 1.0], 'especificidade': [0.0, 1.0], 'kappa': [0.0, 1.0]}}
    r = derivar(no, {'a': (1, 1), 'b': (1, 1)}, seed=20260910)
    f = r['avaliacao']['f1_vigilia']
    assert f['zeros_antes_excluidos'] == 1
    assert f['formula_antiga_mesmas_classificacoes']['media'] == 1.0
    assert f['formula_corrigida']['media'] == 0.5
    assert f['formula_corrigida']['n_valido'] == 2
    assert f['formula_corrigida']['ic95'] == [0.0, 1.0]
    assert f['formula_corrigida']['desvio_padrao'] == pytest.approx(2**-0.5)
    json.dumps(r, allow_nan=False)


def test_ausencia_legitima_e_limites_inteiros():
    assert matriz(1.0, float('nan'), float('nan'), 3, 0) == (3, 0, 0, 0)
    assert resumo([float('nan')], 1, 2000)['media'] is None
    with pytest.raises(ValueError, match='suporte'):
        matriz(1, 0, 0, 0, 0)
    with pytest.raises(ValueError, match='fora do suporte'):
        matriz(0, 1, 0, 1, 1)


def test_recusa_coorte_ou_vetor_incompleto():
    no = {'sujeitos': ['a'], 'n_bootstrap': 2000,
          'por_sujeito': {'acuracia': [1], 'especificidade': [1], 'kappa': []}}
    with pytest.raises(ValueError, match='coorte'):
        derivar(no, {}, 1)
    with pytest.raises(ValueError, match='quantidade'):
        derivar(no, {'a': (1, 1)}, 1)
