"""A vigília que o modelo servido reconhece, por época e por noite (análise de 23/11).

Lê as probabilidades por época do `ml-inf-cabeca-v2` guardadas pela rodada do
ML-INF v2 (`dados-locais/ml-inf-cabeca-v2-2026-11-07-final/*.npz`, fora do
repositório: `y`, `pred`, `probabilidade`, `ids`; 1 = sono, 0 = vigília) e
responde a três perguntas que o κ médio não responde:

1. quanto da vigília o modelo reconhece, e a que custo em sono (AUC e a troca
   no ponto de corte);
2. se mover o ponto de corte ajuda: o corte é escolhido SÓ na Wearanize (fora
   da amostra, LOSO) e medido nas externas, para não escolher olhando a resposta;
3. o erro por noite, em minutos: tempo total de sono e vigília, e se a vigília
   estimada acompanha a real de uma noite para outra.

Grava só agregados (nenhum identificador de participante).

    python -m experimentos.analise_vigilia_por_noite --entrada <pasta-dos-npz> --saida <arquivo.json>
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.metrics import cohen_kappa_score, roc_auc_score

COORTES = (
    ("wearanize-cabeca", "Wearanize cabeça (LOSO)"),
    ("newcastle", "Newcastle (externa)"),
    ("walch_principal", "Walch principal (externa)"),
    ("dreamt", "DREAMT (externa)"),
)
EPOCA_MIN = 0.5
CORTES = (0.5, 0.6, 0.7)
SENSIBILIDADES = (0.80, 0.85, 0.90)


def confusao(y, pred):
    """Contagens com sono como classe positiva."""
    y = np.asarray(y); pred = np.asarray(pred)
    return dict(
        vp=int(((pred == 1) & (y == 1)).sum()), vn=int(((pred == 0) & (y == 0)).sum()),
        fp=int(((pred == 1) & (y == 0)).sum()), fn=int(((pred == 0) & (y == 1)).sum()),
    )


def metricas_por_epoca(y, pred):
    c = confusao(y, pred)
    sens = c["vp"] / (c["vp"] + c["fn"]) if c["vp"] + c["fn"] else float("nan")
    esp = c["vn"] / (c["vn"] + c["fp"]) if c["vn"] + c["fp"] else float("nan")
    prec_vig = c["vn"] / (c["vn"] + c["fn"]) if c["vn"] + c["fn"] else float("nan")
    f1_vig = (2 * prec_vig * esp / (prec_vig + esp)) if prec_vig + esp > 0 else 0.0
    n = sum(c.values())
    return dict(c, sensibilidade=sens, especificidade=esp, precisao_vigilia=prec_vig,
                f1_vigilia=f1_vig, acuracia_balanceada=(sens + esp) / 2,
                acuracia=(c["vp"] + c["vn"]) / n, fracao_vigilia=(c["vn"] + c["fp"]) / n)


def especificidade_com_sensibilidade(y, prob, alvo):
    """Maior especificidade possível mantendo a sensibilidade em `alvo`."""
    y = np.asarray(y); prob = np.asarray(prob)
    corte = np.quantile(prob[y == 1], 1 - alvo)
    return metricas_por_epoca(y, (prob >= corte).astype(int))["especificidade"]


def por_noite(y, pred, ids):
    """Erro do tempo total de sono (previsto − real) e vigília real e prevista, em minutos."""
    y = np.asarray(y); pred = np.asarray(pred); ids = np.asarray(ids)
    erros, vig_real, vig_prev, kappas = [], [], [], []
    for i in np.unique(ids):
        s = ids == i
        erros.append((pred[s].sum() - y[s].sum()) * EPOCA_MIN)
        vig_real.append(float((y[s] == 0).sum()) * EPOCA_MIN)
        vig_prev.append(float((pred[s] == 0).sum()) * EPOCA_MIN)
        kappas.append(cohen_kappa_score(y[s], pred[s]))
    e = np.array(erros); vr = np.array(vig_real); vp = np.array(vig_prev); k = np.array(kappas, dtype=float)
    dp = float(e.std(ddof=1)) if len(e) > 1 else float("nan")
    r = float(np.corrcoef(vr, vp)[0, 1]) if len(e) > 1 and vr.std() > 0 and vp.std() > 0 else float("nan")
    return dict(
        noites=len(e), vies_tst_min=float(e.mean()), dp_tst_min=dp,
        limites_95_min=[float(e.mean() - 1.96 * dp), float(e.mean() + 1.96 * dp)],
        fracao_erro_acima_60_min=float(np.mean(np.abs(e) > 60)),
        vigilia_real_media_min=float(vr.mean()), vigilia_prevista_media_min=float(vp.mean()),
        correlacao_vigilia_entre_noites=r, fracao_noites_kappa_abaixo_0_2=float(np.nanmean(k < 0.2)),
        kappa_medio=float(np.nanmean(k)),
    )


def analisar(dados):
    """`dados`: {nome: (y, pred, prob, ids)}. Devolve o dicionário do relatório."""
    yw, _, pw, _ = dados["wearanize-cabeca"]
    candidatos = [round(c, 2) for c in np.arange(0.30, 0.86, 0.05)]
    corte_kappa = max(candidatos, key=lambda c: cohen_kappa_score(yw, (pw > c).astype(int)))
    saida = {"corte_servido": 0.5, "corte_de_maior_kappa_na_wearanize": corte_kappa, "coortes": {}}
    for nome, rotulo in COORTES:
        if nome not in dados:
            continue
        y, pred, prob, ids = dados[nome]
        cortes = {}
        for corte in sorted(set(CORTES) | {corte_kappa}):
            p = (np.asarray(prob) > corte).astype(int)
            m = metricas_por_epoca(y, p)
            cortes[f"{corte:.2f}"] = dict(sensibilidade=m["sensibilidade"], especificidade=m["especificidade"],
                                          kappa_medio=por_noite(y, p, ids)["kappa_medio"])
        saida["coortes"][nome] = dict(
            rotulo=rotulo, por_epoca=metricas_por_epoca(y, pred), auc=float(roc_auc_score(y, prob)),
            especificidade_com_sensibilidade={f"{a:.2f}": especificidade_com_sensibilidade(y, prob, a) for a in SENSIBILIDADES},
            cortes=cortes, por_noite=por_noite(y, pred, ids),
            sempre_sono_por_noite=por_noite(y, np.ones_like(np.asarray(y)), ids),
        )
    return saida


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--entrada", required=True, type=Path)
    ap.add_argument("--saida", required=True, type=Path)
    args = ap.parse_args(argv)
    dados = {}
    for nome, _ in COORTES:
        z = np.load(args.entrada / f"{nome}.npz", allow_pickle=False)
        dados[nome] = (z["y"], z["pred"], z["probabilidade"], z["ids"])
    resultado = analisar(dados)
    args.saida.write_text(json.dumps(resultado, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    for nome, r in resultado["coortes"].items():
        e, n = r["por_epoca"], r["por_noite"]
        print(f"{r['rotulo']:28s} esp {e['especificidade']:.3f} F1vig {e['f1_vigilia']:.3f} AUC {r['auc']:.3f} "
              f"| TST {n['vies_tst_min']:+.1f}±{n['dp_tst_min']:.1f} min, r vigília {n['correlacao_vigilia_entre_noites']:.2f}")


if __name__ == "__main__":
    main()
