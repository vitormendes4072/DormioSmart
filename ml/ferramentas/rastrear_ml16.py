"""Controles históricos da ML-16, sempre em uma pasta de saída nova.

As variantes L1/mediana por componente são reconstruções para auditoria.
O pipeline atual continua usando L2/mediana geométrica.
"""
import argparse
from contextlib import contextmanager
import csv
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import pickle
import sys
import time
import warnings

import numpy as np
from threadpoolctl import threadpool_info, threadpool_limits

ML = Path(__file__).resolve().parents[1]
if str(ML) not in sys.path:
    sys.path.insert(0, str(ML))


def sha256_texto(caminho):
    return hashlib.sha256(caminho.read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def selecionar_piloto(pasta):
    """Mesma ordem do participants.tsv usada pelo baixador original."""
    from src.carregar.wearanize import _pasta_plugnplay
    pnp = _pasta_plugnplay(Path(pasta))
    with (pnp / 'participants.tsv').open(encoding='utf-8', newline='') as arquivo:
        sujeitos = [r['participant_id'].strip() for r in csv.DictReader(arquivo, delimiter='\t')][:10]
    if len(sujeitos) != 10 or len(set(sujeitos)) != 10:
        raise ValueError('o piloto exige dez IDs distintos na lista canônica')
    for sujeito in sujeitos:
        if not (pnp / sujeito / 'eeg' / f'{sujeito}_task-sleep_eeg.edf').is_file():
            raise ValueError(f'EDF ausente para o candidato {sujeito}')
    return sujeitos


@contextmanager
def variantes_features(norma='l2', referencia='geometrica'):
    """Altera apenas as duas definições investigadas e restaura os módulos."""
    if norma not in ('l1', 'l2') or referencia not in ('geometrica', 'mediana-unitaria', 'mediana-bruta'):
        raise ValueError('variante desconhecida')
    import src.features as f
    import experimentos.ml02_baselines as e
    direcao_original = f.direcao_referencia
    extrator_original = e.features_de_epoca
    if referencia == 'mediana-unitaria':
        f.direcao_referencia = lambda g: f.unitario(np.median(f.unitario(g), axis=0))
    elif referencia == 'mediana-bruta':
        f.direcao_referencia = lambda g: f.unitario(np.median(g, axis=0))

    def extrair(a_epocas, fs, **kwargs):
        X, g = extrator_original(a_epocas, fs, **kwargs)
        if norma == 'l1':
            for i, a in enumerate(a_epocas):
                din = a - f.estimar_gravidade(a, fs)
                X[i, 3] = np.abs(din).sum(axis=1).mean()
        return X, g

    e.features_de_epoca = extrair
    try:
        yield
    finally:
        f.direcao_referencia = direcao_original
        e.features_de_epoca = extrator_original


def executar_baseline(args, saida):
    import experimentos.ml02_baselines as e
    import src.carregar.wearanize as w
    raiz_anterior, argv_anterior = e.RAIZ, sys.argv
    carregador_anterior = w.carregar_wearanize
    sujeitos = None
    try:
        if args.modo.startswith('piloto-'):
            if args.dados_brutos is None:
                raise ValueError('--dados-brutos deve apontar para a pasta Wearanize')
            sujeitos = selecionar_piloto(args.dados_brutos)
            def carregar(**kwargs):
                return carregador_anterior(pasta=args.dados_brutos, sujeitos=sujeitos, **kwargs)
            w.carregar_wearanize = carregar
            parametros = ['--dataset', 'wearanize', '--posicao', args.modo.split('-')[1]]
        else:
            parametros = ['--dataset', 'sintetico']
        e.RAIZ = saida
        sys.argv = ['ml02_baselines', *parametros]
        with variantes_features(args.norma, args.referencia):
            codigo = e.main()
        if codigo:
            raise RuntimeError(f'baseline terminou com código {codigo}')
    finally:
        e.RAIZ, sys.argv = raiz_anterior, argv_anterior
        w.carregar_wearanize = carregador_anterior
    return {'sujeitos_candidatos': sujeitos}


def executar_sem_scaler(args, saida):
    import experimentos.ml03b_ablacao as e
    from sklearn.exceptions import ConvergenceWarning
    from src.configuracao import carregar_config
    if args.cache is None:
        raise ValueError('--cache deve apontar para o cache local de features')
    cfg = carregar_config()
    with args.cache.open('rb') as arquivo:
        base = pickle.load(arquivo)
    Xs = {n: e.montar_X(base, n, cfg.contexto_epocas) for n in e.NOMES_BRACOS}
    ys = {n: base[n]['y'] for n in e.NOMES_BRACOS}
    ids = {n: base[n]['id'] for n in e.NOMES_BRACOS}
    with warnings.catch_warnings(record=True) as avisos:
        warnings.simplefilter('always', ConvergenceWarning)
        matriz = e.matriz_generica(Xs, ys, ids, cfg.seed, modo='sem_scaler')
    resultado = {'item2_sem_scaler': {a + '->' + b: m.dict() for (a, b), m in matriz.items()}}
    (saida / 'sem_scaler.json').write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding='utf-8')
    return {'avisos_convergencia': sum(issubclass(a.category, ConvergenceWarning) for a in avisos),
            'cache_sha256': hashlib.sha256(args.cache.read_bytes()).hexdigest()}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--modo', required=True, choices=('piloto-cabeca', 'piloto-pulso', 'sintetico', 'sem-scaler'))
    ap.add_argument('--saida', type=Path, required=True, help='pasta nova; nunca uma saída histórica')
    ap.add_argument('--threads', type=int, required=True, choices=(1, 8))
    ap.add_argument('--norma', choices=('l1', 'l2'), default='l2')
    ap.add_argument('--referencia', choices=('geometrica', 'mediana-unitaria', 'mediana-bruta'), default='geometrica')
    ap.add_argument('--dados-brutos', type=Path)
    ap.add_argument('--cache', type=Path)
    args = ap.parse_args()
    if args.modo != 'sintetico' and (args.norma != 'l2' or args.referencia != 'geometrica'):
        ap.error('as variantes de features são apenas para o controle sintético')
    if args.saida.exists():
        ap.error('a pasta de saída já existe; use uma pasta nova')
    args.saida.mkdir(parents=True)
    # Carregar todas as bibliotecas antes de limitar os pools nativos.
    import experimentos.ml02_baselines  # noqa: F401
    import experimentos.ml03b_ablacao  # noqa: F401
    inicio = time.monotonic()
    with threadpool_limits(limits=args.threads):
        ambiente = [{k: v for k, v in item.items() if k != 'filepath'} for item in threadpool_info()]
        detalhe = executar_sem_scaler(args, args.saida) if args.modo == 'sem-scaler' else executar_baseline(args, args.saida)
    meta = {
        'modo': args.modo, 'threads': args.threads, 'norma': args.norma, 'referencia': args.referencia,
        'segundos': time.monotonic() - inicio, 'ambiente_numerico': ambiente,
        'versoes': {n: version(n) for n in ('numpy', 'scipy', 'scikit-learn', 'pandas')},
        'config_sha256_utf8_lf': sha256_texto(ML / 'config.yaml'),
        'instrumento_sha256_utf8_lf': sha256_texto(Path(__file__)), **detalhe,
    }
    (args.saida / 'proveniencia.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
