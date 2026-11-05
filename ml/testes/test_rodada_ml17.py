import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from ferramentas.rodar_ml17 import conferir, preparar, sha
from ferramentas.comparar_ml17 import delta, comparar_celula


def test_preparacao_recusa_censo_vazio_e_pasta_preenchida(tmp_path):
    censo = tmp_path / 'censo.json'
    censo.write_text('{}')
    args = SimpleNamespace(pasta=tmp_path/'execucao', censo=censo, cache=tmp_path)
    with pytest.raises(ValueError, match='incompleto ou vazio'):
        preparar(args)
    args.pasta.mkdir()
    marcador = args.pasta / 'nao_apagar'
    marcador.write_bytes(b'preservar')
    with pytest.raises(ValueError, match='já existe'):
        preparar(args)
    assert marcador.read_bytes() == b'preservar'


@pytest.mark.parametrize('alvo', ['fonte', 'cache', 'censo'])
def test_guarda_execucao_acusa_mutacao(tmp_path, alvo):
    import ferramentas.rodar_ml17 as r
    fonte = tmp_path / 'antes/ml/src/epocas.py'
    fonte.parent.mkdir(parents=True)
    fonte.write_bytes(b'fonte')
    censo = tmp_path / 'censo.json'
    censo.write_bytes(b'censo')
    cache = tmp_path / 'cache'
    cache.mkdir()
    arq = cache / 'dados.npz'
    arq.write_bytes(b'cache')
    manifesto = dict(censo=str(censo), censo_sha256=sha(censo), cache=str(cache),
                     executor_sha256=sha(r.__file__),
                     fontes={'antes': {'arquivos': {'ml/src/epocas.py': sha(fonte)}}},
                     cache_sha256={'dados.npz': sha(arq)})
    (tmp_path/'manifesto.json').write_text(json.dumps(manifesto))
    assert conferir(tmp_path) == manifesto
    {'fonte': fonte, 'cache': arq, 'censo': censo}[alvo].write_bytes(b'mudou')
    with pytest.raises(ValueError, match='mudou'):
        conferir(tmp_path)


def test_comparador_nao_esconde_extremos_na_media():
    d = delta([.5, .5, .5, float('nan')], [.67, .33, .5, float('nan')])
    assert d['media'] == pytest.approx(0)
    assert d['max_abs'] == pytest.approx(.17)
    assert d['minimo'] == pytest.approx(-.17)
    assert d['maximo'] == pytest.approx(.17)
    assert d['n_pares'] == 3 and d['n_invalidos_antes'] == 1
    with pytest.raises(ValueError, match='vazios'):
        delta([], [])
    m = dict(sujeitos=['a'], por_sujeito={'kappa': [.5]}, media={'kappa': .5})
    with pytest.raises(ValueError, match='ordem diferentes'):
        comparar_celula(m, dict(m, sujeitos=['b']))


def test_verificador_independente_falha_total_nao_vira_nan():
    import numpy as np
    from ferramentas.conferir_predicoes_ml17 import recalcular, conferir
    r = recalcular([0, 0, 1, 1], [1, 1, 0, 0], ['a']*4)
    assert r == dict(acuracia=[0.], especificidade=[0.], kappa=[-1.],
                     f1_vigilia=[0.], f1_sono=[0.])
    r = recalcular([1, 1], [1, 1], ['a', 'a'])
    assert np.isnan(r['f1_vigilia'][0])  # Classe ausente na verdade e predição.
    with pytest.raises(ValueError, match='vazias'):
        recalcular([], [], [])


def test_verificador_recusa_capturas_incompletas(tmp_path):
    from ferramentas.conferir_predicoes_ml17 import conferir
    with pytest.raises(ValueError, match='incompletas'):
        conferir(tmp_path)
