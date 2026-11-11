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
    def resumo(m, k):
        return dict(desvio=numero(m['desvio_padrao'][k]), n_valido=m['n_valido'][k],
                    ic95=[numero(m['ic95_baixo'][k]), numero(m['ic95_alto'][k])],
                    por_participante=[numero(v) for v in m['por_sujeito'][k]])
    return {k: dict(antes=numero(a['media'][k]), depois=numero(b['media'][k]),
                    resumo_antes=resumo(a, k), resumo_depois=resumo(b, k),
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
    for grupo in ('newcastle', 'walch_principal', 'walch_todos', 'lados', 'otimizacoes'):
        estados = [json.loads((pasta / f'{v}_{grupo}.json').read_text(encoding='utf-8'))
                   for v in ('antes', 'depois')]
        if any(e['status'] != 'concluido' for e in estados) or estados[0]['hash_entradas'] != estados[1]['hash_entradas']:
            raise ValueError('execuções incompletas ou entradas antes/depois diferentes')
    a, b = (carregar_resultados(pasta, v) for v in ('antes', 'depois'))
    if set(a) != set(b):
        raise ValueError('células diferentes')
    return {k: comparar_celula(a[k], b[k]) for k in a}


def f1_da_captura(captura, metrica):
    if json.dumps(captura['metricas'], sort_keys=True) != json.dumps(metrica, sort_keys=True):
        raise ValueError('captura não corresponde à célula; não alinhar somente pela posição')
    return captura['f1']


def carregar_f1(pasta, versao):
    primarias = carregar_resultados(pasta, versao)
    raiz = pasta / versao / 'ml/experimentos/saida/ml17_rodada'
    saida = {}
    for grupo in ('newcastle', 'walch_principal', 'walch_todos', 'lados', 'otimizacoes'):
        capturas = json.loads((raiz / f'{grupo}_capturas.json').read_text(encoding='utf-8'))
        chaves = [k for k in primarias if k.startswith(grupo + '/')]
        if grupo == 'otimizacoes':
            chaves = [f'otimizacoes/{b}/{it}' for it in ('baseline', '8b', '9')
                       for b in ('cabeca', 'cabeca_e4', 'pulso')]
        if grupo in ('newcastle', 'walch_principal', 'walch_todos'):
            capturas = capturas[1:]  # âncora trivial, fora das 69 células de modelos
        if len(chaves) != len(capturas):
            raise ValueError('células/capturas não correspondem')
        for chave, captura in zip(chaves, capturas):
            saida[chave] = f1_da_captura(captura, primarias[chave])
    return saida


def efeitos(pasta):
    saida = {}
    for versao in ('antes', 'depois'):
        celulas = carregar_resultados(pasta, versao)
        saida[versao] = {}
        for coorte in ('newcastle', 'walch_principal', 'walch_todos'):
            for braco in ('cabeca', 'cabeca_e4', 'pulso'):
                base = celulas[f'{coorte}/{braco}/base_ctx2']
                for config in ('item8b_hmm', 'item9_ctx11', 'item9b_ctx11_hmm'):
                    alvo = celulas[f'{coorte}/{braco}/{config}']
                    if base['sujeitos'] != alvo['sujeitos']:
                        raise ValueError('efeito sem participantes pareados')
                    saida[versao][f'{coorte}/{braco}/{config}'] = {
                        k: delta(base['por_sujeito'][k], alvo['por_sujeito'][k])
                        for k in ('kappa', 'especificidade', 'acuracia')}
        for braco in ('cabeca', 'cabeca_e4', 'pulso'):
            base = celulas[f'otimizacoes/{braco}/baseline']
            for item in ('8b', '9'):
                alvo = celulas[f'otimizacoes/{braco}/{item}']
                if base['sujeitos'] != alvo['sujeitos']:
                    raise ValueError('otimização sem participantes pareados')
                saida[versao][f'otimizacoes/{braco}/{item}'] = {
                    k: delta(base['por_sujeito'][k], alvo['por_sujeito'][k])
                    for k in ('kappa', 'especificidade', 'acuracia')}
    return saida


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--pasta', type=Path, required=True)
    ap.add_argument('--saida', type=Path, required=True)
    ap.add_argument('--f1-saida', type=Path)
    ap.add_argument('--efeitos-saida', type=Path)
    args = ap.parse_args()
    resultado = comparar_rodada(args.pasta)
    args.saida.write_text(json.dumps(resultado, indent=2, allow_nan=False), encoding='utf-8')
    if args.f1_saida:
        a, b = (carregar_f1(args.pasta, v) for v in ('antes', 'depois'))
        f1 = {k: comparar_celula(a[k], b[k]) for k in a}
        args.f1_saida.write_text(json.dumps(f1, indent=2, allow_nan=False), encoding='utf-8')
    if args.efeitos_saida:
        args.efeitos_saida.write_text(json.dumps(efeitos(args.pasta), indent=2, allow_nan=False), encoding='utf-8')
    print(len(resultado), 'células comparadas')


if __name__ == '__main__':
    main()
