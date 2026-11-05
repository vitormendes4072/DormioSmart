"""Recalcula métricas das predições sem importar o avaliador do projeto."""
import argparse
import json
from pathlib import Path

import numpy as np


def recalcular(y, p, ids):
    y, p, ids = map(np.asarray, (y, p, ids))
    if y.shape != p.shape or y.ndim != 1 or ids.shape != y.shape or not len(y):
        raise ValueError('predições vazias/desalinhadas')
    if not np.isin(y, [0, 1]).all() or not np.isin(p, [0, 1]).all():
        raise ValueError('classes fora de 0/1')
    r = {k: [] for k in ('acuracia', 'especificidade', 'kappa', 'f1_vigilia', 'f1_sono')}
    div = lambda a, b: a / b if b else float('nan')
    for s in sorted(set(ids.tolist())):
        a, b = y[ids == s], p[ids == s]
        tn, fp, fn, tp = np.bincount(2*a+b, minlength=4).tolist()
        n = len(a)
        esperado = ((tn+fp)*(tn+fn) + (tp+fp)*(tp+fn)) / (n*n)
        valores = ((tn+tp)/n, div(tn, tn+fp), div((tn+tp)/n-esperado, 1-esperado),
                   div(2*tn, 2*tn+fp+fn), div(2*tp, 2*tp+fp+fn))
        for k, v in zip(r, valores):
            r[k].append(v)
    return r


def conferir(pasta):
    n = 0
    maior_erro = 0.
    esperados = dict(newcastle=13, walch_principal=13, walch_todos=13, lados=24, otimizacoes=9)
    for versao in ('antes', 'depois'):
        raiz = pasta / versao / 'ml/experimentos/saida/ml17_rodada'
        arquivos = sorted(raiz.glob('*_capturas.json'))
        if {f.name.removesuffix('_capturas.json') for f in arquivos} != set(esperados):
            raise ValueError('capturas ausentes/incompletas')
        for f in arquivos:
            grupo = f.name.removesuffix('_capturas.json')
            capturas = json.loads(f.read_text(encoding='utf-8'))
            if len(capturas) != esperados[grupo]:
                raise ValueError('capturas incompletas/duplicadas em ' + grupo)
            for i, salvo in enumerate(capturas):
                with np.load(raiz / f'{grupo}_pred_{i:02d}.npz', allow_pickle=True) as d:
                    novo = recalcular(d['y'], d['p'], d['ids'])
                esperado = {**salvo['metricas']['por_sujeito'], **salvo['f1']['por_sujeito']}
                for k, v in novo.items():
                    np.testing.assert_allclose(v, esperado[k], rtol=0, atol=1e-12, equal_nan=True,
                                               err_msg=f'{versao}/{grupo}/{i}/{k}')
                    d = np.abs(np.asarray(v) - np.asarray(esperado[k]))
                    finitos = d[np.isfinite(d)]
                    if len(finitos):
                        maior_erro = max(maior_erro, float(finitos.max()))
                n += 1
    if n != 144:
        raise ValueError(f'capturas totais {n}; esperadas 144')
    return dict(capturas=n, metricas_por_captura=5, tolerancia_absoluta=1e-12,
                maior_erro_absoluto=maior_erro, divergencias=0)


def conferir_repeticao(pasta):
    """ML-04 e ML-04b ajustam novamente as 12 células do punho esquerdo."""
    celulas = []
    for versao in ('antes', 'depois'):
        raiz = pasta / versao / 'ml/experimentos/saida/ml17_rodada'
        for i in range(12):
            with np.load(raiz / f'newcastle_pred_{i+1:02d}.npz', allow_pickle=True) as a, \
                 np.load(raiz / f'lados_pred_{2*i:02d}.npz', allow_pickle=True) as b:
                if not np.array_equal(a['y'], b['y']) or not np.array_equal(a['ids'], b['ids']):
                    raise ValueError('repetição com alvos/participantes desalinhados')
                celulas.append(dict(versao=versao, indice_config=i, n_epocas=len(a['p']),
                                    n_diferentes=int(np.count_nonzero(a['p'] != b['p']))))
    return dict(celulas=len(celulas), epocas_comparadas=sum(v['n_epocas'] for v in celulas),
                predicoes_diferentes=sum(v['n_diferentes'] for v in celulas),
                max_diferentes_celula=max(v['n_diferentes'] for v in celulas))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--pasta', type=Path, required=True)
    ap.add_argument('--saida', type=Path, required=True)
    args = ap.parse_args()
    r = conferir(args.pasta)
    r['controle_repeticao_newcastle'] = conferir_repeticao(args.pasta)
    args.saida.write_text(json.dumps(r, indent=2), encoding='utf-8')
    print(r)


if __name__ == '__main__':
    main()
