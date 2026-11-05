"""A auditoria usa referências externas à rodada e acusa sabotagens."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from ferramentas.auditar_ml16 import PADRAO, auditar
from ferramentas.comparar_reproducao import hash_texto


def test_evidencias_reproduzem_os_sete_registros_e_controles():
    r = auditar()
    assert r['concluido'] and len(r['casos']) == 7
    assert all(c['reproduzido'] for c in r['casos'])
    assert {c['n_diferencas_fora_f1'] for c in r['controles_features']} == {10, 13}
    assert len(r['controle_threads']) == 6
    assert set(r['n_sujeitos_por_celula'].values()) == {92}
    assert json.loads((PADRAO / 'comparacao.json').read_text(encoding='utf-8')) == r
    m = json.loads((PADRAO / 'manifesto.json').read_text(encoding='utf-8'))
    instrumento = Path(__file__).resolve().parents[1] / 'ferramentas/rastrear_ml16.py'
    assert all(v['instrumento_sha256_utf8_lf'] == hash_texto(instrumento)
               for v in m['execucoes_baseline'].values())
    assert all(all(p['num_threads'] == 1 for p in v['ambiente_numerico'])
               for v in m['execucoes_baseline'].values())


@pytest.mark.parametrize('defeito', ['metrica', 'f1_nan', 'threads', 'referencia_autodeclarada'])
def test_auditoria_recusa_sabotagem_nos_resultados(tmp_path, defeito):
    pasta = tmp_path / 'evidencias'
    shutil.copytree(PADRAO, pasta)
    nome = 'controle_threads.json' if defeito == 'referencia_autodeclarada' else 'resultados/' + (
        'sem_scaler_8_threads.json' if defeito == 'threads' else 'piloto_cabeca.json')
    p = pasta / nome
    d = json.loads(p.read_text(encoding='utf-8'))
    if defeito == 'metrica':
        d['resultados']['2_regressao_logistica_loso']['acuracia'] += 0.01
    elif defeito == 'f1_nan':
        d['resultados']['0_sempre_dormindo']['f1_vigilia'] = float('nan')
    elif defeito == 'threads':
        d['threads'] = 1
    else:
        d[0]['testes']['cabeca']['acuracia']['atual'] = 0.5
        d[0]['testes']['cabeca']['acuracia']['ml15'] = 0.5
    p.write_text(json.dumps(d), encoding='utf-8')
    assert not auditar(pasta)['concluido']


def test_cli_acusa_mudanca_da_fonte_mesmo_se_metrica_igual(tmp_path):
    pasta = tmp_path / 'evidencias'
    shutil.copytree(PADRAO, pasta)
    script = Path(__file__).resolve().parents[1] / 'ferramentas/auditar_ml16.py'
    cmd = [sys.executable, str(script), '--pasta', str(pasta), '--conferir']
    assert subprocess.run(cmd, capture_output=True).returncode == 0
    p = pasta / 'resultados/piloto_cabeca.json'
    d = json.loads(p.read_text(encoding='utf-8'))
    d['utc'] = 'tempo alterado deliberadamente'
    p.write_text(json.dumps(d), encoding='utf-8')
    assert auditar(pasta)['concluido']  # Os números continuam corretos.
    assert subprocess.run(cmd, capture_output=True).returncode == 1  # A origem mudou.
