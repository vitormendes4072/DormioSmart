"""Recompõe estatísticas das notas locais; não ajusta modelos nem publica notas."""
import argparse
import json
from math import fsum, isclose
from pathlib import Path
from statistics import stdev
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ferramentas.comparar_ml17 import comparar_rodada, carregar_f1, comparar_celula  # noqa: E402
from ferramentas.resumir_ml17 import comparacao_publica  # noqa: E402


def conferir_notas(dados):
    def igual(a, b):
        if not isclose(a, b, rel_tol=0, abs_tol=1e-14):
            raise ValueError('estatística difere das notas por participante')
    if len(dados) != 69:
        raise ValueError('esperadas 69 células')
    quantidade = 0
    for celula in dados.values():
        for m in celula.values():
            a, b = (m['resumo_' + v]['por_participante'] for v in ('antes', 'depois'))
            if len(a) != len(b) or len(a) != m['delta']['n_total']:
                raise ValueError('notas desalinhadas')
            for versao, valores in (('antes', a), ('depois', b)):
                validos = [v for v in valores if v is not None]
                if len(validos) != m['resumo_' + versao]['n_valido']:
                    raise ValueError('contagem válida difere')
                if validos:
                    igual(m[versao], fsum(validos) / len(validos))
                    igual(m['resumo_' + versao]['desvio'], stdev(validos) if len(validos) > 1 else 0)
                elif m[versao] is not None:
                    raise ValueError('média sem notas válidas')
            d = [y-x for x, y in zip(a, b) if x is not None and y is not None]
            if len(d) != m['delta']['n_pares']:
                raise ValueError('contagem pareada difere')
            if d:
                for campo, valor in dict(media=fsum(d)/len(d), max_abs=max(abs(v) for v in d),
                                          minimo=min(d), maximo=max(d),
                                          desvio=stdev(d) if len(d) > 1 else 0).items():
                    igual(m['delta'][campo], valor)
            elif m['delta']['media'] is not None:
                raise ValueError('delta sem pares válidos')
            quantidade += 1
    return quantidade


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--pasta', type=Path, required=True, help='rodadas na evidência local')
    ap.add_argument('--publicos', type=Path, required=True)
    ap.add_argument('--saida', type=Path, required=True, help='relatório local sem notas')
    args = ap.parse_args()
    a, b = (carregar_f1(args.pasta, v) for v in ('antes', 'depois'))
    conjuntos = {'comparacao.json': comparar_rodada(args.pasta),
                 'f1_complementar.json': {k: comparar_celula(a[k], b[k]) for k in a}}
    n = 0
    for nome, dados in conjuntos.items():
        n += conferir_notas(dados)
        if comparacao_publica(dados) != json.loads((args.publicos / nome).read_text(encoding='utf-8')):
            raise ValueError('agregado publicado difere da evidência local: ' + nome)
    resultado = dict(celulas=69, estatisticas_celula_metrica=n, divergencias=0,
                     metodo='math.fsum e statistics.stdev sobre notas locais; sem src.avaliar',
                     limites='Não recompõe ICs bootstrap nem ajusta modelos.')
    args.saida.write_text(json.dumps(resultado, indent=2) + '\n', encoding='utf-8')
    print(resultado)


if __name__ == '__main__':
    main()
