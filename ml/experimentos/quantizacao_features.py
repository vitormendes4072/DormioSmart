#!/usr/bin/env python3
"""Custo em kappa de quantizar as features para ponto fixo (DATA-07b).

    python3 ml/experimentos/quantizacao_features.py [n_dobras]

A pergunta: o firmware precisa guardar cada feature em `float32` (4 bytes), ou
16 bits de ponto fixo bastam? Isso decide o tamanho do registro de época, que
decide a autonomia offline do aparelho — ver `docs/DECISAO-BUFFER-E-FEATURES.md`.

**A resposta é medida, não argumentada.** Quantiza-se a matriz de features das
bases reais, propaga-se pelo MESMO pipeline do produto (normalização por
sujeito + contexto ±2 + regressão logística balanceada, que é a configuração
que o `ML-03b` item 5 estabeleceu) e compara-se kappa **pareado por dobra**
contra `float64`. Pareado porque o que interessa é o efeito da quantização, não
a variância entre dobras, que é uma ordem de grandeza maior.

⚠️ O argumento de que "float de 32 bits é precisão desperdiçada contra um piso
de ruído de 0,64 mg" está certo, mas ele sozinho não fecha a questão: features
derivadas (desvio, máximo, fração acima de limiar) não herdam o piso da entrada
de forma óbvia, e o classificador vê as oito juntas depois de normalizar por
sujeito. Por isso se mede.
"""

from __future__ import annotations

import json
import pickle
import sys
import time
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import cohen_kappa_score, confusion_matrix
from sklearn.model_selection import GroupKFold

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from src.epocas import empilhar_contexto              # noqa: E402
from src.features import NOMES_FEATURES               # noqa: E402

SEED = 20260910
CONTEXTO = 2                     # ml/config.yaml: contexto_epocas
CACHE_WEARANIZE = RAIZ / "dados" / "processado" / "_cache_base_wearanize_14646b9aacb7d397.pkl"
DIR_NEWCASTLE = RAIZ / "dados" / "processado" / "newcastle_features"
SAIDA = RAIZ / "experimentos" / "saida"

# ──────────────────────────────────────────────────────────────────────────
# Esquema de ponto fixo
# ──────────────────────────────────────────────────────────────────────────
# Fundo de escala por feature, em unidade física. Os fundos foram escolhidos
# com folga sobre o MÁXIMO OBSERVADO nas três bases, e não sobre o máximo
# teórico: um fundo apertado satura, um fundo folgado demais gasta passo.
#
#   feature          fundo   máx. observado (wearanize cabeça/pulso + newcastle)
#   enmo_media        1 g     0,2394
#   enmo_desvio       1 g     0,5467
#   enmo_max         16 g     6,4434   (teto físico ~12,9 g em fundo de ±8 g)
#   mag_din_media     2 g     0,8596
#   inclinacao_rel  180 °   179,3015
#   d_angulo        180 °   175,6912
#
# `zcr` e `p_frac` NÃO entram na tabela: são frações de uma contagem de
# amostras (0..959 numa época de 30 s a 32 Hz). Guardadas como a contagem
# inteira, cabem em `uint16` **sem perda nenhuma**, por construção — não é
# quantização, é a representação exata.
ESCALAS = {
    "enmo_media": 1.0,
    "enmo_desvio": 1.0,
    "enmo_max": 16.0,
    "mag_din_media": 2.0,
    "inclinacao_rel": 180.0,
    "d_angulo": 180.0,
}
EXATAS_EM_U16 = ("zcr", "p_frac")
N_AMOSTRAS_POR_EPOCA = 960       # 32 Hz × 30 s


def quantizar(X: np.ndarray, bits: int) -> np.ndarray:
    """Quantiza e des-quantiza, para propagar o erro pelo pipeline."""
    n_niveis = (1 << bits) - 1
    Xq = X.copy()
    for i, nome in enumerate(NOMES_FEATURES):
        if nome in EXATAS_EM_U16:
            if bits >= 16:
                continue          # a contagem cabe: sem perda
            Xq[:, i] = np.round(X[:, i] * n_niveis) / n_niveis
            continue
        fe = ESCALAS[nome]
        q = np.clip(np.round(X[:, i] / fe * n_niveis), 0, n_niveis)
        Xq[:, i] = q * fe / n_niveis
    return Xq


def normalizar_por_sujeito(X: np.ndarray, ids: np.ndarray) -> np.ndarray:
    """z-score por sujeito — a base do produto desde o ML-03b item 5."""
    Xn = np.empty_like(X, dtype=float)
    for s in np.unique(ids):
        m = ids == s
        mu, sd = X[m].mean(axis=0), X[m].std(axis=0, ddof=1)
        sd[sd < 1e-9] = 1.0
        Xn[m] = (X[m] - mu) / sd
    return Xn


def avaliar(X, y, ids, n_dobras):
    Xc = empilhar_contexto(normalizar_por_sujeito(X, ids), CONTEXTO)
    ks, es, ss = [], [], []
    for tr, te in GroupKFold(n_splits=n_dobras).split(Xc, y, groups=ids):
        clf = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=SEED)
        clf.fit(Xc[tr], y[tr])
        p = clf.predict(Xc[te])
        ks.append(cohen_kappa_score(y[te], p))
        tn, fp, fn, tp = confusion_matrix(y[te], p, labels=[0, 1]).ravel()
        es.append(tn / (tn + fp) if tn + fp else np.nan)
        ss.append(tp / (tp + fn) if tp + fn else np.nan)
    return np.array(ks), np.array(es), np.array(ss)


def carregar_bases():
    bases = {}
    if CACHE_WEARANIZE.exists():
        d = pickle.load(open(CACHE_WEARANIZE, "rb"))
        for pos in ("pulso", "cabeca"):
            if pos in d:
                bases[f"wearanize/{pos}"] = (
                    d[pos]["X"], np.asarray(d[pos]["y"]), np.asarray(d[pos]["id"]))
    arquivos = sorted(DIR_NEWCASTLE.glob("*.npz")) if DIR_NEWCASTLE.exists() else []
    if arquivos:
        Xs, ys, ids = [], [], []
        for f in arquivos:
            z = np.load(f, allow_pickle=True)
            Xs.append(z["X"]); ys.append(z["y"])
            ids.append(np.repeat(str(z["id"]), len(z["y"])))
        X, y, i = np.vstack(Xs), np.concatenate(ys), np.concatenate(ids)
        m = y >= 0
        bases["newcastle"] = (X[m], y[m], i[m])
    return bases


def main() -> int:
    n_dobras = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    bases = carregar_bases()
    if not bases:
        print("Nenhuma base em disco. Este experimento exige as features já extraídas.")
        return 1

    resultado = {"seed": SEED, "n_dobras": n_dobras, "contexto": CONTEXTO,
                 "escalas": ESCALAS, "exatas_em_u16": list(EXATAS_EM_U16),
                 "n_amostras_por_epoca": N_AMOSTRAS_POR_EPOCA, "bases": {}}

    for nome, (X, y, ids) in bases.items():
        print(f"\n===== {nome} — {len(y)} épocas, {len(np.unique(ids))} sujeitos, "
              f"{n_dobras} dobras =====")
        res = {}
        for rotulo, Xv in [("float64", X), ("u16", quantizar(X, 16)),
                           ("u12", quantizar(X, 12)), ("u10", quantizar(X, 10)),
                           ("u8", quantizar(X, 8))]:
            t0 = time.time()
            k, e, s = avaliar(Xv, y, ids, n_dobras)
            res[rotulo] = {"kappa": k.tolist(), "especificidade": e.tolist(),
                           "sensibilidade": s.tolist()}
            print(f"  {rotulo:8s} kappa={k.mean():.4f}±{k.std(ddof=1):.4f}"
                  f"  espec={e.mean():.4f}  sens={s.mean():.4f}  ({time.time()-t0:.0f}s)")
        kf = np.array(res["float64"]["kappa"])
        ef = np.array(res["float64"]["especificidade"])
        print("  --- diferença PAREADA por dobra, contra float64 ---")
        for rotulo in ("u16", "u12", "u10", "u8"):
            dk = np.array(res[rotulo]["kappa"]) - kf
            de = np.array(res[rotulo]["especificidade"]) - ef
            res[rotulo]["dkappa_medio"] = float(dk.mean())
            res[rotulo]["dkappa_max_abs"] = float(np.abs(dk).max())
            res[rotulo]["despecificidade_medio"] = float(de.mean())
            print(f"    {rotulo:5s} Δκ={dk.mean():+.5f} (máx |Δκ|={np.abs(dk).max():.5f})"
                  f"   Δespec={de.mean():+.5f}")
        resultado["bases"][nome] = res

    SAIDA.mkdir(parents=True, exist_ok=True)
    destino = SAIDA / "quantizacao_features.json"
    destino.write_text(json.dumps(resultado, indent=1), encoding="utf-8")
    print(f"\ngravado em {destino.relative_to(RAIZ.parent)}")

    print("\nLEITURA")
    print("-------")
    print("Escala de comparação: o teto entre pontuadores humanos é κ = 0,612 (ML-05)")
    print("e o ganho da suavização por HMM foi Δκ = +0,123 (ML-03b item 8b). Um Δκ da")
    print("ordem de 1e-4 é ruído numérico diante dos dois.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
