"""Reproduz ML-04 item9_ctx11 e exporta o modelo de cabeça para inferência noturna."""

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from numbers import Real
from pathlib import Path
import platform
import subprocess
import sys

import numpy as np
from scipy.special import expit
from sklearn.linear_model import LogisticRegression
from threadpoolctl import threadpool_info, threadpool_limits

from experimentos.ml03b_ablacao import normalizar_por_sujeito
from experimentos.ml04_validacao_externa import CONFIGS
from experimentos.ml_inf import ML, RAIZ, avaliar, dados_ml17, sha_dados
from ferramentas.resumir_ml17 import validar_sem_notas
from src.avaliar import split_por_sujeito
from src.cache_temporal import segmentos_de
from src.carregar.dreamt import carregar_features_dreamt
from src.configuracao import carregar_config
from src.epocas import empilhar_contexto, segmentos_epocas
from src.features import FEATURES_DO_DISPOSITIVO, NOMES_FEATURES, features_inter_epoca

VERSAO = 'ml-inf-cabeca-v2'
CONFIGURACAO = 'item9_ctx11'
CONTEXTO = CONFIGS[CONFIGURACAO]['contexto']
MINIMO_EPOCAS = 23
TOLERANCIA = 1e-12
LACUNA_S = 45.0
ML13 = 'experimentos/saida/ml13/agregados.json'
ML17 = 'experimentos/saida/ml17/comparacao.json'


def ler_json(caminho):
    return json.loads(caminho.read_text(encoding='utf-8'))


def colunas_contexto():
    """Sonda a ordem efetiva do empilhamento usando códigos distintos por célula."""
    deslocamentos = range(-CONTEXTO, CONTEXTO + 1)
    rotulos = [f'{nome}__{d:+d}' for d in deslocamentos for nome in NOMES_FEATURES]
    codigos = np.arange(len(rotulos)).reshape(len(deslocamentos), len(NOMES_FEATURES))
    central = empilhar_contexto(codigos, CONTEXTO, segmentos=np.zeros(len(codigos)))[CONTEXTO]
    return [rotulos[int(i)] for i in central]


def epocas_validas(X):
    if X.ndim != 2 or X.shape[1] != len(NOMES_FEATURES):
        raise ValueError('cada época precisa das oito features canônicas')
    return np.isfinite(X).all(axis=1)


def preparar_historico(dados):
    X, ids = dados['X'], dados['id']
    if not epocas_validas(X).all():
        raise ValueError('época histórica com feature inválida')
    gravacoes = np.broadcast_to(dados['gravacao'], ids.shape)
    chaves = np.unique(np.column_stack((ids, gravacoes)).astype(str), axis=0,
                       return_inverse=True)[1].ravel()
    contagens = np.bincount(chaves)
    if np.any(contagens < 2):
        raise ValueError('desvio amostral indefinido em gravação histórica')
    Xn = normalizar_por_sujeito(X, chaves)
    return empilhar_contexto(Xn, CONTEXTO, segmentos=segmentos_de(dados)), {
        'n_gravacoes': len(contagens), 'minimo_observado': int(contagens.min()),
        'abaixo_do_piso': int(np.sum(contagens < MINIMO_EPOCAS)),
    }


def ajustar(X, y, seed):
    return LogisticRegression(max_iter=2000, class_weight='balanced', random_state=seed).fit(X, y)


def prever_loso(X, y, ids, seed):
    pred = np.empty(len(y), dtype=int)
    p = np.empty(len(y))
    for _, treino, teste in split_por_sujeito(ids):
        modelo = ajustar(X[treino], y[treino], seed)
        pred[teste] = modelo.predict(X[teste])
        p[teste] = modelo.predict_proba(X[teste])[:, 1]
    return pred, p


def exportar(modelo, cfg, codigo, dados, hash_contexto, atribuicao):
    if modelo.classes_.tolist() != [0, 1]:
        raise ValueError('classes esperadas: vigília=0 e sono=1')
    creditos = {k: atribuicao[k] for k in ('colecao', 'colecao_primaria', 'artigo', 'licenca_do_pacote')}
    return dict(
        versao=VERSAO, configuracao=CONFIGURACAO, features=list(NOMES_FEATURES),
        colunas_contexto=colunas_contexto(), coeficientes=modelo.coef_[0].tolist(),
        intercepto=float(modelo.intercept_[0]), classe_positiva=1, limiar=0.5,
        comparacao='>', regra_classe='logit > 0', classe_empate=0,
        normalizacao=dict(unidade='gravacao', ddof=1, piso_desvio=1e-9,
                          desvio_substituto=1.0, minimo_epocas_validas=MINIMO_EPOCAS,
                          epoca_valida='oito features numéricas finitas após conversão',
                          d_angulo_ausente_na_borda=0.0),
        contexto=dict(vizinhas=CONTEXTO, preenchimento='replicar_ponta_do_segmento',
                      quebra_servidor_s=LACUNA_S, comparacao_lacuna='>'),
        treino=dict(dataset='Wearanize+ OA', braco='cabeca', qualidade='original',
                    n_participantes=len(set(dados['id'])), commit=codigo, hash_config=cfg.hash,
                    sha256_dados=sha_dados(dados['X'], dados['y'], dados['id']),
                    sha256_contexto=hash_contexto),
        atribuicao=dict(creditos, alteracoes='Modelo derivado do Wearanize+ OA.'))


def prever_exportado(modelo, X):
    z = X @ np.asarray(modelo['coeficientes']) + modelo['intercepto']
    return (z > 0).astype(int), expit(z)


def importar_fronteira():
    sys.path[:0] = [str(RAIZ / 'web-app'), str(RAIZ / 'scripts')]
    try:
        import features_noite
        import simulador_c2
    finally:
        del sys.path[:2]
    return features_noite, simulador_c2


def preparar_noite(payloads, servidor):
    if tuple(servidor.ORDEM_FEATURES) != tuple(NOMES_FEATURES):
        raise ValueError('features canônicas do ML e do servidor divergem')
    if servidor.LACUNA_MAXIMA_S != LACUNA_S:
        raise ValueError('limite de lacuna do servidor difere do modelo')
    epocas = [dict(zip(FEATURES_DO_DISPOSITIVO, p['f'], strict=True),
                   instante=servidor.instante_do_banco(p['ts']), g=p['g'], fs=p['fs'])
              for p in payloads]
    linhas, ref = servidor.derivar_noite(epocas)
    # O None do servidor existe apenas no começo de cada sequência contínua.
    def valor(e, k):
        v = e[k]
        if k == 'd_angulo' and v is None:
            return 0.0
        return v if isinstance(v, Real) and not isinstance(v, bool) else np.nan

    X = np.asarray([[valor(e, k) for k in NOMES_FEATURES] for e in linhas],
                   dtype=float).reshape(-1, len(NOMES_FEATURES))
    validas = epocas_validas(X)
    if validas.sum() < MINIMO_EPOCAS:
        raise ValueError(f'noite com {validas.sum()} épocas válidas; mínimo {MINIMO_EPOCAS}')
    linhas_validas = [e for e, ok in zip(linhas, validas) if ok]
    instantes = [servidor.instante_do_banco(e['instante']) for e in linhas_validas]
    quebras = [(b - a).total_seconds() > LACUNA_S
               for a, b in zip(instantes, instantes[1:])]
    segmentos = np.cumsum([False, *quebras])
    Xn = normalizar_por_sujeito(X[validas], np.zeros(len(segmentos)))
    return linhas_validas, ref, segmentos, empilhar_contexto(Xn, CONTEXTO, segmentos=segmentos)


def casos_limiar(modelo):
    casos = []
    w, b = modelo.coef_[0], modelo.intercept_[0]
    for alvo in (-4e-6, 0.0, 4e-6):
        for i in np.flatnonzero(w):
            x = np.zeros(len(w))
            x[i] = (alvo - b) / w[i]
            logit = float(modelo.decision_function(x[None])[0])
            if (alvo == 0 and logit == 0) or (alvo != 0 and np.sign(logit) == np.sign(alvo)):
                p = float(modelo.predict_proba(x[None])[0, 1])
                casos.append(dict(contexto=x.tolist(), probabilidade=p,
                                  classe=int(modelo.predict(x[None])[0])))
                break
        else:
            raise ValueError('não foi possível gerar caso no limiar')
    return casos


def vetor_dourado(modelo):
    servidor, simulador = importar_fronteira()
    seed, n = 7, 960
    inicio = datetime(2026, 11, 1, 23, tzinfo=timezone.utc)
    payloads = [simulador.payload_da_epoca(e)
                for e in simulador.NoiteSintetica(inicio, n, seed=seed)]
    noites, paridade = {}, {}
    for nome, indices in (('continua', np.arange(n)), ('lacuna', np.delete(np.arange(n), n // 2))):
        entrada = [payloads[i] for i in indices]
        linhas, ref, segmentos, X = preparar_noite(entrada, servidor)
        inc_ml, delta_ml = features_inter_epoca(np.asarray([p['g'] for p in entrada]))
        inc_servidor = np.asarray([e['inclinacao_rel'] for e in linhas])
        comparaveis = [i for i, e in enumerate(linhas) if e['d_angulo'] is not None]
        bordas = [i for i, e in enumerate(linhas) if e['d_angulo'] is None]
        seg_ml = segmentos_epocas(np.zeros(len(indices)), np.zeros(len(indices)), indices)
        np.testing.assert_array_equal(segmentos, seg_ml)
        paridade[nome] = dict(
            max_inclinacao_graus=float(np.max(np.abs(inc_ml - inc_servidor))),
            max_delta_comparavel_graus=max(abs(delta_ml[i] - linhas[i]['d_angulo']) for i in comparaveis),
            max_delta_bordas_graus=float(np.max(np.abs(delta_ml[bordas]))),
            n_segmentos=int(segmentos[-1]) + 1)
        if max(paridade[nome][k] for k in ('max_inclinacao_graus', 'max_delta_comparavel_graus')) > 1e-6:
            raise ValueError('ângulos do servidor diferem do ML além da tolerância angular')
        noites[nome] = dict(payloads=entrada, features_servidor=linhas, g_ref=ref,
                            segmentos=segmentos.tolist(),
                            probabilidades=modelo.predict_proba(X)[:, 1].tolist(),
                            classes=modelo.predict(X).tolist())
    return dict(modelo=VERSAO, seed_simulador=seed, inicio=inicio.isoformat(),
                tolerancia_absoluta=TOLERANCIA, noites=noites, limiar=casos_limiar(modelo)), paridade


def conferir_reproducao(nome, agregado, notas, ml13, ml17, ref_local):
    chave = f'cabeca/{CONFIGURACAO}'
    if nome == 'dreamt':
        publico = ml13['resultados']['cabeca'][CONFIGURACAO]['kappa']
        alvo, ic, n = publico['media'], publico['ic95'], publico['n_valido']
        confusao = ref_local['confusoes'][chave]
        for k, v in agregado['confusoes']['modelo'].items():
            if v != confusao[k]:
                raise ValueError(f'DREAMT: matriz de confusão diverge em {k}')
    else:
        publico = ml17[f'{nome}/{chave}']['kappa']
        alvo = publico['depois']
        ic, n = (publico['resumo_depois'][k] for k in ('ic95', 'n_valido'))
    kappa = agregado['modelo']['kappa']
    esperado = ref_local['resultados']['cabeca'][CONFIGURACAO]['por_sujeito']
    maior = max(float(np.nanmax(np.abs(np.asarray(valores) - esperado[k])))
                for k, valores in notas['por_sujeito'].items() if k in esperado)
    np.testing.assert_allclose([kappa['media'], *kappa['ic95']], [alvo, *ic], rtol=0, atol=TOLERANCIA)
    if kappa['n_valido'] != n or maior > TOLERANCIA:
        raise ValueError(f'{nome}: contagem ou notas divergem; maior diferença {maior}')
    return dict(kappa_alvo=alvo, ic95=ic, n_valido=n, max_diferenca_por_participante=maior)


def executar(evidencia_ml17, dados_dreamt, referencia_ml13, saida):
    if saida.resolve().is_relative_to(RAIZ.resolve()):
        raise ValueError('resultados individuais exigem saída fora do repositório')
    cfg = carregar_config()
    if (cfg.hash, cfg.seed, cfg.taxa_comum_hz, cfg.epoca_s) != ('aec203907e6f', 20260910, 32, 30):
        raise ValueError('configuração difere do protocolo ML-INF')
    saida.mkdir(parents=True, exist_ok=False)
    codigo = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=RAIZ, text=True).strip()
    conjuntos, atribuicao = dados_ml17(evidencia_ml17, cfg, temporal=True)
    ml13, ml17 = ler_json(ML / ML13), ler_json(ML / ML17)
    manifesto = hashlib.sha256((dados_dreamt / 'SHA256SUMS.txt').read_bytes()).hexdigest()
    if manifesto != ml13['sha256_manifesto_dreamt']:
        raise ValueError('manifesto DREAMT difere do conferido na ML-13')
    print('Caches ML-17 conferidos. Carregando DREAMT.', flush=True)
    conjuntos['dreamt'], qualidade, _ = carregar_features_dreamt(dados_dreamt, cfg)
    if qualidade != {k: v for k, v in ml13['qualidade'].items() if k != 'segmentos'}:
        raise ValueError('DREAMT difere da cobertura fixada na ML-13')

    treino = conjuntos['wearanize/cabeca']
    X, cobertura = preparar_historico(treino)
    hash_contexto = hashlib.sha256(np.asarray(X, dtype='<f8').tobytes()).hexdigest()
    print('Iniciando LOSO e avaliações externas congeladas.', flush=True)
    with threadpool_limits(limits=1):
        pools = [{k: p[k] for k in ('user_api', 'internal_api', 'num_threads', 'version')}
                 for p in threadpool_info()]
        if not pools or any(p['num_threads'] != 1 for p in pools):
            raise RuntimeError('protocolo exige uma thread em todos os pools nativos')
        final = ajustar(X, treino['y'], cfg.seed)
        modelo = exportar(final, cfg, codigo, treino, hash_contexto, atribuicao)
        # A avaliação usa exatamente os números que atravessam a serialização JSON.
        modelo = json.loads(json.dumps(modelo, allow_nan=False))
        resultados, locais = {}, {}
        for nome, d in conjuntos.items():
            if nome == 'wearanize/cabeca':
                pred, p = prever_loso(X, d['y'], d['id'], cfg.seed)
                detalhe = {}
            else:
                Xt, cobertura = preparar_historico(d)
                pred, p = prever_exportado(modelo, Xt)
                p_sklearn = final.predict_proba(Xt)[:, 1]
                np.testing.assert_allclose(p, p_sklearn, rtol=0, atol=TOLERANCIA)
                np.testing.assert_array_equal(pred, final.predict(Xt))
                detalhe = dict(max_diferenca_probabilidade=float(np.max(np.abs(p - p_sklearn))))
            agregado, locais[nome] = avaliar(d['y'], pred, d['id'], cfg.seed)
            if nome != 'wearanize/cabeca':
                ref = (referencia_ml13 if nome == 'dreamt' else evidencia_ml17 /
                       f'rodadas/depois/ml/experimentos/saida/ml17_rodada/{nome}.json')
                detalhe.update(conferir_reproducao(nome, agregado, locais[nome][0],
                                                    ml13, ml17, ler_json(ref)))
            resultados[nome] = dict(agregado, cobertura=cobertura, reproducao=detalhe)
            np.savez_compressed(saida / (nome.replace('/', '-') + '.npz'), y=d['y'],
                                pred=pred, probabilidade=p, ids=d['id'].astype(str))
            print(nome, len(d['y']), 'épocas', flush=True)
        dourado, paridade = vetor_dourado(final)
    resumo = dict(modelo=VERSAO, commit=codigo, hash_config=cfg.hash, seed=cfg.seed,
                  sha256_manifesto_dreamt=manifesto, resultados=resultados,
                  paridade_angular=paridade, pools=pools, python=platform.python_version(),
                  sistema=platform.system(), bibliotecas={n: importlib.metadata.version(n)
                      for n in ('numpy', 'pandas', 'scipy', 'scikit-learn', 'threadpoolctl')})
    validar_sem_notas(resumo)
    for nome, obj in ((VERSAO, modelo), (VERSAO + '-dourado', dourado), ('agregados-v2', resumo)):
        (saida / f'{nome}.json').write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n',
                                          encoding='utf-8', newline='\n')
    (saida / 'metricas-locais.json').write_text(json.dumps(locais), encoding='utf-8')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for arg in ('evidencia-ml17', 'dados-dreamt', 'referencia-ml13', 'saida'):
        ap.add_argument('--' + arg, type=Path, required=True)
    executar(**vars(ap.parse_args()))


if __name__ == '__main__':
    main()
