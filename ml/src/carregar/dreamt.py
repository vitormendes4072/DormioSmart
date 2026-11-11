"""DREAMT v2.2.0, gravações E4 da pasta data_64Hz."""
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from ..epocas import fatias_segmentos, segmentos_epocas
from ..features import features_de_epoca


ACC = ('ACC_X', 'ACC_Y', 'ACC_Z')
COLUNAS = ('TIMESTAMP', *ACC, 'Sleep_Stage')
ROTULOS = {'P': -1, 'Missing': -1, 'W': 0, 'N1': 1, 'N2': 1, 'N3': 1, 'R': 1}
TICKS_EPOCA = 64 * 30


class FaseAmbigua(ValueError):
    """Gravação sem uma única fase PSG demonstrável pelas transições."""


def _rotulo_epoca(estagios):
    """Converte uma época de estágio uniforme para o rótulo binário."""
    return ROTULOS[estagios[0]] if np.all(estagios == estagios[0]) else -1


def ler_epocas(arquivo):
    """Recupera os pares repetidos e a grade de rótulos, sem interpolar lacunas."""
    d = pd.read_csv(arquivo, usecols=list(COLUNAS), dtype={'Sleep_Stage': 'category'})
    t = d['TIMESTAMP'].to_numpy(dtype=float) * 64
    if (not len(t) or not np.isfinite(t).all() or np.any(t < 0)
            or np.any(t != np.rint(t)) or np.any(np.diff(t) <= 0)):
        raise ValueError('TIMESTAMP fora da grade crescente de 64 Hz')
    ticks = t.astype(np.int64)
    estagios = d['Sleep_Stage'].astype(object).fillna('Missing').to_numpy()
    if not set(d['Sleep_Stage'].cat.categories) <= ROTULOS.keys():
        raise ValueError('estágio PSG desconhecido')
    pontuados = np.flatnonzero(np.isin(estagios, ('W', 'N1', 'N2', 'N3', 'R')))
    if not len(pontuados):
        raise FaseAmbigua('fase PSG sem rótulo pontuado')
    primeira = pontuados[0]
    ancora = ticks[primeira]
    mudancas = np.flatnonzero((estagios[1:] != estagios[:-1]) & (np.diff(ticks) == 1)) + 1
    if ancora % 2 or np.any((ticks[mudancas[mudancas > primeira]] - ancora) % TICKS_EPOCA):
        raise FaseAmbigua('fase PSG incompatível com épocas de 30 s')

    acc = d.loc[:, list(ACC)].to_numpy(dtype=float)
    finitos = np.isfinite(acc).all(axis=1)
    pares = (ticks[:-1] % 2 == 0) & (np.diff(ticks) == 1) & finitos[:-1] & finitos[1:]
    if np.any(pares & np.any(acc[:-1] != acc[1:], axis=1)):
        raise ValueError('pares ACC não repetidos na grade 64/32 Hz')
    inicios = np.arange(ancora, ticks[-1] + 1, TICKS_EPOCA)
    linhas = np.searchsorted(ticks, inicios)
    blocos, rotulos, indices = [], [], []
    perdas = Counter(epocas_na_grade=len(inicios))
    for indice, (inicio, linha) in enumerate(zip(inicios, linhas)):
        fim = linha + TICKS_EPOCA
        if inicio + TICKS_EPOCA - 1 > ticks[-1]:
            perdas['cauda_incompleta'] += 1
        elif (fim > len(ticks) or ticks[linha] != inicio
              or ticks[fim - 1] != inicio + TICKS_EPOCA - 1):
            perdas['lacuna_temporal'] += 1
        elif not finitos[linha:fim].all():
            perdas['acc_ausente'] += 1
        else:
            rotulo = _rotulo_epoca(estagios[linha:fim])
            perdas['sem_rotulo'] += int(rotulo < 0)
            blocos.append(acc[linha:fim:2] / 64)
            indices.append(indice)
            rotulos.append(rotulo)
    return (np.asarray(blocos, dtype=float).reshape(-1, 960, 3),
            np.asarray(rotulos, dtype=int), np.asarray(indices, dtype=int), dict(perdas))


def carregar_features_dreamt(pasta, cfg):
    """Retorna features sem contexto com a identidade temporal original."""
    if (cfg.taxa_comum_hz, cfg.epoca_s) != (32, 30):
        raise ValueError('DREAMT exige grade de 32 Hz e épocas de 30 s')
    arquivos = sorted((Path(pasta) / 'data_64Hz').glob('S[0-9][0-9][0-9]_whole_df.csv'))
    if not arquivos:
        raise ValueError('DREAMT sem CSVs na pasta data_64Hz')
    partes = []
    exclusoes = {}
    por_gravacao = []
    perdas = Counter(gravacoes_encontradas=len(arquivos))
    for arquivo in arquivos:
        sujeito = arquivo.name.split('_', 1)[0]
        try:
            a, y, idx, info = ler_epocas(arquivo)
        except FaseAmbigua as exc:
            exclusoes[sujeito] = str(exc)
            perdas['gravacoes_fase_ambigua'] += 1
            continue
        perdas.update(info)
        ok = y >= 0
        if not ok.any():
            exclusoes[sujeito] = 'sem época completa pontuada'
            perdas['gravacoes_sem_epoca_pontuada'] += 1
            continue
        ids = np.repeat(sujeito, len(y))
        gravacao = np.repeat(arquivo.stem, len(y))
        seg = segmentos_epocas(ids, gravacao, idx)
        X = np.concatenate([features_de_epoca(a[s], fs=32)[0] for s in fatias_segmentos(seg)])
        partes.append(dict(X=X[ok], y=y[ok], id=ids[ok],
                           gravacao=gravacao[ok], indice_epoca=idx[ok]))
        por_gravacao.append(info)
    if not partes:
        raise ValueError('DREAMT sem épocas completas com rótulo')
    dados = {chave: np.concatenate([parte[chave] for parte in partes]) for chave in partes[0]}
    perdas['gravacoes_avaliaveis'] = len(partes)
    perdas['epocas_retidas'] = len(dados['y'])
    perdas.update({f'max_{k}_por_gravacao': max(info.get(k, 0) for info in por_gravacao)
                   for k in ('cauda_incompleta', 'lacuna_temporal', 'acc_ausente', 'sem_rotulo')})
    return dados, dict(perdas), exclusoes
