"""Rodadas isoladas antes/depois, usando fontes Git e as mesmas entradas (ML-17)."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import warnings
from zipfile import ZipFile

GRUPOS = ('newcastle', 'walch_principal', 'walch_todos', 'lados', 'otimizacoes')


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def preparar(args):
    if args.pasta.exists():
        raise ValueError('pasta de execução já existe: não sobrescrever resultados/checkpoints')
    # O censo foi produzido pelo conferidor de entradas; não aceitar resultado vazio.
    censo = json.loads(args.censo.read_text(encoding='utf-8'))
    esperados = {'wearanize/cabeca', 'wearanize/cabeca_e4', 'wearanize/pulso',
                 'newcastle/esquerdo', 'newcastle/direito', 'walch/principal', 'walch/todos'}
    if set(censo) != esperados or any(len(v) != 2 or [r['janela'] for r in v] != [2, 11]
                                     or any(r['n_epocas'] <= 0 for r in v)
                                     for v in censo.values()):
        raise ValueError('censo incompleto ou vazio')
    args.pasta.mkdir(parents=True)
    manifesto = dict(utc_preparacao=datetime.now(timezone.utc).isoformat(),
                     censo=str(args.censo.resolve()), censo_sha256=sha(args.censo),
                     cache=str(args.cache.resolve()), executor_sha256=sha(__file__), fontes={},
                     cache_sha256={str(p.relative_to(args.cache)): sha(p)
                                   for p in sorted(args.cache.rglob('*')) if p.is_file()})
    for nome, ref in [('antes', args.antes), ('depois', args.depois)]:
        commit = subprocess.check_output(['git', 'rev-parse', ref], text=True).strip()
        arquivo = subprocess.check_output(['git', 'archive', '--format=zip', commit, 'ml'])
        destino = args.pasta / nome
        with ZipFile(io.BytesIO(arquivo)) as z:
            for n in z.namelist():
                if n.endswith('.py') or n in ('ml/config.yaml', 'ml/requirements.txt'):
                    alvo = destino / n
                    alvo.parent.mkdir(parents=True, exist_ok=True)
                    alvo.write_bytes(z.read(n))
        manifesto['fontes'][nome] = dict(commit=commit, arquivos={
            str(p.relative_to(destino)): sha(p) for p in sorted(destino.rglob('*')) if p.is_file()})
    (args.pasta / 'manifesto.json').write_text(json.dumps(manifesto, indent=2), encoding='utf-8')


def conferir(pasta):
    m = json.loads((pasta / 'manifesto.json').read_text(encoding='utf-8'))
    if sha(m['censo']) != m['censo_sha256'] or sha(__file__) != m['executor_sha256']:
        raise ValueError('censo/executor mudou depois do congelamento')
    for nome, entrada in m['fontes'].items():
        for arq, digest in entrada['arquivos'].items():
            if sha(pasta / nome / arq) != digest:
                raise ValueError('fonte da execução mudou: ' + arq)
    cache = Path(m['cache'])
    for arq, digest in m['cache_sha256'].items():
        if sha(cache / arq) != digest:
            raise ValueError('cache da execução mudou: ' + arq)
    return m


def worker(pasta, versao, grupo):
    for n in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        os.environ[n] = '1'
    m = conferir(pasta)
    raiz = pasta / versao / 'ml'
    sys.path.insert(0, str(raiz))
    import importlib
    import importlib.metadata
    import pickle
    import numpy as np
    from threadpoolctl import threadpool_limits, threadpool_info
    from src.avaliar import avaliar_epoca, avaliar_por_sujeito
    from src.configuracao import carregar_config

    cache = Path(m['cache'])
    arquivos = list(cache.glob('_cache_base_wearanize_ml17-v1_*.pkl'))
    if len(arquivos) != 1:
        raise ValueError('seleção de treino ambígua')
    with arquivos[0].open('rb') as f:
        dados = pickle.load(f)
    base, sujeitos = dados['dados'], dados['sujeitos']
    cfg = carregar_config(raiz / 'config.yaml')
    modulo = ('experimentos.ml03b_otimizacoes' if grupo == 'otimizacoes' else
              'experimentos.ml04_validacao_externa')
    e = importlib.import_module(modulo)
    # Adaptadores somente de entrada: seleção conferida e cache X/y/id idêntico.
    e.sujeitos_com_posicoes = lambda *a, **kw: sujeitos
    e._base_wearanize = lambda *a, **kw: base
    e._carregar_base_com_cache = lambda *a, **kw: base
    e.PASTA_FEATURES = cache / 'newcastle_features_ml17-v1'
    e.PASTA_FEATURES_WALCH = cache / 'walch_features_ml17-v1'
    destino = raiz / 'experimentos/saida/ml17_rodada'
    destino.mkdir(parents=True, exist_ok=True)
    capturas_arquivo = destino / f'{grupo}_capturas.json'
    capturas = (json.loads(capturas_arquivo.read_text(encoding='utf-8'))
                if grupo == 'otimizacoes' and capturas_arquivo.exists() else [])
    def capturar(y, p, ids, **kw):
        r = avaliar_por_sujeito(y, p, ids, **kw)
        extra = avaliar_por_sujeito(y, p, ids, metricas=('f1_vigilia', 'f1_sono'),
                                   seed=kw.get('seed', cfg.seed))
        conf = [avaliar_epoca(np.asarray(y)[ids == s], np.asarray(p)[ids == s]).dict()
                for s in r.sujeitos]
        i = len(capturas)
        np.savez_compressed(destino / f'{grupo}_pred_{i:02d}.npz', y=y, p=p, ids=ids)
        capturas.append(dict(metricas=r.dict(), f1=extra.dict(), confusoes=conf))
        (destino / f'{grupo}_capturas.json').write_text(json.dumps(capturas), encoding='utf-8')
        return r
    e.avaliar_por_sujeito = capturar
    inicio = time.time()
    utc_inicio = datetime.now(timezone.utc).isoformat()
    with threadpool_limits(limits=1), warnings.catch_warnings(record=True) as avisos:
        warnings.simplefilter('always')
        pools = threadpool_info()
        if not pools or any(v['num_threads'] != 1 for v in pools):
            raise ValueError('pool nativo não está com uma thread')
        if grupo == 'otimizacoes':
            for item in ('baseline', '8b', '9'):
                while True:
                    sys.argv = [modulo, '--item', item, '--orcamento-s', '60']
                    codigo = e.main()
                    if codigo == 0:
                        break
                    if codigo != 2:
                        raise RuntimeError(f'otimização {item} falhou com {codigo}')
        elif grupo == 'lados':
            e.lados(cfg, cfg.seed, destino / 'lados.json')
        else:
            coorte = 'newcastle' if grupo == 'newcastle' else 'walch'
            e.rodar(cfg, cfg.seed, 'esquerdo', destino / (grupo + '.json'), coorte=coorte,
                    incluir_baixa_taxa=grupo == 'walch_todos')
    esperado = 9 if grupo == 'otimizacoes' else 24 if grupo == 'lados' else 13
    if len(capturas) != esperado:
        raise ValueError(f'capturas incompletas/duplicadas: {len(capturas)} != {esperado}')
    estado = dict(status='concluido', segundos=time.time()-inicio, versao=versao, grupo=grupo,
                  utc_inicio=utc_inicio, utc_fim=datetime.now(timezone.utc).isoformat(),
                  codigo=m['fontes'][versao]['commit'], python=sys.version,
                  bibliotecas={n: importlib.metadata.version(n) for n in
                               ('numpy', 'scipy', 'pandas', 'scikit-learn', 'threadpoolctl')},
                  pools=pools, n_avisos=len(avisos), n_capturas=len(capturas),
                  avisos_por_tipo={n: sum(type(v.message).__name__ == n for v in avisos)
                                   for n in sorted({type(v.message).__name__ for v in avisos})})
    (pasta / f'{versao}_{grupo}.json').write_text(json.dumps(estado, indent=2), encoding='utf-8')


def rodar(pasta):
    conferir(pasta)
    def executar(versao, grupo):
        estado = pasta / f'{versao}_{grupo}.json'
        if estado.exists() and json.loads(estado.read_text())['status'] == 'concluido':
            return
        log = pasta / f'{versao}_{grupo}.log'
        with log.open('w', encoding='utf-8') as f:
            r = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--pasta', str(pasta),
                                '--worker', versao, grupo], stdout=f, stderr=subprocess.STDOUT)
        if r.returncode:
            raise RuntimeError(f'{versao}/{grupo} falhou ({r.returncode}); veja {log.name}')
        print(versao, grupo, 'concluído', flush=True)
    with ThreadPoolExecutor(max_workers=2) as ex:
        fs = [ex.submit(executar, v, g) for v in ('antes', 'depois') for g in GRUPOS]
        for f in as_completed(fs):
            f.result()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--pasta', type=Path, required=True)
    ap.add_argument('--preparar', action='store_true')
    ap.add_argument('--rodar', action='store_true')
    ap.add_argument('--cache', type=Path)
    ap.add_argument('--censo', type=Path)
    ap.add_argument('--antes', default='d429d43e1b7bafacae67fbebb9a328942d63efff')
    ap.add_argument('--depois', default='3273431b6ebec4e3889bd3f01c3593b32dc0137e')
    ap.add_argument('--worker', nargs=2)
    args = ap.parse_args()
    args.pasta = args.pasta.resolve()
    if args.preparar:
        if args.cache is None or args.censo is None:
            ap.error('--preparar exige --cache e --censo')
        preparar(args)
    elif args.worker:
        worker(args.pasta, *args.worker)
    elif args.rodar:
        rodar(args.pasta)
    else:
        ap.error('escolha --preparar ou --rodar')


if __name__ == '__main__':
    main()
