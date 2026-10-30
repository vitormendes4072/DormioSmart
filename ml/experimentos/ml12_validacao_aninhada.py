#!/usr/bin/env python3
"""ML-12 — a redução para 3 features sobrevive a uma validação honesta?

    ml/.venv/Scripts/python ml/experimentos/ml12_validacao_aninhada.py

=============================================================================
POR QUE ESTE SCRIPT EXISTE
=============================================================================
O `ML-11` (30/10) achou que três features — `mag_din_media`, `p_frac`,
`d_angulo` — empatam com as oito. Mas escolheu o trio olhando as dobras de
AVALIAÇÃO da base de cabeça, o que é otimista por construção, e o testou fixo
em pulso e Newcastle. Antes de o `DATA-07e` encolher o registro do firmware,
três perguntas:

  (a) ANINHADA. Se a seleção for refeita DENTRO de cada dobra de treino, sem
      nunca ver o sujeito de teste, o procedimento "selecionar e reduzir"
      ainda empata com as oito? E escolhe sempre as mesmas?
  (b) HMM. O pipeline de produto é a logística mais o Viterbi de 2 estados
      (`ML-03b` item 8b). O empate vale também com ele?
  (c) Dado do travesseiro. Não existe ainda (`VIA-01`/`VIA-02`): fica aberto.

E um achado de passagem, medido em vez de anotado:

  (d) CONTEXTO POR SUJEITO. `empilhar_contexto` roda sobre a base inteira
      concatenada, então nas fronteiras entre sujeitos a janela de ±2 épocas
      mistura features de duas pessoas. Acontece em todos os experimentos
      desde o ML-02. Aqui se mede quanto isso move o kappa.

=============================================================================
O PROTOCOLO, DECLARADO ANTES DE RODAR
=============================================================================
- Externa: 10 dobras por sujeito (`GroupKFold`), as mesmas do `ML-11`.
- Interna: 5 dobras por sujeito, só com os sujeitos de TREINO da externa.
- Seleção progressiva na interna, até as 8. Regra de parada: o MENOR conjunto
  cujo kappa interno fica a até 0,005 do melhor kappa interno (parcimônia com
  tolerância, fixada antes de rodar). Também se registra o "primeiro trio"
  da interna, para comparar com o trio do `ML-11`.
- O conjunto escolhido é treinado na externa inteira e avaliado no sujeito de
  teste. Comparação PAREADA por dobra contra as 8, IC 95 % pela t.
- Pipeline: normalização por sujeito + contexto ±2 POR SUJEITO + logística
  balanceada (+ Viterbi em (b)).

=============================================================================
CONTROLE POSITIVO
=============================================================================
Uma seleção que nunca escolhe nada de diferente não prova nada. Na base de
cabeça, acrescenta-se uma coluna-isca que VAZA o rótulo (`y` com 20 % de
ruído). Se a seleção aninhada funciona, ela tem de escolher a isca primeiro em
TODAS as dobras e o kappa tem de saltar. Se não escolher, o instrumento está
quebrado e o resto do resultado não vale.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import cohen_kappa_score, confusion_matrix
from sklearn.model_selection import GroupKFold

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "experimentos"))

from src.epocas import empilhar_contexto              # noqa: E402
from src.features import NOMES_FEATURES               # noqa: E402
from src.modelos import suavizar_hmm, transicoes_hmm  # noqa: E402
from ml11_ablacao_features import (                   # noqa: E402
    SUBCONJUNTOS_DA_CABECA,
    TETO_KAPPA,
    carregar_bases,
    normalizar_por_sujeito,
)

SEED = 20260910
CONTEXTO = 2
N_EXTERNA = 10
N_INTERNA = 5
TOLERANCIA_PARADA = 0.005
TRIO_ML11 = SUBCONJUNTOS_DA_CABECA["3 (cabeça)"]
SAIDA = RAIZ / "experimentos" / "saida"
IDX = {n: i for i, n in enumerate(NOMES_FEATURES)}


# ── pipeline ──────────────────────────────────────────────────────────────

def contexto_por_sujeito(X: np.ndarray, ids: np.ndarray) -> np.ndarray:
    """±2 épocas sem atravessar a fronteira entre sujeitos (d).

    Exige os sujeitos contíguos na matriz, o que o cache garante (conferido
    em 30/10: 92 blocos para 92 sujeitos; 27 para 27).
    """
    partes = []
    inicio = 0
    for fim in list(np.flatnonzero(ids[1:] != ids[:-1]) + 1) + [len(ids)]:
        partes.append(empilhar_contexto(X[inicio:fim], CONTEXTO))
        inicio = fim
    return np.vstack(partes)


def preparar(X, ids, por_sujeito=True):
    Xn = normalizar_por_sujeito(X, ids)
    return contexto_por_sujeito(Xn, ids) if por_sujeito else empilhar_contexto(Xn, CONTEXTO)


def _clf():
    return LogisticRegression(max_iter=2000, class_weight="balanced", random_state=SEED)


def prever(clf, Xte, ids_te, A=None):
    """Logística pura, ou Viterbi por sujeito por cima dela quando há `A`."""
    if A is None:
        return clf.predict(Xte)
    p = clf.predict_proba(Xte)[:, 1]
    pred = np.empty(len(p), dtype=int)
    for s in np.unique(ids_te):
        m = ids_te == s
        pred[m] = suavizar_hmm(p[m], A)
    return pred


def metricas(y, p):
    tn, fp, fn, tp = confusion_matrix(y, p, labels=[0, 1]).ravel()
    return (cohen_kappa_score(y, p),
            tn / (tn + fp) if tn + fp else np.nan,
            tp / (tp + fn) if tp + fn else np.nan)


def kappa_interno(Xc_cols, y, ids):
    """Kappa médio da validação INTERNA, só sobre o treino da externa."""
    ks = []
    for tr, te in GroupKFold(n_splits=N_INTERNA).split(Xc_cols, y, groups=ids):
        clf = _clf().fit(Xc_cols[tr], y[tr])
        ks.append(cohen_kappa_score(y[te], clf.predict(Xc_cols[te])))
    return float(np.mean(ks))


def colunas_de(nomes, n_feat):
    """Colunas do bloco de contexto (5 cópias de n_feat) das features pedidas."""
    blocos = 2 * CONTEXTO + 1
    return [b * n_feat + IDX_LOCAL[n] for b in range(blocos) for n in nomes]


IDX_LOCAL = dict(IDX)


def selecao_interna(Xc, y, ids, nomes_disponiveis, n_feat):
    escolhidas, restantes, trilha = [], list(nomes_disponiveis), []
    while restantes:
        melhor = None
        for f in restantes:
            k = kappa_interno(Xc[:, colunas_de(escolhidas + [f], n_feat)], y, ids)
            if melhor is None or k > melhor[1]:
                melhor = (f, k)
        escolhidas.append(melhor[0])
        restantes.remove(melhor[0])
        trilha.append({"conjunto": list(escolhidas), "kappa_interno": melhor[1]})
    topo = max(t["kappa_interno"] for t in trilha)
    parada = next(t for t in trilha if t["kappa_interno"] >= topo - TOLERANCIA_PARADA)
    return parada["conjunto"], trilha


def ic95(d):
    d = np.asarray(d, float)
    m = float(d.mean())
    h = float(stats.t.ppf(0.975, len(d) - 1) * d.std(ddof=1) / np.sqrt(len(d)))
    return [m, m - h, m + h]


# ── os experimentos ──────────────────────────────────────────────────────────

def rodar_base(nome, X, y, ids, nomes):
    n_feat = X.shape[1]
    Xc = preparar(X, ids, por_sujeito=True)
    todas = list(nomes)
    r = {"kappa": {}, "especificidade": {}, "selecionados": [], "trilhas": []}

    def guardar(rotulo, k, e):
        r["kappa"].setdefault(rotulo, []).append(float(k))
        r["especificidade"].setdefault(rotulo, []).append(float(e))

    for dobra, (tr, te) in enumerate(GroupKFold(n_splits=N_EXTERNA).split(Xc, y, groups=ids)):
        t0 = time.time()
        escolhido, trilha = selecao_interna(Xc[tr], y[tr], ids[tr], todas, n_feat)
        primeiro_trio = trilha[2]["conjunto"] if len(trilha) >= 3 else escolhido
        r["selecionados"].append(escolhido)
        r["trilhas"].append(trilha)
        A, _ = transicoes_hmm(y[tr], ids[tr])

        for rotulo, conj in (("as 8", todas), ("aninhada", escolhido),
                             ("primeiro trio interno", primeiro_trio),
                             ("trio do ML-11", [n for n in TRIO_ML11 if n in todas])):
            cols = colunas_de(conj, n_feat)
            clf = _clf().fit(Xc[tr][:, cols], y[tr])
            for sufixo, matriz in (("", None), (" + HMM", A)):
                p = prever(clf, Xc[te][:, cols], ids[te], matriz)
                k, e, _ = metricas(y[te], p)
                guardar(rotulo + sufixo, k, e)
        print(f"  dobra {dobra}: escolheu {escolhido}  ({time.time() - t0:.0f} s)",
              flush=True)

    # (d) contexto global (o de todos os experimentos anteriores) contra por sujeito
    Xg = preparar(X, ids, por_sujeito=False)
    for tr, te in GroupKFold(n_splits=N_EXTERNA).split(Xg, y, groups=ids):
        clf = _clf().fit(Xg[tr], y[tr])
        k, e, _ = metricas(y[te], clf.predict(Xg[te]))
        guardar("as 8, contexto global", k, e)

    ref, ref_e = np.array(r["kappa"]["as 8"]), np.array(r["especificidade"]["as 8"])
    ref_h, ref_he = (np.array(r["kappa"]["as 8 + HMM"]),
                     np.array(r["especificidade"]["as 8 + HMM"]))
    r["resumo"] = {}
    for rotulo, ks in r["kappa"].items():
        base_k, base_e = (ref_h, ref_he) if rotulo.endswith("+ HMM") else (ref, ref_e)
        ks = np.array(ks)
        es = np.array(r["especificidade"][rotulo])
        r["resumo"][rotulo] = {
            "kappa_medio": float(ks.mean()), "frac_teto": float(ks.mean() / TETO_KAPPA),
            "especificidade_media": float(np.nanmean(es)),
            "dkappa": ic95(ks - base_k), "despecificidade": ic95(es - base_e)}
    freq = {n: sum(n in s for s in r["selecionados"]) for n in todas}
    r["frequencia_de_selecao"] = freq
    r["tamanhos_escolhidos"] = [len(s) for s in r["selecionados"]]
    return r


def controle_positivo(X, y, ids):
    """Isca que vaza o rótulo: a seleção aninhada tem de achá-la sempre."""
    rng = np.random.default_rng(SEED)
    isca = np.where(rng.random(len(y)) < 0.2, 1 - y, y).astype(float)
    Xi = np.column_stack([X, isca])
    nomes = list(NOMES_FEATURES) + ["ISCA"]
    IDX_LOCAL["ISCA"] = X.shape[1]
    Xc = preparar(Xi, ids, por_sujeito=True)
    primeiros = []
    for tr, te in GroupKFold(n_splits=N_EXTERNA).split(Xc, y, groups=ids):
        # Só o primeiro passo da seleção: é ele que tem de ser a isca.
        melhor = max(nomes, key=lambda f: kappa_interno(
            Xc[tr][:, colunas_de([f], Xi.shape[1])], y[tr], ids[tr]))
        primeiros.append(melhor)
    del IDX_LOCAL["ISCA"]
    return primeiros


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    bases = carregar_bases()
    if not bases:
        print("Nenhuma base em disco.")
        return 1
    resultado = {"experimento": "ML-12 validação aninhada", "seed": SEED,
                 "n_externa": N_EXTERNA, "n_interna": N_INTERNA,
                 "tolerancia_parada": TOLERANCIA_PARADA, "trio_ml11": list(TRIO_ML11),
                 "teto_kappa": TETO_KAPPA, "bases": {}}

    print("===== controle positivo (cabeça, isca que vaza o rótulo) =====", flush=True)
    X, y, ids, _ = bases["wearanize/cabeca"]
    primeiros = controle_positivo(X, y, ids)
    acertos = sum(p == "ISCA" for p in primeiros)
    print(f"  a isca foi a primeira escolha em {acertos}/{N_EXTERNA} dobras: {primeiros}")
    resultado["controle_positivo"] = {"primeiras_escolhas": primeiros,
                                      "acertos": acertos}
    if acertos != N_EXTERNA:
        print("  ✗ O INSTRUMENTO NÃO ACHA UMA FEATURE QUE VAZA O RÓTULO. Parando.")
        return 1

    for nome, (X, y, ids, _) in bases.items():
        t0 = time.time()
        print(f"\n===== {nome} — {len(y)} épocas, {len(np.unique(ids))} sujeitos =====",
              flush=True)
        r = rodar_base(nome, X, y, ids, NOMES_FEATURES)
        r["segundos"] = time.time() - t0
        resultado["bases"][nome] = r
        for rot, v in r["resumo"].items():
            dk = v["dkappa"]
            print(f"  {rot:28s} κ={v['kappa_medio']:.4f} ({v['frac_teto'] * 100:3.0f} %)"
                  f"  Δκ={dk[0]:+.4f} [{dk[1]:+.4f}; {dk[2]:+.4f}]"
                  f"  espec={v['especificidade_media']:.3f}"
                  f"  Δespec={v['despecificidade'][0]:+.4f}")
        print(f"  tamanhos escolhidos: {r['tamanhos_escolhidos']}")
        print(f"  frequência de seleção: {r['frequencia_de_selecao']}")

    SAIDA.mkdir(parents=True, exist_ok=True)
    destino = SAIDA / "ml12_validacao_aninhada.json"
    destino.write_text(json.dumps(resultado, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\ngravado em {destino.relative_to(RAIZ.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
