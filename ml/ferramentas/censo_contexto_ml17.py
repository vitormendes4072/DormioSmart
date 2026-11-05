"""Conta mudanças de contexto antes de treinar; exige igualdade das entradas."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import pickle
import sys

import numpy as np

ML = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ML))

from src.cache_temporal import VERSAO, ler_base, ler_features, segmentos_de  # noqa: E402
from src.configuracao import carregar_config  # noqa: E402
from src.epocas import empilhar_contexto, fatias_segmentos  # noqa: E402
from experimentos.ml03b_ablacao import normalizar_por_sujeito  # noqa: E402


def conferir_entrada(a, b):
    for k in ('X', 'y', 'id'):
        igual = np.array_equal(a[k], b[k], equal_nan=True) if k == 'X' else np.array_equal(a[k], b[k])
        if not igual:
            raise ValueError(f'entrada reconstruída difere em {k}; não atribuir o efeito só ao contexto')


def contar(b, janela):
    X = normalizar_por_sujeito(b['X'], b['id'])
    seg = segmentos_de(b)
    antes = empilhar_contexto(X, janela)
    depois = empilhar_contexto(X, janela, segmentos=seg)
    estrutural = np.zeros(len(X), dtype=bool)
    # Toda época cujo alcance pediria uma linha fora de seu segmento muda
    # de vizinhança, mesmo quando as features nas pontas são iguais.
    for f in fatias_segmentos(seg):
        k = np.arange(f.start, f.stop)
        estrutural[k] = ((k - janela < f.start) & (f.start > 0)) | (
                        (k + janela >= f.stop) & (f.stop < len(X)))
    numerica = np.any(antes != depois, axis=1)
    por_sujeito = []
    for s in dict.fromkeys(b['id'].tolist()):
        m = b['id'] == s
        por_sujeito.append(dict(n_epocas=int(m.sum()),
                               vizinhanca_alterada=int(estrutural[m].sum()),
                               vetor_alterado=int(numerica[m].sum())))
    return dict(janela=janela, n_epocas=len(X), n_segmentos=sum(1 for _ in fatias_segmentos(seg)),
                n_sujeitos=len(por_sujeito), vizinhanca_alterada=int(estrutural.sum()),
                vetor_alterado=int(numerica.sum()),
                maior_por_sujeito=max((v['vizinhanca_alterada'] for v in por_sujeito), default=0),
                por_sujeito_sem_ids=por_sujeito)


def _juntar(arquivos, cfg, temporal):
    partes = []
    for f in arquivos:
        if temporal:
            d = ler_features(f, cfg)
        else:
            with np.load(f, allow_pickle=True) as z:
                d = dict(z)
        n = len(d['y'])
        d['id'] = np.repeat(str(d['id']), n)
        d = {k: d[k] for k in ('X', 'y', 'id', 'gravacao', 'indice_epoca') if k in d}
        partes.append(d)
    if not partes:
        raise ValueError('nenhum cache selecionado; conferência no vazio proibida')
    return {k: np.concatenate([p[k] for p in partes]) for k in partes[0]}


def censar(cache, legado, cfg):
    arquivos = list(cache.glob('_cache_base_wearanize_ml17-v1_*.pkl'))
    if len(arquivos) != 1:
        raise ValueError('exige exatamente uma seleção de treino')
    with arquivos[0].open('rb') as f:
        selecao = pickle.load(f)['sujeitos']
    base = ler_base(arquivos[0], selecao, cfg)
    with (legado / '_cache_base_wearanize_14646b9aacb7d397.pkl').open('rb') as f:
        antiga = pickle.load(f)
    conjuntos = {}
    for braco, b in base.items():
        conferir_entrada(b, antiga[braco])
        conjuntos['wearanize/' + braco] = b
    for coorte, filtros in [('newcastle', ['esquerdo', 'direito']),
                            ('walch', ['principal', 'todos'])]:
        for filtro in filtros:
            padrao = (f'{cfg.hash}_*_{filtro}.npz' if coorte == 'newcastle' else
                      f'{cfg.hash}_{filtro}_*.npz')
            novos = sorted((cache / (coorte + '_features_' + VERSAO)).glob(padrao))
            velhos = sorted((legado / (coorte + '_features')).glob(padrao))
            if [f.name for f in novos] != [f.name for f in velhos]:
                raise ValueError('censo de arquivos novo/antigo diferente: ' + coorte + '/' + filtro)
            b = _juntar(novos, cfg, True)
            conferir_entrada(b, _juntar(velhos, cfg, False))
            conjuntos[coorte + '/' + filtro] = b
    return {nome: [contar(b, j) for j in (2, 11)] for nome, b in conjuntos.items()}


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cache', type=Path, required=True)
    ap.add_argument('--legado', type=Path, required=True)
    ap.add_argument('--saida', type=Path, required=True)
    args = ap.parse_args()
    censo = censar(args.cache, args.legado, carregar_config())
    args.saida.write_text(json.dumps(censo, indent=2), encoding='utf-8')
    for nome, linhas in censo.items():
        for v in linhas:
            print(nome, '±' + str(v['janela']), v['n_epocas'], 'épocas;',
                  v['vizinhanca_alterada'], 'vizinhanças;', v['vetor_alterado'], 'vetores alterados')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
