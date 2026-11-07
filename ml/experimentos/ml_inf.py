"""Treina, avalia e exporta a regressão logística de seis features da ML-INF."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
from io import BytesIO
import json
from pathlib import Path
import pickle
import platform
import subprocess
import sys

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_info, threadpool_limits

from ferramentas.comparar_ml17 import delta
from ferramentas.resumir_ml13 import resumo_metricas
from ferramentas.resumir_ml17 import delta_publico, validar_sem_notas
from src.avaliar import avaliar_epoca, avaliar_por_sujeito, split_por_sujeito
from src.carregar.dreamt import carregar_features_dreamt
from src.configuracao import carregar_config
from src.features import FEATURES_DO_DISPOSITIVO, NOMES_FEATURES


ML = Path(__file__).resolve().parents[1]
RAIZ = ML.parent
VERSAO = 'ml-inf-cabeca-v1'
LIMIAR = .5
METRICAS = ('kappa', 'especificidade', 'acuracia', 'f1_vigilia', 'f1_sono')


def sha_dados(X, y, ids):
    h = hashlib.sha256(np.asarray(X, dtype='<f8').tobytes())
    h.update(np.asarray(y, dtype='<i8').tobytes())
    h.update(json.dumps(ids.tolist()).encode())
    return h.hexdigest()


def dados_ml17(evidencia, cfg, *, temporal=False):
    """Reutiliza somente o cache local congelado e autenticado pela ML-17."""
    publico = json.loads((ML / 'experimentos/saida/ml17/manifesto.json').read_text(encoding='utf-8'))
    privado = json.loads((evidencia / 'rodadas/manifesto.json').read_text(encoding='utf-8'))
    hashes = privado['cache_sha256']
    if hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest() != publico['caches_agregado_sha256']:
        raise ValueError('inventário local de caches difere do manifesto ML-17')
    cache = evidencia / 'cache'
    hashes = {k.replace(chr(92), '/'): v for k, v in hashes.items()}

    def bytes_conferidos(caminho):
        dados = caminho.read_bytes()
        if hashlib.sha256(dados).hexdigest() != hashes.get(caminho.relative_to(cache).as_posix()):
            raise ValueError('cache não confere com o manifesto ML-17')
        return dados

    def externa(pasta, padrao, *, esquerdo=False):
        Xs, ys, ids, gravacoes, indices = [], [], [], [], []
        for p in sorted((cache / pasta).glob(padrao)):
            with np.load(BytesIO(bytes_conferidos(p)), allow_pickle=False) as d:
                if esquerdo and str(d['lado']) != 'esquerdo':
                    continue
                Xs.append(d['X'])
                ys.append(d['y'])
                ids.append(np.full(len(d['y']), str(d['id'])))
                if temporal:
                    gravacoes.append(np.broadcast_to(d['gravacao'], d['y'].shape))
                    indices.append(d['indice_epoca'])
        dados = dict(zip(('X', 'y', 'id'), map(np.concatenate, (Xs, ys, ids))))
        if temporal:
            dados.update(gravacao=np.concatenate(gravacoes), indice_epoca=np.concatenate(indices))
        return dados

    # O pickle só é aberto após verificar os bytes contra o manifesto público.
    pkl, = cache.glob('_cache_base_wearanize_ml17-v1_*.pkl')
    treino = pickle.loads(bytes_conferidos(pkl))
    if treino['identidade']['hash_config'] != cfg.hash or len(treino['sujeitos']) != 92:
        raise ValueError('configuração ou seleção de treino diferente da ML-17')
    treino = treino['dados']['cabeca']
    conjuntos = {
        'wearanize/cabeca': treino,
        'newcastle': externa('newcastle_features_ml17-v1', f'{cfg.hash}_*.npz', esquerdo=True),
        'walch_principal': externa('walch_features_ml17-v1', f'{cfg.hash}_principal_*.npz'),
    }
    if temporal:
        conjuntos['walch_todos'] = externa('walch_features_ml17-v1', f'{cfg.hash}_todos_*.npz')
    execucoes = publico['execucoes']
    for nome, dados in conjuntos.items():
        rodada = 'newcastle' if nome == 'wearanize/cabeca' else nome
        esperado = execucoes['depois/' + rodada]['hash_entradas'][nome]['sha256']
        if sha_dados(dados['X'], dados['y'], dados['id']) != esperado:
            raise ValueError('X/y/IDs carregados divergem da rodada ML-17: ' + nome)
    if not temporal:
        conjuntos = {k: (d['X'], d['y'], d['id']) for k, d in conjuntos.items()}
    return conjuntos, publico['atribuicao_wearanize_oa']


def ajustar(X, y, seed):
    if X.ndim != 2 or X.shape[1] != len(FEATURES_DO_DISPOSITIVO):
        raise ValueError('treino exige as seis features canônicas do dispositivo')
    modelo = make_pipeline(StandardScaler(), LogisticRegression(
        C=1.0, solver='lbfgs', max_iter=2000, class_weight='balanced', random_state=seed))
    return modelo.fit(X, y)


def probabilidade_loso(X, y, ids, seed):
    p = np.empty(len(y))
    for _, treino, teste in split_por_sujeito(ids):
        p[teste] = ajustar(X[treino], y[treino], seed).predict_proba(X[teste])[:, 1]
    return p


def exportar_modelo(modelo, cfg, codigo, hash_treino, atribuicao):
    escala = modelo.named_steps['standardscaler']
    lr = modelo.named_steps['logisticregression']
    if lr.classes_.tolist() != [0, 1]:
        raise ValueError('classes do modelo devem ser vigília=0 e sono=1')
    creditos = {k: atribuicao[k] for k in ('colecao', 'colecao_primaria', 'artigo', 'licenca_do_pacote')}
    return dict(versao=VERSAO, features=list(FEATURES_DO_DISPOSITIVO),
                coeficientes=lr.coef_[0].tolist(), intercepto=float(lr.intercept_[0]),
                medias=escala.mean_.tolist(), escalas=escala.scale_.tolist(),
                limiar=LIMIAR, comparacao='>', classe_positiva=1,
                treino=dict(dataset='Wearanize+ OA', braco='cabeca', qualidade='original',
                            n_participantes=92, commit=codigo, hash_config=cfg.hash,
                            sha256_dados=hash_treino),
                atribuicao=dict(creditos, alteracoes='Modelo derivado do Wearanize+ OA.'))


def vetor_dourado(modelo):
    sys.path.insert(0, str(RAIZ / 'scripts'))
    from simulador_c2 import NoiteSintetica, payload_da_epoca

    seed = 7
    inicio = datetime(2026, 11, 1, 23, tzinfo=timezone.utc)
    payloads = [json.loads(json.dumps(payload_da_epoca(e)))
                for e in NoiteSintetica(inicio, 360, seed=seed)]
    X = np.asarray([p['f'] for p in payloads])
    probas = modelo.predict_proba(X)[:, 1]
    abaixo = np.flatnonzero(probas < LIMIAR)
    acima = np.flatnonzero(probas > LIMIAR)
    if not len(abaixo) or not len(acima):
        raise ValueError('fixture SIM-02 precisa de entradas nos dois lados do limiar')
    lo, hi = abaixo[np.argmax(probas[abaixo])], acima[np.argmin(probas[acima])]
    casos = [dict(origem='simulador_c2', indice=int(i), payload=payloads[i],
                  probabilidade=float(probas[i]), classe=int(probas[i] > LIMIAR))
             for i in sorted({int(np.argmin(probas)), int(lo), int(hi), int(np.argmax(probas))})]

    # Interpolação entre dois vetores do simulador. A afinidade vale no logit,
    # portanto as entradas continuam nas faixas das features e cercam 0,5.
    i_min, i_max = np.argmin(probas), np.argmax(probas)
    zlo, zhi = modelo.decision_function(X[[i_min, i_max]])
    if not zlo < -4e-6 < 4e-6 < zhi:
        raise ValueError('logits do simulador não cobrem os casos próximos ao limiar')
    for alvo in (-4e-6, 4e-6):
        fracao = (alvo - zlo) / (zhi - zlo)
        f = X[i_min] + fracao * (X[i_max] - X[i_min])
        p = float(modelo.predict_proba(f[None, :])[0, 1])
        casos.append(dict(origem='interpolacao_sintetica', f=f.tolist(),
                          probabilidade=p, classe=int(p > LIMIAR)))
    return dict(modelo=VERSAO, seed_simulador=seed, inicio=inicio.isoformat(),
                epocas_simulador=360, tolerancia_absoluta=1e-12, casos=casos)


def avaliar(y, pred, ids, seed):
    trivial = np.ones_like(y)
    m = avaliar_por_sujeito(y, pred, ids, metricas=METRICAS, seed=seed).dict()
    t = avaliar_por_sujeito(y, trivial, ids, metricas=METRICAS, seed=seed).dict()
    pareado = {k: delta_publico(delta(t['por_sujeito'][k], m['por_sujeito'][k], seed))
               for k in METRICAS}
    confusoes = {}
    for nome, p in (('modelo', pred), ('sempre_sono', trivial)):
        d = avaliar_epoca(y, p).dict()
        confusoes[nome] = {k: d[k] for k in ('vp', 'vn', 'fp', 'fn', 'n')}
    return dict(n_epocas=len(y), n_participantes=m['n_sujeitos'], modelo=resumo_metricas(m),
                sempre_sono=resumo_metricas(t), delta_pareado=pareado, confusoes=confusoes), (m, t)


def executar(evidencia_ml17, dados_dreamt, saida):
    if saida.resolve().is_relative_to(RAIZ.resolve()):
        raise ValueError('resultados individuais exigem saída fora do repositório')
    cfg = carregar_config()
    if (cfg.hash, cfg.seed, cfg.taxa_comum_hz, cfg.epoca_s) != ('aec203907e6f', 20260910, 32, 30):
        raise ValueError('configuração difere do protocolo ML-INF')
    saida.mkdir(parents=True, exist_ok=False)
    codigo = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=RAIZ, text=True).strip()
    conjuntos, atribuicao = dados_ml17(evidencia_ml17, cfg)
    print('Caches Wearanize, Newcastle e Walch conferidos contra a ML-17.', flush=True)
    ml13 = json.loads((ML / 'experimentos/saida/ml13/agregados.json').read_text(encoding='utf-8'))
    hash_dreamt = hashlib.sha256((dados_dreamt / 'SHA256SUMS.txt').read_bytes()).hexdigest()
    if hash_dreamt != ml13['sha256_manifesto_dreamt']:
        raise ValueError('manifesto DREAMT difere do conferido na ML-13')
    sonho, qualidade, exclusoes = carregar_features_dreamt(dados_dreamt, cfg)
    if qualidade != {k: v for k, v in ml13['qualidade'].items() if k != 'segmentos'}:
        raise ValueError('DREAMT difere da cobertura fixada na ML-13')
    conjuntos['dreamt'] = sonho['X'], sonho['y'], sonho['id']
    colunas = [NOMES_FEATURES.index(nome) for nome in FEATURES_DO_DISPOSITIVO]
    conjuntos = {k: (X[:, colunas], y, ids) for k, (X, y, ids) in conjuntos.items()}
    X, y, ids = conjuntos['wearanize/cabeca']
    if len(set(ids)) != 92:
        raise ValueError('treino exige os 92 participantes aprovados')
    print('DREAMT carregada. Iniciando LOSO e avaliação externa.', flush=True)
    with threadpool_limits(limits=1):
        pools = [{k: p[k] for k in ('user_api', 'internal_api', 'num_threads', 'version')}
                 for p in threadpool_info()]
        if not pools or any(p['num_threads'] != 1 for p in pools):
            raise RuntimeError('protocolo exige uma thread em todos os pools nativos')
        p_loso = probabilidade_loso(X, y, ids, cfg.seed)
        final = ajustar(X, y, cfg.seed)
        resultados, locais = {}, {}
        for nome, (Xt, yt, ids_t) in conjuntos.items():
            p = p_loso if nome == 'wearanize/cabeca' else final.predict_proba(Xt)[:, 1]
            pred = (p > LIMIAR).astype(int)
            resultados[nome], locais[nome] = avaliar(yt, pred, ids_t, cfg.seed)
            np.savez_compressed(saida / (nome.replace('/', '-') + '.npz'),
                                y=yt, pred=pred, probabilidade=p, ids=ids_t.astype(str))
            print(nome, len(yt), 'épocas', flush=True)
        modelo = exportar_modelo(final, cfg, codigo, sha_dados(X, y, ids), atribuicao)
        dourado = vetor_dourado(final)
    resumo = dict(modelo=VERSAO, hash_config=cfg.hash, seed=cfg.seed, commit=codigo,
                  sha256_dados_treino=modelo['treino']['sha256_dados'],
                  sha256_manifesto_dreamt=hash_dreamt,
                  qualidade_dreamt=qualidade, resultados=resultados, pools=pools,
                  python=platform.python_version(), sistema=platform.system(),
                  bibliotecas={n: importlib.metadata.version(n) for n in
                               ('numpy', 'pandas', 'scipy', 'scikit-learn', 'threadpoolctl')})
    validar_sem_notas(resumo)
    for nome, obj in ((VERSAO, modelo), (VERSAO + '-dourado', dourado), ('agregados', resumo)):
        (saida / f'{nome}.json').write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n',
                                          encoding='utf-8', newline='\n')
    (saida / 'metricas-locais.json').write_text(json.dumps(dict(metricas=locais, exclusoes=exclusoes)),
                                              encoding='utf-8')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--evidencia-ml17', type=Path, required=True)
    ap.add_argument('--dados-dreamt', type=Path, required=True)
    ap.add_argument('--saida', type=Path, required=True)
    args = ap.parse_args()
    executar(args.evidencia_ml17, args.dados_dreamt, args.saida)


if __name__ == '__main__':
    main()
