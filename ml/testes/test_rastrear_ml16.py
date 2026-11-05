"""Controles das reconstruções históricas; nenhuma variante vira produção."""
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from ferramentas.rastrear_ml16 import selecionar_piloto, variantes_features


def test_piloto_segue_ordem_canonica_e_nao_ordem_das_pastas(tmp_path):
    ids = [f'sub-{i:03d}' for i in (5, 1, 4, 2, 7, 8, 9, 10, 11, 12, 13)]
    (tmp_path / 'participants.tsv').write_text('participant_id\tage\n' + '\n'.join(s + '\t99' for s in ids), encoding='utf-8')
    for s in ids:
        p = tmp_path / s / 'eeg'
        p.mkdir(parents=True)
        (p / f'{s}_task-sleep_eeg.edf').write_bytes(b'EDF')
    assert selecionar_piloto(tmp_path) == ids[:10]
    (tmp_path / ids[0] / 'eeg' / f'{ids[0]}_task-sleep_eeg.edf').unlink()
    with pytest.raises(ValueError, match='EDF ausente'):
        selecionar_piloto(tmp_path)


def test_l1_altera_so_coluna_da_magnitude_e_restaura_extrator():
    import experimentos.ml02_baselines as e
    import src.features as f
    original = e.features_de_epoca
    a = np.random.default_rng(5).normal(0, 0.1, (4, 128, 3)) + [0, 0, 1]
    referencia, _ = original(a, fs=32)
    with variantes_features(norma='l1'):
        historico, _ = e.features_de_epoca(a, fs=32)
        for i, ep in enumerate(a):
            esperado = np.abs(ep - f.estimar_gravidade(ep, 32)).sum(axis=1).mean()
            assert historico[i, 3] == pytest.approx(esperado)
        np.testing.assert_array_equal(historico[:, [0, 1, 2, 4, 5, 6, 7]], referencia[:, [0, 1, 2, 4, 5, 6, 7]])
        assert not np.allclose(historico[:, 3], referencia[:, 3])
    assert e.features_de_epoca is original


def test_mediana_unitaria_e_restauracao_mesmo_com_excecao():
    import src.features as f
    original = f.direcao_referencia
    g = np.array([[1., 0, 0], [3., 1, 0], [0, 0, 4], [1, 2, 3]])
    with pytest.raises(RuntimeError):
        with variantes_features(referencia='mediana-unitaria'):
            np.testing.assert_allclose(f.direcao_referencia(g), f.unitario(np.median(f.unitario(g), axis=0)))
            raise RuntimeError('controle de restauração')
    assert f.direcao_referencia is original
    with pytest.raises(ValueError, match='desconhecida'):
        with variantes_features(norma='inventada'):
            pass


def test_cli_recusa_sobrescrever_e_rejeita_variante_fora_do_sintetico(tmp_path):
    script = Path(__file__).resolve().parents[1] / 'ferramentas/rastrear_ml16.py'
    cmd = [sys.executable, str(script), '--modo', 'sintetico', '--threads', '1', '--saida', str(tmp_path)]
    r = subprocess.run(cmd, capture_output=True)
    assert r.returncode == 2 and b'pasta de sa' in r.stderr
    r = subprocess.run([sys.executable, str(script), '--modo', 'sem-scaler', '--threads', '8', '--norma', 'l1', '--saida', str(tmp_path / 'nova')], capture_output=True)
    assert r.returncode == 2 and b'apenas para o controle' in r.stderr
    assert not (tmp_path / 'nova').exists()
