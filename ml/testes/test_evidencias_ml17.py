"""Contrato/hashes públicos; recompor médias exige notas locais, fora do Git."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from ferramentas.resumir_ml17 import ARQUIVOS, validar_sem_notas

PASTA = Path(__file__).resolve().parents[1] / 'experimentos/saida/ml17'


def verificar(pasta):
    assert {p.name for p in pasta.iterdir()} == set(ARQUIVOS) | {'manifesto.json'}
    m = json.loads((pasta / 'manifesto.json').read_text(encoding='utf-8'))
    validar_sem_notas(m)
    assert set(m['arquivos_publicos_sha256_utf8_lf']) == set(ARQUIVOS)
    for nome in ARQUIVOS:
        b = (pasta / nome).read_bytes()
        assert hashlib.sha256(b.replace(b'\r\n', b'\n')).hexdigest() == m['arquivos_publicos_sha256_utf8_lf'][nome], nome
        d = json.loads(b)
        validar_sem_notas(d)
        if nome in ('comparacao.json', 'f1_complementar.json'):
            assert len(d) == 69
            for metricas in d.values():
                for metrica in metricas.values():
                    assert set(metrica) == {'antes', 'depois', 'resumo_antes', 'resumo_depois', 'delta'}
                    assert metrica['delta']['n_pares'] <= metrica['delta']['n_total']
    return m


def test_resumos_publicados_so_agregados_hashes_e_fontes_historicas():
    m = verificar(PASTA)
    from ferramentas.comparar_reproducao import conferir_fontes_historicas
    assert conferir_fontes_historicas(PASTA.parents[2], dict(base_codigo=m['analise_commit'],
        fontes={'ferramentas/' + n: sha for n, sha in m['fontes_analise_sha256_utf8_lf'].items()}))
    assert conferir_fontes_historicas(PASTA.parents[2], dict(base_codigo=m['executor_commit'],
        fontes={'ferramentas/rodar_ml17.py': m['executor_sha256_utf8_lf']}))


def test_controle_media_publicada_adulterada_reprova(tmp_path):
    # Pequenos JSONs públicos, sem junction, dataset ou pasta de execução.
    for p in PASTA.iterdir():
        (tmp_path / p.name).write_bytes(p.read_bytes())
    p = tmp_path / 'comparacao.json'
    d = deepcopy(json.loads(p.read_text(encoding='utf-8')))
    next(iter(d.values()))['kappa']['delta']['media'] += .1
    p.write_text(json.dumps(d), encoding='utf-8')
    with pytest.raises(AssertionError, match='comparacao.json'):
        verificar(tmp_path)
