"""Contrato da DREAMT com sinais artificiais e entrada real do ML-04."""
import sys

import numpy as np
import pandas as pd
import pytest


def csv_dreamt(tmp_path, *, lacuna=False):
    inicio = 7 * 64
    tick = np.arange(inicio + 4 * 1920)
    estagio = np.repeat(['P', 'W', 'N2', 'Missing', 'R'], [inicio, 1920, 1920, 1920, 1920])
    d = pd.DataFrame(dict(TIMESTAMP=tick / 64, ACC_X=0, ACC_Y=0, ACC_Z=64,
                          Sleep_Stage=estagio, Obstructive_Apnea=tick))
    if lacuna:
        d = d.drop(index=inicio + 1920 + 10)
    p = tmp_path / 'S002_whole_df.csv'
    d.to_csv(p, index=False)
    return p


def test_unidade_grade_e_indices_originais(tmp_path):
    from src.carregar.dreamt import ler_epocas
    a, y, idx, _ = ler_epocas(csv_dreamt(tmp_path))
    assert a.shape == (4, 960, 3)
    np.testing.assert_array_equal(a[0, 0], [0, 0, 1])
    np.testing.assert_array_equal(y, [0, 1, -1, 1])
    np.testing.assert_array_equal(idx, [0, 1, 2, 3])


def test_lacuna_nao_e_interpolada_e_nao_renumera(tmp_path):
    from src.carregar.dreamt import ler_epocas
    _, y, idx, _ = ler_epocas(csv_dreamt(tmp_path, lacuna=True))
    np.testing.assert_array_equal(y, [0, -1, 1])
    np.testing.assert_array_equal(idx, [0, 2, 3])


def test_pares_e_fase_incoerentes_reprovam(tmp_path):
    from src.carregar.dreamt import ler_epocas
    p = csv_dreamt(tmp_path)
    d = pd.read_csv(p)
    d.loc[7 * 64 + 1, 'ACC_Z'] = 63
    d.to_csv(p, index=False)
    with pytest.raises(ValueError, match='pares'):
        ler_epocas(p)
    d.loc[7 * 64 + 1, 'ACC_Z'] = 64
    d.loc[7 * 64 + 1920, 'Sleep_Stage'] = 'W'
    d.to_csv(p, index=False)
    with pytest.raises(ValueError, match='fase'):
        ler_epocas(p)


def test_colunas_clinicas_ignoradas_e_acc_obrigatoria(tmp_path):
    from src.carregar.dreamt import ler_epocas
    p = csv_dreamt(tmp_path)
    a = ler_epocas(p)[0]
    d = pd.read_csv(p)
    d['Obstructive_Apnea'] = 'não é sinal'
    d.to_csv(p, index=False)
    np.testing.assert_array_equal(a, ler_epocas(p)[0])
    d.drop(columns='ACC_Z').to_csv(p, index=False)
    with pytest.raises(ValueError, match='ACC_Z'):
        ler_epocas(p)


def test_cauda_truncada_fica_fora(tmp_path):
    from src.carregar.dreamt import ler_epocas
    p = csv_dreamt(tmp_path)
    pd.read_csv(p).iloc[:-1].to_csv(p, index=False)
    _, y, idx, info = ler_epocas(p)
    np.testing.assert_array_equal(y, [0, 1, -1])
    np.testing.assert_array_equal(idx, [0, 1, 2])
    assert info['cauda_incompleta'] == 1


def test_carregador_comum_separa_lacuna_e_participante(tmp_path):
    from dataclasses import replace
    from src.carregar import carregar
    from src.configuracao import carregar_config
    pasta = tmp_path / 'data_64Hz'
    pasta.mkdir()
    p = csv_dreamt(pasta)
    d = pd.read_csv(p)
    d.loc[d['Sleep_Stage'] == 'R', 'ACC_Z'] = 128
    d.to_csv(p, index=False)
    d['ACC_Z'] = 192
    d.to_csv(pasta / 'S003_whole_df.csv', index=False)
    cfg = replace(carregar_config(), contexto_epocas=1)
    conj = carregar('dreamt', cfg, pasta=tmp_path)
    np.testing.assert_array_equal(conj.segmentos, [0, 0, 1, 2, 2, 3])
    np.testing.assert_array_equal(conj.X[2, ::8], [1, 1, 1])
    np.testing.assert_array_equal(conj.X[3, ::8], [2, 2, 2])


def test_cli_dreamt_exige_dados_brutos(monkeypatch, capsys):
    from experimentos import ml04_validacao_externa as ml04
    monkeypatch.setattr(sys, 'argv', ['ml04', '--coorte', 'dreamt'])
    with pytest.raises(SystemExit, match='2'):
        ml04.main()
    assert 'dreamt exige --dados-brutos' in capsys.readouterr().err


def test_cli_dreamt_encaminha_o_caminho(monkeypatch, tmp_path):
    from experimentos import ml04_validacao_externa as ml04
    from pathlib import Path
    treino = tmp_path / 'treino'
    treino.mkdir()
    saida = tmp_path / 'saida'
    brutos = tmp_path / 'dreamt'
    brutos.mkdir()
    chamadas = []
    monkeypatch.setattr(ml04, 'rodar', lambda *a, **kw: chamadas.append(kw))
    monkeypatch.setattr(ml04, 'comparar', lambda *a: None)
    monkeypatch.setattr(sys, 'argv', ['ml04', '--coorte', 'dreamt',
                                    '--dados-brutos', str(brutos), '--dados-wearanize', str(treino),
                                    '--cache', str(tmp_path / 'cache'), '--saida-dir', str(saida)])
    assert ml04.main() == 0
    assert chamadas[0]['coorte'] == 'dreamt'
    assert chamadas[0]['dados_dreamt'] == Path(brutos)
