"""Executa o protocolo ML-18 e publica somente agregados."""

import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess

import numpy as np
from sklearn.metrics import cohen_kappa_score, roc_auc_score
from threadpoolctl import threadpool_limits

from experimentos.analise_vigilia_por_noite import metricas_por_epoca, por_noite
from experimentos.ml_inf_v2 import ajustar, preparar_historico, prever_exportado
from experimentos.ml_inf import ML, dados_ml17
from src.carregar.dreamt import carregar_features_dreamt
from src.configuracao import carregar_config

BASES = ("wearanize/cabeca", "wearanize/pulso", "walch_principal", "dreamt", "newcastle")
EXTERNAS = BASES[2:]
SEED_MODELO = 20260910
SEED_BOOTSTRAP = 20261123
SEED_PERMUTACAO = 18112026
REAMOSTRAS = 2000
PERMUTACOES = 20
CRITERIO = ("especificidade", "kappa", "sensibilidade")
METRICAS = (*CRITERIO, "f1_vigilia", "auc")
MODELO = ML / "modelos/ml-inf-cabeca-v2.json"


def familia(base):
    return base.split("/")[0]


def bases_de_treino(teste):
    return tuple(base for base in BASES if familia(base) != familia(teste))


def identidades(base, dados):
    return {(familia(base), str(pessoa)) for pessoa in np.unique(dados["id"])}


def conferir_separacao(treino, teste):
    intersecao = treino & teste
    if intersecao:
        raise ValueError(f"{len(intersecao)} participante(s) no treino e no teste")


def melhorou(delta):
    return (
        delta["especificidade"] >= .05
        and delta["kappa"] >= 0
        and delta["sensibilidade"] >= -.02
    )


def embaralhar(grupos, divisao, rodada):
    rng = np.random.default_rng(np.random.SeedSequence([SEED_PERMUTACAO, divisao, rodada]))
    return np.concatenate([rng.permutation(y) for y in grupos])


def classes(prob):
    return (prob > .5).astype(int)


def resumir(y, prob, noites):
    pred = classes(prob)
    return {
        "por_epoca": {
            **metricas_por_epoca(y, pred),
            "kappa": float(cohen_kappa_score(y, pred)),
            "auc": float(roc_auc_score(y, prob)),
        },
        "por_noite": por_noite(y, pred, noites),
    }


def numeros_confusao(contagens):
    vn, fp, fn, vp = contagens.T.astype(float)
    n = vn + fp + fn + vp
    acerto = (vn + vp) / n
    acaso = ((vn + fp) * (vn + fn) + (vp + fn) * (vp + fp)) / n**2
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.column_stack((
            vn / (vn + fp), (acerto - acaso) / (1 - acaso), vp / (vp + fn),
            2 * vn / (2 * vn + fn + fp),
        ))


def auc_ponderada(y, prob, pessoas, pesos):
    """Mann–Whitney com peso por pessoa e meio acerto para empates."""
    ordem = np.argsort(prob)
    p, rotulo, grupo = prob[ordem], y[ordem], pessoas[ordem]
    inicio = np.r_[0, np.flatnonzero(np.diff(p)) + 1]
    positivo = rotulo == 1
    ap, an = inicio, inicio
    indice = np.searchsorted(inicio, np.arange(len(p)), side="right") - 1
    gp, gn = grupo[positivo], grupo[~positivo]
    ip, ine = indice[positivo], indice[~positivo]
    auc = []
    for amostra in pesos:
        pos = np.bincount(ip, weights=amostra[gp], minlength=len(ap))
        neg = np.bincount(ine, weights=amostra[gn], minlength=len(an))
        total = pos.sum() * neg.sum()
        auc.append(pos @ (np.cumsum(neg) - .5 * neg) / total if total else np.nan)
    return np.asarray(auc)


def bootstrap_epocas(y, ref, conjunto, pessoas, indice, repeticoes=REAMOSTRAS):
    _, grupo = np.unique(pessoas, return_inverse=True)
    n = int(grupo.max()) + 1
    rng = np.random.default_rng(np.random.SeedSequence([SEED_BOOTSTRAP, indice]))
    pesos = rng.multinomial(n, np.full(n, 1 / n), size=repeticoes)

    def calcular(prob):
        quem = np.bincount(grupo * 4 + y * 2 + classes(prob), minlength=n * 4).reshape(n, 4)
        return np.column_stack((numeros_confusao(pesos @ quem), auc_ponderada(y, prob, grupo, pesos)))

    return calcular(conjunto) - calcular(ref)


def intervalo(amostras):
    validas = amostras[np.isfinite(amostras)]
    return {
        "ic95": np.percentile(validas, [2.5, 97.5]).tolist() if len(validas) else None,
        "reamostras_validas": len(validas),
    }


def delta_noite(antigo, novo):
    chaves = ("vies_tst_min", "fracao_erro_acima_60_min", "correlacao_vigilia_entre_noites")
    deltas = {k: novo[k] - antigo[k] for k in chaves}
    deltas["limites_95_min"] = (np.asarray(novo["limites_95_min"]) - antigo["limites_95_min"]).tolist()
    return deltas


def delta_kappa_individual(y, ref, conjunto, ids):
    validos = []
    for pessoa in np.unique(ids):
        linhas = ids == pessoa
        rotulos = y[linhas]
        r, c = classes(ref[linhas]), classes(conjunto[linhas])
        # Em caso degenerado, kappa é indefinido. A contagem permanece explícita.
        if any(np.unique(np.r_[rotulos, p]).size < 2 for p in (r, c)):
            continue
        validos.append(float(cohen_kappa_score(rotulos, c) - cohen_kappa_score(rotulos, r)))
    return {
        "pessoas_validas": len(validos),
        "media": float(np.mean(validos)) if validos else None,
        "maior_modulo": max(map(abs, validos), default=None),
        "minimo": min(validos, default=None),
        "maximo": max(validos, default=None),
    }


def noite_ids(dados):
    _, ids = np.unique(
        np.column_stack((dados["id"], np.broadcast_to(dados["gravacao"], dados["id"].shape))).astype(str),
        axis=0, return_inverse=True,
    )
    return ids.ravel()


def censo(dados):
    return {
        "pessoas": len(np.unique(dados["id"])),
        "noites": len(np.unique(noite_ids(dados))),
        "epocas": len(dados["y"]),
        "epocas_vigilia": int((dados["y"] == 0).sum()),
    }


def prever_referencia(base, dados, x, modelo, cabeca, x_cabeca):
    if base in EXTERNAS:
        return prever_exportado(modelo, x)[1]
    ids = dados["id"].astype(str)
    ids_cabeca = cabeca["id"].astype(str)
    prob = np.empty(len(ids))
    for pessoa in np.unique(ids):
        treino, teste = ids_cabeca != pessoa, ids == pessoa
        conferir_separacao({("wearanize", i) for i in np.unique(ids_cabeca[treino])}, {("wearanize", pessoa)})
        prob[teste] = ajustar(x_cabeca[treino], cabeca["y"][treino], SEED_MODELO).predict_proba(x[teste])[:, 1]
    return prob


def comparar(base, todos, preparados, modelo, cabeca, x_cabeca, qualidade_dreamt):
    dados = todos[base]
    y, x = dados["y"], preparados[base]
    nomes = bases_de_treino(base)
    ids_treino = set().union(*(identidades(n, todos[n]) for n in nomes))
    conferir_separacao(ids_treino, identidades(base, dados))
    xt = np.concatenate([preparados[n] for n in nomes])
    grupos = [todos[n]["y"] for n in nomes]
    yt = np.concatenate(grupos)
    prob = ajustar(xt, yt, SEED_MODELO).predict_proba(x)[:, 1]
    ref = prever_referencia(base, dados, x, modelo, cabeca, x_cabeca)
    noites = noite_ids(dados)
    a, b = resumir(y, ref, noites), resumir(y, prob, noites)
    delta = {k: b["por_epoca"][k] - a["por_epoca"][k] for k in METRICAS}
    print(f"{base}: referência e conjunto avaliados. Controles e bootstrap.", flush=True)
    indice = BASES.index(base)
    # Os dois testes Wearanize compartilham a divisão e o conjunto de permutações.
    divisao = 0 if familia(base) == "wearanize" else indice - 1
    aucs = []
    for i in range(PERMUTACOES):
        treino_permutado = embaralhar(grupos, divisao, i)
        controle = ajustar(xt, treino_permutado, SEED_MODELO).predict_proba(x)[:, 1]
        aucs.append(float(roc_auc_score(y, controle)))
    boot = bootstrap_epocas(y, ref, prob, dados["id"], indice)
    cobertura = censo(dados)
    if base == "dreamt":
        cobertura["qualidade_carregamento"] = qualidade_dreamt
    resultado = dict(
        cobertura=cobertura, treino={
            n: {**censo(todos[n]), "fracao_epocas": len(todos[n]["y"]) / len(yt)} for n in nomes
        }, pessoas_distintas_no_treino=len(ids_treino),
        referencia=a, conjunto=b, delta_por_epoca=delta,
        delta_por_noite=delta_noite(a["por_noite"], b["por_noite"]),
        delta_kappa_por_pessoa=delta_kappa_individual(y, ref, prob, dados["id"]),
        ic_delta_por_epoca={k: intervalo(boot[:, i]) for i, k in enumerate(METRICAS)},
        controle_permutado={
            "auc_media": float(np.mean(aucs)), "auc_min": min(aucs), "auc_max": max(aucs),
            "auc_dp": float(np.std(aucs, ddof=1)),
        },
        melhorou=melhorou(delta),
    )
    return resultado, boot


def sha256(caminho):
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def serializavel(valor):
    if isinstance(valor, dict):
        return {k: serializavel(v) for k, v in valor.items()}
    if isinstance(valor, list):
        return [serializavel(v) for v in valor]
    if isinstance(valor, float) and not np.isfinite(valor):
        return None
    return valor


def executar(cache, dreamt):
    cfg = carregar_config()
    if (cfg.hash, cfg.seed, cfg.taxa_comum_hz, cfg.epoca_s) != ("aec203907e6f", SEED_MODELO, 32, 30):
        raise ValueError("configuração difere do v2")
    ref_ml13 = json.loads((ML / "experimentos/saida/ml13/agregados.json").read_text(encoding="utf-8"))
    hash_dreamt = sha256(dreamt / "SHA256SUMS.txt")
    if hash_dreamt != ref_ml13["sha256_manifesto_dreamt"]:
        raise ValueError("manifesto difere do conferido na ML-13")
    todos, _ = dados_ml17(cache, cfg, temporal=True, incluir_pulso=True)
    print("Caches ML-17 conferidos. Extraindo DREAMT.", flush=True)
    todos["dreamt"], qualidade, _ = carregar_features_dreamt(dreamt, cfg)
    if qualidade != {k: v for k, v in ref_ml13["qualidade"].items() if k != "segmentos"}:
        raise ValueError("a cobertura DREAMT difere da ML-13")
    preparados = {n: preparar_historico(todos[n])[0] for n in BASES}
    modelo = json.loads(MODELO.read_text(encoding="utf-8"))
    resultados, boots = {}, {}
    for base in BASES:
        resultados[base], boots[base] = comparar(
            base, todos, preparados, modelo, todos[BASES[0]], preparados[BASES[0]], qualidade,
        )
        print(f"{base}: concluída.", flush=True)
    delta = {k: float(np.mean([resultados[n]["delta_por_epoca"][k] for n in EXTERNAS])) for k in CRITERIO}
    amostras = np.mean([boots[n][:, :len(CRITERIO)] for n in EXTERNAS], axis=0)
    return serializavel(dict(
        procedencia={
            "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ML, encoding="utf-8").strip(),
            "python": platform.python_version(), "sistema": platform.system(), "hash_config": cfg.hash,
            "modelo_sha256": sha256(MODELO), "manifesto_dreamt_sha256": hash_dreamt,
            "manifesto_ml17_sha256": sha256(ML / "experimentos/saida/ml17/manifesto.json"),
            "semente_modelo": SEED_MODELO, "semente_bootstrap": SEED_BOOTSTRAP,
            "semente_permutacao": SEED_PERMUTACAO, "reamostras": REAMOSTRAS, "permutacoes": PERMUTACOES,
        },
        bases=resultados, media_externa={
            "bases": list(EXTERNAS), "delta": delta, "melhorou": melhorou(delta),
            "ic_delta": {k: intervalo(amostras[:, i]) for i, k in enumerate(CRITERIO)},
        },
    ))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cache-ml17", required=True, type=Path)
    p.add_argument("--dreamt", required=True, type=Path)
    p.add_argument("--saida", required=True, type=Path)
    args = p.parse_args()
    if args.saida.exists():
        p.error("a saída já existe")
    with threadpool_limits(limits=1):
        resultado = executar(args.cache_ml17, args.dreamt)
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    with args.saida.open("x", encoding="utf-8") as arq:
        arq.write(json.dumps(resultado, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
