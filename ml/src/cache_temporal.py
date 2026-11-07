"""Caches derivados com contrato temporal explícito (ML-17), sem dados no Git."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import pickle

import numpy as np

from .epocas import segmentos_epocas

VERSAO = 'ml17-v1'
RAIZ = Path(__file__).resolve().parents[1]
FONTES = ('src/cache_temporal.py', 'src/epocas.py', 'src/features.py', 'src/sinal.py',
          'src/carregar/base.py', 'src/carregar/__init__.py',
          'src/carregar/wearanize.py', 'src/carregar/newcastle.py', 'src/carregar/walch.py',
          'experimentos/ml03b_ablacao.py', 'experimentos/ml04_validacao_externa.py')


def identidade(cfg):
    return dict(versao=VERSAO, hash_config=cfg.hash, fontes={
        p: hashlib.sha256((RAIZ / p).read_text(encoding='utf-8').encode('utf-8')).hexdigest()
        for p in FONTES})


def segmentos_de(d):
    try:
        ids = np.asarray(d['id'])
        n = len(d['y'])
        if ids.ndim == 0:
            ids = np.repeat(str(ids), n)
        if len(d['X']) != n or len(ids) != n:
            raise ValueError('X/y/id com comprimentos diferentes')
        return segmentos_epocas(ids, d['gravacao'], d['indice_epoca'])
    except KeyError as e:
        raise ValueError('cache sem identidade temporal: regenere a partir do bruto') from e


def salvar_features(caminho, cfg, **dados):
    segmentos_de(dados)
    np.savez_compressed(caminho, identidade=json.dumps(identidade(cfg), sort_keys=True), **dados)


def ler_features(caminho, cfg):
    with np.load(caminho, allow_pickle=False) as d:
        if 'identidade' not in d or json.loads(str(d['identidade'])) != identidade(cfg):
            raise ValueError(f'cache temporal incompatível: {Path(caminho).name}; regenere')
        dados = {k: d[k] for k in d.files if k != 'identidade'}
    segmentos_de(dados)
    return dados


def caminho_base(sujeitos, cfg, pasta):
    chave = hashlib.sha256(json.dumps([identidade(cfg), list(sujeitos)],
                                     sort_keys=True).encode()).hexdigest()[:16]
    return Path(pasta) / f'_cache_base_wearanize_{VERSAO}_{chave}.pkl'


def salvar_base(caminho, base, sujeitos, cfg):
    for b in base.values():
        segmentos_de(b)
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open('wb') as f:
        pickle.dump(dict(identidade=identidade(cfg), sujeitos=list(sujeitos), dados=base), f)


def ler_base(caminho, sujeitos, cfg):
    # Somente caches locais confiáveis. pickle não é um formato de intercâmbio.
    with Path(caminho).open('rb') as f:
        d = pickle.load(f)
    if d.get('identidade') != identidade(cfg) or d.get('sujeitos') != list(sujeitos):
        raise ValueError('cache base temporal incompatível; regenere a partir do bruto')
    for b in d['dados'].values():
        segmentos_de(b)
    return d['dados']
