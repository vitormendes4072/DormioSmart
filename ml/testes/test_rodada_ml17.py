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
@pytest.mark.parametrize('realocado', [False, True])
def test_guarda_execucao_acusa_mutacao(tmp_path, alvo, realocado):
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
    if realocado:
        manifesto.update(cache='LOCAL_ANTIGO/cache', censo='LOCAL_ANTIGO/censo.json')
    (tmp_path/'manifesto.json').write_text(json.dumps(manifesto))
    from ferramentas.resumir_ml17 import conferir_evidencia
    executar = (lambda: conferir_evidencia(tmp_path, cache, censo)) if realocado else lambda: conferir(tmp_path)
    assert executar() == (dict(manifesto, cache=str(cache), censo=str(censo)) if realocado else manifesto)
    {'fonte': fonte, 'cache': arq, 'censo': censo}[alvo].write_bytes(b'mudou')
    with pytest.raises(ValueError, match='mudou'):
        executar()


def test_realocacao_exige_os_dois_caminhos(tmp_path):
    from ferramentas.resumir_ml17 import conferir_evidencia
    with pytest.raises(ValueError, match='juntos'):
        conferir_evidencia(tmp_path, cache=tmp_path)


def test_executor_realocado_aceita_so_diferenca_crlf(monkeypatch, tmp_path):
    import hashlib
    import ferramentas.rodar_ml17 as r
    from ferramentas.resumir_ml17 import conferir_evidencia
    executor = tmp_path / 'executor.py'
    executor.write_bytes(b'x = 1\r\n')
    monkeypatch.setattr(r, '__file__', str(executor))
    censo = tmp_path / 'censo.json'
    censo.write_bytes(b'censo')
    m = dict(censo_sha256=sha(censo), executor_sha256=hashlib.sha256(b'x = 1\n').hexdigest(),
             fontes={}, cache_sha256={})
    (tmp_path / 'manifesto.json').write_text(json.dumps(m))
    assert conferir_evidencia(tmp_path, tmp_path, censo)['censo'] == str(censo)
    executor.write_bytes(b'x = 2\r\n')
    with pytest.raises(ValueError, match='executor mudou'):
        conferir_evidencia(tmp_path, tmp_path, censo)


@pytest.mark.parametrize('chave,valor', [('por_participante', [.2, .5]),
                                       ('indice_max_abs', 1), ('outro_vetor', [.2, .5])])
def test_controle_notas_individuais_na_publicacao_reprova(chave, valor):
    from ferramentas.resumir_ml17 import validar_sem_notas
    validar_sem_notas({'delta': {'media': .2, 'max_abs': .8, 'ic95': [.1, .3]}})
    with pytest.raises(ValueError):
        validar_sem_notas({'delta': {chave: valor}})


def test_auditoria_local_recompoe_e_acusa_media_adulterada():
    from copy import deepcopy
    from ferramentas.auditar_resumos_ml17 import conferir_notas
    from ferramentas.resumir_ml17 import comparacao_publica, validar_sem_notas
    m = dict(sujeitos=['a', 'b'], por_sujeito={'kappa': [.2, .4]}, media={'kappa': .3},
             desvio_padrao={'kappa': 2**.5/10}, n_valido={'kappa': 2},
             ic95_baixo={'kappa': .2}, ic95_alto={'kappa': .4})
    dados = {str(i): comparar_celula(m, m) for i in range(69)}
    assert conferir_notas(dados) == 69
    validar_sem_notas(comparacao_publica(dados))
    with pytest.raises(ValueError, match='individual'):
        validar_sem_notas(dados)  # A saída anterior, com vetores, é recusada.
    adulterado = deepcopy(dados)
    adulterado['0']['kappa']['antes'] += .1
    with pytest.raises(ValueError, match='estatística'):
        conferir_notas(adulterado)


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


def test_limite_angular_legado_e_explicito_e_nao_aceita_outros_desvios():
    import numpy as np
    from ferramentas.censo_contexto_ml17 import conferir_entrada
    a = dict(X=np.zeros((2, 8)), y=np.array([0, 1]), id=np.array(['a', 'a']))
    b = {**a, 'X': a['X'].copy()}
    b['X'][0, 6] = 1e-14
    with pytest.raises(ValueError, match='difere em X'):
        conferir_entrada(a, b)
    assert conferir_entrada(a, b, 3e-14) is None
    b['X'][0, 0] = 1e-15
    with pytest.raises(ValueError, match='difere em X'):
        conferir_entrada(a, b, 3e-14)
    b['X'][0, 0] = 0
    b['X'][0, 6] = 4e-14
    with pytest.raises(ValueError, match='difere em X'):
        conferir_entrada(a, b, 3e-14)
    with pytest.raises(ValueError, match='limite angular'):
        conferir_entrada(a, b, 1e-10)


def test_alinhamento_f1_recusa_captura_de_outra_celula():
    from ferramentas.comparar_ml17 import f1_da_captura
    metrica = {'media': {'kappa': .5}}
    c = dict(metricas=metrica, f1={'media': {'f1_vigilia': .2}})
    assert f1_da_captura(c, metrica) == c['f1']
    with pytest.raises(ValueError, match='não corresponde'):
        f1_da_captura(c, {'media': {'kappa': .6}})


def test_repeticao_conta_predicao_adulterada(tmp_path):
    import numpy as np
    from ferramentas.conferir_predicoes_ml17 import conferir_repeticao
    dados = dict(y=np.array([0, 1]), p=np.array([0, 1]), ids=np.array(['a', 'a']))
    for v in ('antes', 'depois'):
        p = tmp_path / v / 'ml/experimentos/saida/ml17_rodada'
        p.mkdir(parents=True)
        for i in range(12):
            np.savez(p / f'newcastle_pred_{i+1:02d}.npz', **dados)
            np.savez(p / f'lados_pred_{2*i:02d}.npz', **dados)
    assert conferir_repeticao(tmp_path)['predicoes_diferentes'] == 0
    np.savez(tmp_path / 'depois/ml/experimentos/saida/ml17_rodada/lados_pred_00.npz',
             **{**dados, 'p': np.array([1, 1])})
    assert conferir_repeticao(tmp_path)['predicoes_diferentes'] == 1


def test_resumo_ambiente_nao_publica_caminho_local():
    from ferramentas.resumir_ml17 import ambiente_publico
    e = dict(python='3.11', bibliotecas={'numpy': '2.2.6'},
             pools=[dict(num_threads=1, internal_api='openblas', filepath='CAMINHO_PRIVADO_NAO_PUBLICAR')])
    r = ambiente_publico(e)
    assert 'CAMINHO_PRIVADO_NAO_PUBLICAR' not in json.dumps(r)
    assert r['pools'][0]['num_threads'] == 1
