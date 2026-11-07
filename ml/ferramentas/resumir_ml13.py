"""Publica somente estatísticas agregadas do resultado local da DREAMT."""
import argparse
import json
from math import fsum, isclose, isfinite
from pathlib import Path
from statistics import stdev

from ferramentas.comparar_ml17 import delta
from ferramentas.resumir_ml17 import delta_publico, validar_sem_notas


def _numero(valor):
    return valor if isfinite(valor) else None


def resumo_metricas(m):
    saida = {}
    for metrica, valores in m['por_sujeito'].items():
        finitos = [v for v in valores if isfinite(v)]
        if len(valores) != m['n_sujeitos'] or len(finitos) != m['n_valido'][metrica]:
            raise ValueError('contagem de notas incompatível')
        if finitos:
            media = fsum(finitos) / len(finitos)
            desvio = stdev(finitos) if len(finitos) > 1 else 0.0
            if not (isclose(media, m['media'][metrica], rel_tol=0, abs_tol=1e-14)
                    and isclose(desvio, m['desvio_padrao'][metrica], rel_tol=0, abs_tol=1e-14)):
                raise ValueError('estatística agregada difere das notas locais')
        saida[metrica] = dict(media=_numero(m['media'][metrica]),
                             desvio=_numero(m['desvio_padrao'][metrica]),
                             ic95=[_numero(m[k][metrica]) for k in ('ic95_baixo', 'ic95_alto')],
                             n_valido=len(finitos), n_total=len(valores))
    return saida


def _direcao(ic, sinal):
    if ic is None or None in ic:
        return 'inconclusiva'
    lo, hi = ic
    if (lo > 0 and sinal == 1) or (hi < 0 and sinal == -1):
        return 'confirmada'
    if (hi < 0 and sinal == 1) or (lo > 0 and sinal == -1):
        return 'refutada'
    return 'inconclusiva'


def resumir(r):
    if r['teste']['dataset'] != 'dreamt' or set(r['resultados']) != {'pulso', 'cabeca', 'cabeca_e4'}:
        raise ValueError('resultado DREAMT incompleto')
    resumo, contrastes = {}, {}
    for braco, configs in r['resultados'].items():
        if set(configs) != {'base_ctx2', 'item8b_hmm', 'item9_ctx11', 'item9b_ctx11_hmm'}:
            raise ValueError('configurações DREAMT incompletas')
        base = configs['base_ctx2']
        resumo[braco] = {k: resumo_metricas(m) for k, m in configs.items()}
        contrastes[braco] = {}
        for config, m in configs.items():
            if config == 'base_ctx2':
                continue
            if base['sujeitos'] != m['sujeitos']:
                raise ValueError('notas desalinhadas no contraste pareado')
            contrastes[braco][config] = {
                metrica: delta_publico(delta(antes, m['por_sujeito'][metrica], seed=r['seed']))
                for metrica, antes in base['por_sujeito'].items()}

    pulso = contrastes['pulso']
    ic_p1 = resumo['pulso']['item9_ctx11']['kappa']['ic95']
    ic_p2k = pulso['item9_ctx11']['kappa']['ic95']
    ic_p2e = pulso['item9_ctx11']['especificidade']['ic95']
    ic_p3 = pulso['item8b_hmm']['especificidade']['ic95']
    p2 = [_direcao(ic_p2k, 1), _direcao(ic_p2e, 1)]
    previsoes = {
        'P1': dict(ic95=ic_p1, resultado=_direcao(ic_p1, 1)),
        'P2': dict(kappa=dict(ic95=ic_p2k, resultado=p2[0]),
                   especificidade=dict(ic95=ic_p2e, resultado=p2[1]),
                   resultado='confirmada' if p2 == ['confirmada'] * 2 else
                   ('refutada' if 'refutada' in p2 else 'inconclusiva')),
        'P3': dict(ic95=ic_p3, resultado=_direcao(ic_p3, -1)),
    }
    publico = {k: r[k] for k in ('hash_config', 'seed', 'utc', 'treino', 'teste',
                                 'qualidade', 'sha256_manifesto_dreamt', 'sha256_treino')}
    publico.update(trivial=resumo_metricas(r['trivial_no_dreamt']), resultados=resumo,
                   contrastes_pareados=contrastes, previsoes=previsoes,
                   confusoes={nome: {k: m[k] for k in ('vp', 'vn', 'fp', 'fn', 'n')}
                              for nome, m in r['confusoes'].items()})
    validar_sem_notas(publico)
    return publico


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--entrada', type=Path, required=True)
    ap.add_argument('--saida', type=Path, required=True)
    args = ap.parse_args()
    d = resumir(json.loads(args.entrada.read_text(encoding='utf-8')))
    args.saida.write_text(json.dumps(d, indent=2, allow_nan=False) + '\n',
                         encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
