#!/usr/bin/env python3
"""ML-11 — quais das 8 features carregam a informação, e o que cada
arquitetura do ARQ-01 consegue entregar ao modelo.

    ml/.venv/Scripts/python ml/experimentos/ml11_ablacao_features.py [n_dobras]

=============================================================================
POR QUE ESTE SCRIPT EXISTE
=============================================================================
O `ARQ-01` (ver `docs/DECISAO-ARQ-01-CADENCIA.md`) compara arquiteturas de
captação pelo que elas custam em corrente. Falta o outro eixo: o que cada uma
**entrega ao modelo**. A pergunta do autor, em 29/10: *"todas essas features
são necessárias, ou há alguma que pode ser eliminada sem grandes perdas?"*

Nenhum experimento anterior retirou feature. O `ML-03b` mexeu em escala,
normalização, limiar e contexto; o de quantização mexeu em bits. Este mede.

=============================================================================
O QUE É MEDIDO
=============================================================================
Sempre o MESMO pipeline do produto (o do `quantizacao_features.py`):
normalização por sujeito + contexto ±2 épocas + regressão logística
balanceada, `GroupKFold` por sujeito. O que muda é só QUAIS colunas entram.
Toda diferença é **pareada por dobra** contra as 8 features, com IC de 95 %
pela t de Student sobre as dobras — a variância entre dobras é uma ordem de
grandeza maior que os efeitos, e pareando ela se cancela.

  1. Tirar UMA feature de cada vez (8 configurações).
  2. Seleção progressiva: começar do zero e, a cada passo, somar a feature
     que mais aumenta o kappa. Diz quantas bastam.
  3. Os conjuntos que cada ARQUITETURA consegue produzir:

     C2  sono leve + FIFO         as 8
     DISP só o que o dispositivo   as 6 intra-época (sem `inclinacao_rel` e
          calcula                  `d_angulo`, que o servidor deriva)
     POST só postura               `inclinacao_rel`, `d_angulo`
     WOMb WoM binário              1 coluna: houve movimento acima do limiar
                                   na época? (`p_frac > 0`)
     WOMb+POST  WoM + 1 leitura de gravidade por época  — LIMITE INFERIOR
     PF+POST    `p_frac` + postura                       — LIMITE SUPERIOR
     CONT  contagem de atividade   a coluna `c` do cache: o substituto de
          clássica                 *activity count* do ML-02 (banda 0,25–3 Hz)

  4. O subconjunto que a seleção progressiva escolheu NA CABEÇA (rodada de
     30/10), FIXO, avaliado nas outras bases. A seleção progressiva escolhe e
     mede nos mesmos dados, então o kappa dela é otimista; avaliar o conjunto
     fixo numa base que não participou da escolha é o teste honesto. Na
     própria cabeça o número continua otimista, e o JSON marca isso.

=============================================================================
⚠️ O QUE OS PROXIES DO WoM SÃO, E O QUE NÃO SÃO
=============================================================================
O cache tem features, não sinal bruto; reprocessar 46 GB para simular o
circuito de detecção de movimento do MPU6050 não cabe neste experimento.
Então o WoM é CERCADO por dois proxies, e o valor real fica entre eles:

  - **Inferior (`WOMb`)**: só "houve evento na época", com o limiar do
    projeto (1,2 m/s² sobre a aceleração dinâmica, o mesmo de `p_frac`). É o
    mínimo que qualquer firmware de WoM entrega.
  - **Superior (`p_frac`)**: a fração de amostras acima do limiar a 32 Hz. Um
    WoM que contasse despertares por época teria no máximo esta resolução —
    na prática menos (cada despertar segura o ESP32 ~0,5 s, Z.4.4).

E a postura com uma leitura por época é aproximada pelas features de postura
do cache, que usam a época inteira: com uma amostra só, o vetor de gravidade
leva junto a aceleração dinâmica daquele instante. É, portanto, OTIMISTA.

O circuito do MPU6050 detecta movimento pela diferença entre amostras
(passa-alta), não pela magnitude sem a gravidade; o limiar equivalente não é
o mesmo número. Isso fica para a parte (c) do `ARQ-01` medir.
"""

from __future__ import annotations

import json
import pickle
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

from src.epocas import empilhar_contexto              # noqa: E402
from src.features import NOMES_FEATURES               # noqa: E402

SEED = 20260910
CONTEXTO = 2                     # ml/config.yaml: contexto_epocas
CACHE_WEARANIZE = RAIZ / "dados" / "processado" / "_cache_base_wearanize_14646b9aacb7d397.pkl"
DIR_NEWCASTLE = RAIZ / "dados" / "processado" / "newcastle_features"
SAIDA = RAIZ / "experimentos" / "saida"

# Teto entre pontuadores humanos (ML-05) — a régua para ler os Δκ.
TETO_KAPPA = 0.612

IDX = {n: i for i, n in enumerate(NOMES_FEATURES)}
POSTURA = ("inclinacao_rel", "d_angulo")

# Escolhidos pela seleção progressiva na base de cabeça (rodada de 30/10). FIXOS
# de propósito: mudar aqui sem rodar de novo a seleção quebra a procedência.
SUBCONJUNTOS_DA_CABECA = {
    "3 (cabeça)": ("mag_din_media", "p_frac", "d_angulo"),
    "4 (cabeça)": ("mag_din_media", "p_frac", "d_angulo", "enmo_media"),
}


def normalizar_por_sujeito(X: np.ndarray, ids: np.ndarray) -> np.ndarray:
    """z-score por sujeito — a base do produto desde o ML-03b item 5."""
    Xn = np.empty_like(X, dtype=float)
    for s in np.unique(ids):
        m = ids == s
        mu, sd = X[m].mean(axis=0), X[m].std(axis=0, ddof=1)
        sd[~np.isfinite(sd) | (sd < 1e-9)] = 1.0
        Xn[m] = (X[m] - mu) / sd
    return Xn


def avaliar(X: np.ndarray, y: np.ndarray, ids: np.ndarray,
            n_dobras: int) -> dict[str, np.ndarray]:
    Xc = empilhar_contexto(normalizar_por_sujeito(X, ids), CONTEXTO)
    ks, es, ss = [], [], []
    for tr, te in GroupKFold(n_splits=n_dobras).split(Xc, y, groups=ids):
        clf = LogisticRegression(max_iter=2000, class_weight="balanced",
                                 random_state=SEED)
        clf.fit(Xc[tr], y[tr])
        p = clf.predict(Xc[te])
        ks.append(cohen_kappa_score(y[te], p))
        tn, fp, fn, tp = confusion_matrix(y[te], p, labels=[0, 1]).ravel()
        es.append(tn / (tn + fp) if tn + fp else np.nan)
        ss.append(tp / (tp + fn) if tp + fn else np.nan)
    return {"kappa": np.array(ks), "especificidade": np.array(es),
            "sensibilidade": np.array(ss)}


def ic95_pareado(a: np.ndarray, b: np.ndarray) -> tuple[float, float, float]:
    """Média e IC 95 % de (a − b), pareado por dobra."""
    d = a - b
    m = float(d.mean())
    h = float(stats.t.ppf(0.975, len(d) - 1) * d.std(ddof=1) / np.sqrt(len(d)))
    return m, m - h, m + h


def colunas(X: np.ndarray, nomes: tuple[str, ...]) -> np.ndarray:
    return X[:, [IDX[n] for n in nomes]]


def conjuntos_de_arquitetura(X: np.ndarray, c: np.ndarray) -> dict[str, np.ndarray]:
    womb = (X[:, IDX["p_frac"]] > 0).astype(float)[:, None]
    post = colunas(X, POSTURA)
    return {
        "C2 (as 8)": X,
        "DISP (6 intra-época)": X[:, :6],
        "POST (só postura)": post,
        "WOMb (WoM binário)": womb,
        "WOMb+POST (inferior)": np.hstack([womb, post]),
        "PF+POST (superior)": np.hstack([colunas(X, ("p_frac",)), post]),
        "CONT (contagem clássica)": c[:, None],
    }


def selecao_progressiva(X, y, ids, n_dobras) -> list[dict]:
    escolhidas: list[str] = []
    restantes = list(NOMES_FEATURES)
    passos = []
    while restantes:
        melhor = None
        for f in restantes:
            r = avaliar(colunas(X, tuple(escolhidas + [f])), y, ids, n_dobras)
            k = float(r["kappa"].mean())
            if melhor is None or k > melhor[1]:
                melhor = (f, k, r)
        f, k, r = melhor
        escolhidas.append(f)
        restantes.remove(f)
        passos.append({"feature": f, "conjunto": list(escolhidas),
                       "kappa": r["kappa"].tolist(),
                       "kappa_medio": k,
                       "especificidade_media": float(np.nanmean(r["especificidade"]))})
        print(f"    +{f:15s} → κ={k:.4f}")
    return passos


def carregar_bases():
    bases = {}
    if CACHE_WEARANIZE.exists():
        d = pickle.load(open(CACHE_WEARANIZE, "rb"))
        for pos in ("cabeca", "pulso"):
            if pos in d:
                v = d[pos]
                assert np.array_equal(np.asarray(v["id"]), np.asarray(v["id_c"]))
                assert np.array_equal(np.asarray(v["y"]), np.asarray(v["y_c"]))
                bases[f"wearanize/{pos}"] = (
                    np.asarray(v["X"], float), np.asarray(v["y"]),
                    np.asarray(v["id"]), np.asarray(v["c"], float))
    arquivos = sorted(DIR_NEWCASTLE.glob("*.npz")) if DIR_NEWCASTLE.exists() else []
    if arquivos:
        Xs, ys, ids, cs = [], [], [], []
        tem_c = True
        for f in arquivos:
            z = np.load(f, allow_pickle=True)
            Xs.append(z["X"]); ys.append(z["y"])
            ids.append(np.repeat(str(z["id"]), len(z["y"])))
            if "c" in z.files:
                cs.append(z["c"])
            else:
                tem_c = False
        X, y, i = np.vstack(Xs), np.concatenate(ys), np.concatenate(ids)
        c = np.concatenate(cs) if tem_c else np.full(len(y), np.nan)
        m = y >= 0
        bases["newcastle"] = (X[m], y[m], i[m], c[m])
    return bases


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    n_dobras = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    bases = carregar_bases()
    if not bases:
        print("Nenhuma base em disco. Este experimento exige as features já extraídas.")
        return 1

    resultado = {"experimento": "ML-11 ablação de features", "seed": SEED,
                 "n_dobras": n_dobras, "contexto": CONTEXTO,
                 "teto_kappa": TETO_KAPPA, "bases": {}}

    for nome, (X, y, ids, c) in bases.items():
        t0 = time.time()
        print(f"\n===== {nome} — {len(y)} épocas, {len(np.unique(ids))} sujeitos, "
              f"{n_dobras} dobras =====")
        print(f"  épocas com p_frac > 0: {np.mean(X[:, IDX['p_frac']] > 0) * 100:.1f} %")
        ref = avaliar(X, y, ids, n_dobras)
        kref = ref["kappa"]
        eref = ref["especificidade"]
        print(f"  as 8: κ={kref.mean():.4f} ({kref.mean() / TETO_KAPPA * 100:.0f} % do teto)"
              f"  espec={np.nanmean(eref):.4f}  sens={np.nanmean(ref['sensibilidade']):.4f}")
        res: dict = {"n_epocas": int(len(y)), "n_sujeitos": int(len(np.unique(ids))),
                     "frac_p_frac_positivo": float(np.mean(X[:, IDX["p_frac"]] > 0)),
                     "referencia": {k: v.tolist() for k, v in ref.items()},
                     "sem_uma": {}, "arquiteturas": {}}

        print("  --- tirar uma, Δ pareado contra as 8 [IC 95 %] ---")
        for f in NOMES_FEATURES:
            manter = tuple(n for n in NOMES_FEATURES if n != f)
            r = avaliar(colunas(X, manter), y, ids, n_dobras)
            dk = ic95_pareado(r["kappa"], kref)
            de = ic95_pareado(r["especificidade"], eref)
            res["sem_uma"][f] = {"kappa": r["kappa"].tolist(),
                                 "dkappa": dk, "despecificidade": de}
            print(f"    sem {f:15s} Δκ={dk[0]:+.4f} [{dk[1]:+.4f}; {dk[2]:+.4f}]"
                  f"  Δespec={de[0]:+.4f}")

        print("  --- o que cada arquitetura entrega ---")
        for rot, Xa in conjuntos_de_arquitetura(X, c).items():
            if not np.all(np.isfinite(Xa)):
                print(f"    {rot:26s} (sem dado nesta base)")
                continue
            r = avaliar(Xa, y, ids, n_dobras)
            dk = ic95_pareado(r["kappa"], kref)
            de = ic95_pareado(r["especificidade"], eref)
            km = float(r["kappa"].mean())
            res["arquiteturas"][rot] = {
                "kappa": r["kappa"].tolist(), "kappa_medio": km,
                "frac_teto": km / TETO_KAPPA,
                "especificidade_media": float(np.nanmean(r["especificidade"])),
                "sensibilidade_media": float(np.nanmean(r["sensibilidade"])),
                "dkappa": dk, "despecificidade": de}
            print(f"    {rot:26s} κ={km:.4f} ({km / TETO_KAPPA * 100:3.0f} % do teto)"
                  f"  Δκ={dk[0]:+.4f} [{dk[1]:+.4f}; {dk[2]:+.4f}]"
                  f"  espec={np.nanmean(r['especificidade']):.3f}")

        print("  --- subconjunto escolhido na cabeça, fixo ---")
        res["subconjuntos_da_cabeca"] = {}
        for rot, nomes in SUBCONJUNTOS_DA_CABECA.items():
            r = avaliar(colunas(X, nomes), y, ids, n_dobras)
            dk = ic95_pareado(r["kappa"], kref)
            de = ic95_pareado(r["especificidade"], eref)
            fora = nome != "wearanize/cabeca"
            res["subconjuntos_da_cabeca"][rot] = {
                "features": list(nomes), "fora_da_amostra": fora,
                "kappa": r["kappa"].tolist(),
                "kappa_medio": float(r["kappa"].mean()),
                "especificidade_media": float(np.nanmean(r["especificidade"])),
                "dkappa": dk, "despecificidade": de}
            print(f"    {rot:12s} κ={r['kappa'].mean():.4f}  Δκ={dk[0]:+.4f} "
                  f"[{dk[1]:+.4f}; {dk[2]:+.4f}]  Δespec={de[0]:+.4f}"
                  f"  {'(fora da amostra)' if fora else '(OTIMISTA: escolhido aqui)'}")

        print("  --- seleção progressiva ---")
        res["progressiva"] = selecao_progressiva(X, y, ids, n_dobras)
        res["segundos"] = time.time() - t0
        resultado["bases"][nome] = res

    SAIDA.mkdir(parents=True, exist_ok=True)
    destino = SAIDA / "ml11_ablacao_features.json"
    destino.write_text(json.dumps(resultado, indent=1, ensure_ascii=False),
                       encoding="utf-8")
    print(f"\ngravado em {destino.relative_to(RAIZ.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
