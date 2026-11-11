"""Controles do instrumento: alterações deliberadas devem aparecer no relatório."""
import json
from pathlib import Path
import subprocess
import sys
import pytest

from ferramentas.comparar_reproducao import comparar, comparar_pastas, hash_texto, conferir_fontes_historicas


def test_guarda_historica_acusa_adulteracao_e_historico_ausente():
    ml = Path(__file__).resolve().parents[1]
    original = json.loads((ml / 'experimentos/saida/ml15/manifesto.json').read_text(encoding='utf-8'))
    assert conferir_fontes_historicas(ml, original)
    adulterado = dict(original, fontes={'src/epocas.py': '0' * 64})
    with pytest.raises(ValueError, match='adulterada/divergente'):
        conferir_fontes_historicas(ml, adulterado)
    with pytest.raises(ValueError, match='indisponível'):
        conferir_fontes_historicas(ml, dict(original, base_codigo='0' * 40))
    with pytest.raises(ValueError, match='inválida/vazia'):
        conferir_fontes_historicas(ml, dict(original, fontes={}))


def test_igualdade_tolerancia_e_nan():
    assert comparar({'a': [0.5, float('nan')]}, {'a': [0.5+1e-12, float('nan')]}) == []
    assert comparar({'kappa': 0.5}, {'kappa': 0.6})[0]['caminho'] == '$.kappa'


def test_f1_nan_para_zero_pode_ser_serializado():
    d = comparar({'f1_vigilia': float('nan')}, {'f1_vigilia': 0.0})
    assert d[0]['antes_nan'] and d[0]['depois'] == 0.0
    json.dumps(d, allow_nan=False)


def test_listas_campos_removidos_e_adicionados():
    d = comparar({'v': [1, 2], 'removido': 1}, {'v': [1, 3, 4], 'novo': 1})
    assert {v['tipo'] for v in d} == {'campo_novo', 'campo_ausente', 'tamanho'}
    assert comparar([1, 2], [1, 3])[0]['caminho'] == '$[1]'


def test_tempo_ignorado_e_hash_independente_de_crlf(tmp_path):
    assert comparar({'utc': 'ontem', 'segundos': 4}, {'utc': 'hoje', 'segundos': 9}) == []
    a, b = tmp_path / 'a', tmp_path / 'b'
    a.write_bytes(b'a\r\nb\r\n')
    b.write_bytes(b'a\nb\n')
    assert hash_texto(a) == hash_texto(b)


def test_coorte_distinta_e_parcial_excluido(tmp_path):
    refs, novos = tmp_path / 'refs', tmp_path / 'novos'
    refs.mkdir()
    novos.mkdir()
    nome = 'ml02_teste_hash_20260914T052628Z.json'
    (refs / nome).write_text(json.dumps({'n_sujeitos': 10, 'f1_vigilia': float('nan'), 'parcial': True}), encoding='utf-8')
    novo = novos / nome.replace('20260914', '20261105')
    novo.write_text(json.dumps({'n_sujeitos': 92, 'f1_vigilia': 0.0}), encoding='utf-8')
    r = comparar_pastas(refs, novos)
    assert len(r) == 1 and not r[0]['coorte_metadados_compativeis']
    assert r[0]['referencia_parcial']
    assert r[0]['n_diferencas_f1'] == r[0]['n_outras_diferencas'] == 1
    novo.write_text('{"parcial": true}', encoding='utf-8')
    assert comparar_pastas(refs, novos) == []


def test_cli_acusa_sabotagem_e_nao_confere_no_vazio(tmp_path):
    refs, novos = tmp_path / 'refs', tmp_path / 'novos'
    refs.mkdir()
    novos.mkdir()
    for pasta in (refs, novos):
        (pasta / 'resultado.json').write_text('{"kappa": 0.5}', encoding='utf-8')
    script = Path(__file__).resolve().parents[1] / 'ferramentas/comparar_reproducao.py'
    cmd = [sys.executable, str(script), '--referencias', str(refs), '--novos', str(novos),
           '--saida', str(tmp_path / 'comparacao.json')]
    assert subprocess.run(cmd, capture_output=True).returncode == 0
    assert subprocess.run(cmd + ['--conferir'], capture_output=True).returncode == 0
    (novos / 'resultado.json').write_text('{"kappa": 0.6}', encoding='utf-8')
    assert subprocess.run(cmd + ['--conferir'], capture_output=True).returncode == 1
    (novos / 'resultado.json').write_text('{"parcial": true}', encoding='utf-8')
    assert subprocess.run(cmd, capture_output=True).returncode == 2


def test_evidencias_publicadas_cobrem_a_rodada_completa():
    ml = Path(__file__).resolve().parents[1]
    rodada = ml / 'experimentos/saida/ml15'
    novos = rodada / 'resultados'
    arquivos = {p.name for p in novos.glob('*.json')}
    salvo = json.loads((rodada / 'comparacao.json').read_text(encoding='utf-8'))
    assert len(arquivos) == 15
    assert len(salvo) == 18
    assert {r['novo'] for r in salvo} == arquivos
    assert comparar_pastas(ml / 'experimentos/saida', novos) == salvo
    assert all(not json.loads(p.read_text(encoding='utf-8')).get('parcial') for p in novos.glob('*.json'))
    manifesto = json.loads((rodada / 'manifesto.json').read_text(encoding='utf-8'))
    assert conferir_fontes_historicas(ml, manifesto)
    f1 = json.loads((rodada / 'f1_complementar.json').read_text(encoding='utf-8'))
    assert len(f1) == 132
    assert sum(r['n_matrizes_verificadas'] for r in f1) == 9687
    assert all(hash_texto(novos / r['arquivo']) == r['sha256_utf8_lf'] for r in f1)


def test_executor_recusa_saida_historica_e_primeira_saida_preenchida(tmp_path):
    ml = Path(__file__).resolve().parents[1]
    script = ml / 'ferramentas/executar_reproducao.py'
    r = subprocess.run([sys.executable, str(script), '--pasta', str(ml.parent)], capture_output=True)
    assert r.returncode == 2 and b'prepare uma' in r.stderr
    copia = tmp_path / 'ml'
    (copia / 'src').mkdir(parents=True)
    (copia / 'src/avaliar.py').write_text('', encoding='utf-8')
    saida = copia / 'experimentos/saida'
    saida.mkdir(parents=True)
    historico = saida / 'referencia.json'
    historico.write_text('{"kappa": 0.5}', encoding='utf-8')
    antes = historico.read_bytes()
    r = subprocess.run([sys.executable, str(script), '--pasta', str(tmp_path)], capture_output=True)
    assert r.returncode == 2 and b'sem checkpoints antigos' in r.stderr
    assert historico.read_bytes() == antes
