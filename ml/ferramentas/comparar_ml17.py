"""Comparação pareada por célula, com dispersão e máximos (ML-17)."""
import argparse
import json
from pathlib import Path

import numpy as np


def delta(antes, depois, seed=20260910):
    a, b = np.asarray(antes, float), np.asarray(depois, float)
    if a.ndim != 1 or a.shape != b.shape or not len(a):
        raise ValueError('pares vazios ou desalinhados')
    ok = np.isfinite(a) & np.isfinite(b)
    d = b[ok] - a[ok]
    base = dict(n_total=len(a), n_pares=int(ok.sum()),
                n_invalidos_antes=int((~np.isfinite(a)).sum()),
                n_invalidos_depois=int((~np.isfinite(b)).sum()))
    if not len(d):
        return dict(base, media=None, desvio=None, minimo=None, maximo=None, max_abs=None,
                    ic95=None, por_participante=[None] * len(a))
    rng = np.random.default_rng(seed)
    medias = rng.choice(d, size=(2000, len(d)), replace=True).mean(axis=1)
    indices = np.flatnonzero(ok)
    return dict(base, media=float(d.mean()), desvio=float(d.std(ddof=1)) if len(d) > 1 else 0.,
                minimo=float(d.min()), maximo=float(d.max()), max_abs=float(np.abs(d).max()),
                indice_max_abs=int(indices[np.argmax(np.abs(d))]),
                ic95=np.percentile(medias, [2.5, 97.5]).tolist(),
                por_participante=[float(bi-ai) if valido else None
                                  for ai, bi, valido in zip(a, b, ok)])


def comparar_celula(a, b):
    if a['sujeitos'] != b['sujeitos']:
        raise ValueError('participantes ou ordem diferentes; não fazer pareado')
    if set(a['por_sujeito']) != set(b['por_sujeito']):
        raise ValueError('métricas diferentes')
    numero = lambda v: float(v) if np.isfinite(v) else None
    return {k: dict(antes=numero(a['media'][k]), depois=numero(b['media'][k]),
                    delta=delta(a['por_sujeito'][k], b['por_sujeito'][k]))
            for k in a['por_sujeito']}


def carregar_resultados(pasta, versao):
    raiz = pasta / versao / 'ml/experimentos/saida'
    direto = raiz / 'ml17_rodada'
    celulas = {}
    for grupo in ('newcastle', 'walch_principal', 'walch_todos'):
        d = json.loads((direto / (grupo + '.json')).read_text(encoding='utf-8'))
        for braco, configs in d['resultados'].items():
            for config, met in configs.items():
                celulas[f'{grupo}/{braco}/{config}'] = met
    d = json.loads((direto / 'lados.json').read_text(encoding='utf-8'))
    for braco, configs in d['resultados'].items():
        for config, lados in configs.items():
            for lado in ('a_esquerdo_isolado', 'b_direito_isolado'):
                celulas[f'lados/{braco}/{config}/{lado}'] = lados[lado]
    arquivos = [p for p in raiz.rglob('ml03b_otimizacoes_*.json')]
    if len(arquivos) != 1:
        raise ValueError('resultados de otimização ausentes/ambíguos')
    d = json.loads(arquivos[0].read_text(encoding='utf-8'))
    if set(d['itens']) != {'baseline', '8b', '9'}:
        raise ValueError('otimizações incompletas')
    for item, bracos in d['itens'].items():
        for braco, met in bracos.items():
            celulas[f'otimizacoes/{braco}/{item}'] = met
    if len(celulas) != 69:
        raise ValueError('esperadas 36 células externas, 24 de punhos e 9 de otimizações')
    return celulas


def comparar_rodada(pasta):
    a, b = (carregar_resultados(pasta, v) for v in ('antes', 'depois'))
    if set(a) != set(b):
        raise ValueError('células diferentes')
    return {k: comparar_celula(a[k], b[k]) for k in a}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--pasta', type=Path, required=True)
    ap.add_argument('--saida', type=Path, required=True)
    args = ap.parse_args()
    resultado = comparar_rodada(args.pasta)
    args.saida.write_text(json.dumps(resultado, indent=2, allow_nan=False), encoding='utf-8')
    print(len(resultado), 'células comparadas')


if __name__ == '__main__':
    main()
