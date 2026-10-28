"""ML-02 — os baselines, medidos antes de qualquer modelo aprendido.

Uso:
    python -m experimentos.ml02_baselines --dataset sintetico
    python -m experimentos.ml02_baselines --dataset newcastle
    python -m experimentos.ml02_baselines --dataset wearanize --posicao cabeca
    python -m experimentos.ml02_baselines --dataset wearanize --posicao pulso

Grava o log de métricas em experimentos/saida/, com o hash do config junto.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

# O relatório usa acentos e símbolos (±, →, ·): no Windows o console cai para
# cp1252 por padrão e quebra no primeiro caractere fora dessa tabela.
for _fluxo in (sys.stdout, sys.stderr):
    if hasattr(_fluxo, "reconfigure"):
        _fluxo.reconfigure(encoding="utf-8")

from collections.abc import Iterable                               # noqa: E402

from src.avaliar import avaliar_epoca, split_por_sujeito          # noqa: E402
from src.baseline import (                                        # noqa: E402
    calibrar_escala, cole_kripke, fracao_implicada_de_sono, sadeh,
    sempre_dormindo, substituto_de_contagem,
)
from src.carregar.base import ConjuntoEpocas, Gravacao              # noqa: E402
from src.configuracao import carregar_config, fixar_seed           # noqa: E402
from src.epocas import empilhar_contexto, fatiar_epocas             # noqa: E402
from src.features import NOMES_FEATURES, features_de_epoca         # noqa: E402
from src.modelos import regressao_logistica, suavizar_mediana      # noqa: E402
from src.sinal import reamostrar                                   # noqa: E402


def _processar_unificado(
    gravacoes: Iterable[Gravacao], cfg
) -> tuple[ConjuntoEpocas, np.ndarray, np.ndarray, np.ndarray]:
    """Uma passada só sobre as gravações brutas: features (para `conj`, usado
    pela regressão logística) e substituto de contagem (para Cole-Kripke e
    Sadeh — ver DECISÃO TÉCNICA 3 em src/baseline.py), lado a lado.

    Substitui duas passadas independentes que existiam antes — uma via
    `carregar()` só para as features, outra local só para o substituto de
    contagem — cada uma lendo e decodificando as MESMAS gravações brutas do
    zero. Para o Newcastle (55 arquivos, 4,6 GB, sem cache: cada leitura
    decodifica o `.bin` de novo) isso dobrava o tempo de execução por nada:
    reamostragem e fatiamento em épocas (`reamostrar` + `fatiar_epocas`) já
    são idênticos para as duas saídas, então rodam uma vez só por gravação.
    """
    lo, hi = cfg.baseline["banda_contagem_hz"]
    Xs, ys, ids = [], [], []
    cs, ys_c, ids_c = [], [], []
    n_gravacoes = 0
    descartadas = 0

    for gr in gravacoes:
        n_gravacoes += 1
        t, a = reamostrar(gr.t, gr.a, cfg.taxa_comum_hz, cfg.corte_antialiasing_frac_nyquist)
        a_ep, idx = fatiar_epocas(t, a, gr.t0_rotulo, int(gr.rotulos.shape[0]),
                                  cfg.epoca_s, cfg.taxa_comum_hz)
        if a_ep.shape[0] == 0:
            continue
        descartadas += int(gr.rotulos.shape[0]) - a_ep.shape[0]

        y_ep = gr.rotulos[idx]
        ok = y_ep >= 0                      # não pontuadas (-1) saem: sem verdade p/ comparar
        if not ok.any():
            continue
        y_ok = y_ep[ok]
        ids_ok = np.full(int(ok.sum()), gr.id_sujeito, dtype=object)

        X, _ = features_de_epoca(a_ep, fs=cfg.taxa_comum_hz)
        Xs.append(empilhar_contexto(X[ok], cfg.contexto_epocas))
        ys.append(y_ok)
        ids.append(ids_ok)

        c = substituto_de_contagem(a_ep, cfg.taxa_comum_hz, (float(lo), float(hi)),
                                   float(cfg.baseline["escala_contagem"]))
        cs.append(c[ok])
        ys_c.append(y_ok)
        ids_c.append(ids_ok)

    if not Xs:
        raise ValueError("nenhuma época válida — verifique o alinhamento dos rótulos")

    nomes: list[str] = []
    for d in range(-cfg.contexto_epocas, cfg.contexto_epocas + 1):
        suf = "" if d == 0 else f"__{d:+d}"
        nomes.extend(f"{n}{suf}" for n in NOMES_FEATURES)

    conj = ConjuntoEpocas(
        X=np.concatenate(Xs),
        y=np.concatenate(ys),
        id_sujeito=np.concatenate(ids),
        nomes_features=tuple(nomes),
        meta={
            "n_gravacoes": n_gravacoes,
            "epocas_descartadas_sem_cobertura": descartadas,
            "hash_config": cfg.hash,
        },
    )
    return conj, np.concatenate(cs), np.concatenate(ys_c), np.concatenate(ids_c)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="sintetico",
                    choices=("sintetico", "newcastle", "wearanize"))
    # Só o Wearanize+ tem mais de uma posição de sensor. É o parâmetro do ML-03:
    # treinar numa e testar em outra, medindo a queda de kappa.
    ap.add_argument("--posicao", default="cabeca", choices=("cabeca", "pulso", "coxa"),
                    help="só para --dataset wearanize (padrão: cabeca)")
    ap.add_argument("--pontuador", type=int, default=1, choices=(1, 2),
                    help="qual pontuação manual usar; a 2ª existe em 96 dos 100")
    args = ap.parse_args()

    cfg = carregar_config()
    fixar_seed(cfg.seed)

    print(f"config hash={cfg.hash} · seed={cfg.seed} · época={cfg.epoca_s:g}s · "
          f"grade={cfg.taxa_comum_hz:g}Hz · contexto=±{cfg.contexto_epocas}")

    # --- gravações brutas (para os baselines de contagem) -------------------
    if args.dataset == "sintetico":
        from src.carregar.sintetico import gerar_sinteticos
        s = cfg.sintetico
        gravacoes = gerar_sinteticos(
            n_sujeitos=int(s["n_sujeitos"]), horas_por_noite=float(s["horas_por_noite"]),
            taxa_origem_hz=float(s["taxa_origem_hz"]), fracao_sono=float(s["fracao_sono"]),
            fracao_vigilia_quieta=float(s["fracao_vigilia_quieta"]),
            ruido_mg=float(s["ruido_mg"]), epoca_s=cfg.epoca_s, seed=cfg.seed)
    elif args.dataset == "wearanize":
        from src.carregar.wearanize import carregar_wearanize
        gravacoes = carregar_wearanize(
            posicao=args.posicao, pontuador=args.pontuador
        )
    else:
        from src.carregar.newcastle import carregar_newcastle
        gravacoes = carregar_newcastle()

    conj, c, y_c, id_c = _processar_unificado(gravacoes, cfg)
    conj.meta["dataset"] = args.dataset
    if args.dataset == "wearanize":
        # Um resultado do ML-03 sem a posição registrada é um resultado sem
        # sentido: as células da matriz só diferem nisso.
        conj.meta["posicao"] = args.posicao
        conj.meta["pontuador"] = args.pontuador

    print(f"\n{len(conj)} épocas · {len(set(conj.id_sujeito.tolist()))} sujeitos · "
          f"{conj.X.shape[1]} features (8 × {2*cfg.contexto_epocas+1} janelas)")
    print(f"prevalência de sono: {conj.y.mean():.1%}\n")

    resultados: dict[str, dict] = {}

    # --- Passo 0: o baseline degenerado ------------------------------------
    resultados["0_sempre_dormindo"] = avaliar_epoca(conj.y, sempre_dormindo(len(conj))).dict()

    # --- Passo 1: Cole-Kripke e Sadeh sobre o substituto de contagem --------
    # (a) escala arbitrária do config — mostra a degeneração da DECISÃO 4
    resultados["1a_cole_kripke_escala_arbitraria"] = avaliar_epoca(y_c, cole_kripke(c)).dict()
    resultados["1b_sadeh_escala_arbitraria"] = avaliar_epoca(y_c, sadeh(c)).dict()

    # (b) escala calibrada NO TREINO de cada dobra, limiares publicados intactos
    escalas_usadas: dict[str, list[float]] = {"cole_kripke": [], "sadeh": []}
    for alg, chave in ((cole_kripke, "cole_kripke"), (sadeh, "sadeh")):
        pred_c = np.zeros_like(y_c)
        for _, tr, te in split_por_sujeito(id_c):
            e = calibrar_escala(c[tr], y_c[tr], alg)
            escalas_usadas[chave].append(e)
            pred_c[te] = alg(c[te] * e)
        rot = "1c_cole_kripke_calibrado_loso" if chave == "cole_kripke" else "1d_sadeh_calibrado_loso"
        resultados[rot] = avaliar_epoca(y_c, pred_c).dict()

    # --- Passo 2: regressão logística, leave-one-subject-out ---------------
    pred = np.zeros(len(conj), dtype=int)
    for _, tr, te in split_por_sujeito(conj.id_sujeito):
        m = regressao_logistica(cfg.seed)
        m.fit(conj.X[tr], conj.y[tr])
        pred[te] = m.predict(conj.X[te])
    resultados["2_regressao_logistica_loso"] = avaliar_epoca(conj.y, pred).dict()

    # --- Passo 4: suavização temporal sobre o passo 2 -----------------------
    suave = np.concatenate([
        suavizar_mediana(pred[conj.id_sujeito == s])
        for s in sorted(set(conj.id_sujeito.tolist()))
    ])
    ordem = np.concatenate([np.flatnonzero(conj.id_sujeito == s)
                            for s in sorted(set(conj.id_sujeito.tolist()))])
    pred_suave = np.zeros_like(pred)
    pred_suave[ordem] = suave
    resultados["4_logistica_mais_suavizacao"] = avaliar_epoca(conj.y, pred_suave).dict()

    # --- tabela -------------------------------------------------------------
    cab = f"{'modelo':<34} {'acur':>7} {'sens':>7} {'espec':>7} {'kappa':>7} {'F1 vig':>7}"
    print(cab); print("-" * len(cab))
    for nome, m in resultados.items():
        print(f"{nome:<34} {m['acuracia']:>6.1%} {m['sensibilidade']:>6.1%} "
              f"{m['especificidade']:>6.1%} {m['kappa']:>7.3f} {m['f1_vigilia']:>6.1%}")

    triv = resultados["0_sempre_dormindo"]["acuracia"]
    print("\nLeitura obrigatória:")
    for nome, m in resultados.items():
        if nome.startswith("0_"):
            continue
        d = (m["acuracia"] - triv) * 100
        sinal = "GANHA" if d > 0 else "PERDE"
        print(f"  {nome:<34} {sinal} {abs(d):5.2f} pt de acurácia sobre 'sempre dormindo'")
    print("  'sempre dormindo' tem kappa = 0 por construção: ele não concorda "
          "com nada além do acaso.")

    # --- validação da conta do §0.2 contra a literatura --------------------
    print("\nConferência da identidade do §0.2 (p implicado por trios publicados):")
    for rot, (acc, sen, esp) in {
        "Li et al. 2025 (MotionWatch8)": (0.873, 0.948, 0.331),
        "Walch et al. 2019 (Apple Watch)": (0.900, 0.930, 0.596),
    }.items():
        p = fracao_implicada_de_sono(acc, sen, esp)
        print(f"  {rot:<34} p = {p:.1%} · 'sempre dormindo' acertaria {p:.1%} "
              f"vs. {acc:.1%} publicado → {(acc - p) * 100:+.1f} pt")

    # --- log de métricas ----------------------------------------------------
    saida = RAIZ / "experimentos" / "saida"
    saida.mkdir(parents=True, exist_ok=True)
    carimbo = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    sufixo = f"_{args.posicao}" if args.dataset == "wearanize" else ""
    destino = saida / f"ml02_{args.dataset}{sufixo}_{cfg.hash}_{carimbo}.json"
    destino.write_text(json.dumps({
        "experimento": "ML-02 baselines",
        "dataset": args.dataset,
        **({"posicao": args.posicao, "pontuador": args.pontuador}
           if args.dataset == "wearanize" else {}),
        "AVISO": ("DADO SINTÉTICO — exercita o pipeline, NÃO é medição nem achado"
                  if args.dataset == "sintetico" else "dado real"),
        "hash_config": cfg.hash, "seed": cfg.seed, "utc": carimbo,
        "n_epocas": len(conj), "n_sujeitos": len(set(conj.id_sujeito.tolist())),
        "prevalencia_sono": float(conj.y.mean()),
        "validacao": cfg.validacao, "resultados": resultados,
        "escalas_de_contagem_por_dobra": escalas_usadas,
        "nota_escala": (
            "Escala do substituto de contagem calibrada por dobra, SOMENTE nos "
            "sujeitos de treino (1 parâmetro). Limiares de Cole-Kripke e Sadeh "
            "nos valores publicados. Ver DECISÃO TÉCNICA 4 em src/baseline.py."
        ),
        "config": cfg.bruto,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nlog: {destino.relative_to(RAIZ)}")

    if args.dataset == "sintetico":
        print("\n⚠️  DADO SINTÉTICO. Estes números exercitam o pipeline e NÃO são\n"
              "    achado científico. Nada daqui vai para o TCC como medição.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
