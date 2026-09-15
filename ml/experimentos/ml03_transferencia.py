"""ML-03 -- matriz de transferência entre posições do Wearanize+.

Uso:
    python -m experimentos.ml03_transferencia
    python -m experimentos.ml03_transferencia --n-sujeitos 10   # piloto rápido

O experimento que é a contribuição original do trabalho: treinar um modelo
numa posição de sensor e testar em outra, medindo a queda de kappa (Δκ) em vez
de declarar a transferência como limitação (ver §9 e o experimento do §7 de
`docs/ML-DATASETS-E-PLANO.md`).

=============================================================================
O CONTROLE EXPERIMENTAL — por que "cabeça degradada" existe
=============================================================================
A matriz ingênua (treina em pulso, testa em cabeça) mistura duas variáveis: o
Zmax da cabeça é 256 Hz / 12 bits / 0,977 mg-LSB; o Empatica do pulso é 32 Hz /
8 bits / 15,625 mg-LSB -- 16x mais grosseiro. Um Δκ medido daí não se pode
atribuir a "mudou a posição" nem a "mudou a qualidade do sensor" isoladamente.

Este script roda em **três braços**, não dois:

  cabeca      -- Zmax original (256 Hz, 12 bits)
  cabeca_e4   -- Zmax degradado para a grade do E4 (32 Hz, 8 bits) via
                 `degradar_para_e4()` -- MESMO sinal, qualidade do pulso
  pulso       -- Empatica original (32 Hz, 8 bits)

  cabeca      vs. cabeca_e4  ->  custo da QUALIDADE do sensor, isolado
  pulso       vs. cabeca_e4  ->  custo da POSIÇÃO, isolado (mesma qualidade
                                  nos dois lados)
  cabeca      vs. pulso      ->  a matriz ingênua, reportada por comparação

=============================================================================
DESENHO DA MATRIZ — por que é fold a fold, não "treina em tudo, testa em tudo"
=============================================================================
Para que os 9 números sejam comparáveis, cada um dos 92 folds (um sujeito de
cada vez) treina um modelo por braço usando os OUTROS 91 sujeitos, e testa
esse modelo nos TRÊS braços do sujeito deixado de fora. Isso garante que:

  1. O sujeito de teste nunca entra no treino, em nenhum braço -- sem
     vazamento, mesmo entre células fora da diagonal.
  2. A diagonal (treina=X, testa=X) É o resultado padrão de LOSO por posição
     -- não se calcula duas vezes.
  3. As nove células usam exatamente os mesmos 92 folds -- a única coisa que
     muda de uma célula para outra é qual sinal foi usado para treinar e qual
     para testar, nunca o particionamento.

Δκ é sempre relativo à diagonal da própria LINHA (o mesmo modelo, testado na
posição em que foi treinado): Δκ(treino=X, teste=Y) = κ(X,X) − κ(X,Y).
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

for _fluxo in (sys.stdout, sys.stderr):
    if hasattr(_fluxo, "reconfigure"):
        _fluxo.reconfigure(encoding="utf-8")

from src.avaliar import MetricasAgregadas, avaliar_por_sujeito              # noqa: E402
from src.baseline import calibrar_escala, sadeh, sempre_dormindo            # noqa: E402
from src.carregar.base import ConjuntoEpocas                                # noqa: E402
from src.carregar.wearanize import carregar_wearanize, sujeitos_com_posicoes  # noqa: E402
from src.configuracao import carregar_config, fixar_seed                    # noqa: E402
from src.modelos import regressao_logistica                                 # noqa: E402
from experimentos.ml02_baselines import _processar_unificado                # noqa: E402

#: Os três braços do experimento: nome -> (posicao, qualidade).
BRACOS: dict[str, tuple[str, str]] = {
    "cabeca": ("cabeca", "original"),
    "cabeca_e4": ("cabeca", "e4"),
    "pulso": ("pulso", "original"),
}

METRICAS_RELATORIO = ("acuracia", "especificidade", "kappa")


def _sadeh_calibrado_loso(c: np.ndarray, y_c: np.ndarray, id_c: np.ndarray, seed: int) -> np.ndarray:
    """Predição pooled do Sadeh com escala calibrada por dobra (LOSO), só no
    treino de cada dobra -- mesma lógica de `ml02_baselines.py`, aqui isolada
    porque este script não precisa do Cole-Kripke."""
    from src.avaliar import split_por_sujeito
    pred = np.zeros_like(y_c)
    for _, tr, te in split_por_sujeito(id_c):
        escala = calibrar_escala(c[tr], y_c[tr], sadeh)
        pred[te] = sadeh(c[te] * escala)
    return pred


def matriz_de_transferencia(
    bracos: dict[str, ConjuntoEpocas], seed: int
) -> dict[tuple[str, str], MetricasAgregadas]:
    """9 células (treino, teste), fold a fold sobre a interseção de sujeitos."""
    nomes = list(bracos)
    conjuntos_sujeitos = [set(bracos[n].id_sujeito.tolist()) for n in nomes]
    sujeitos = sorted(set.intersection(*conjuntos_sujeitos))
    if len(sujeitos) < 2:
        raise ValueError(
            f"só {len(sujeitos)} sujeito(s) comum(ns) aos três braços -- "
            "não dá para fazer LOSO. Confira `sujeitos_com_posicoes`."
        )
    descartados = set.union(*conjuntos_sujeitos) - set(sujeitos)
    if descartados:
        print(
            f"[ml03] {len(descartados)} sujeito(s) presentes em só ALGUNS braços, "
            f"descartados da matriz (precisa dos três): {sorted(descartados)}",
            file=sys.stderr,
        )

    preds = {
        (tr, te): np.zeros(bracos[te].X.shape[0], dtype=int)
        for tr in nomes for te in nomes
    }

    for k, s in enumerate(sujeitos, 1):
        modelos = {}
        for tr in nomes:
            conj_tr = bracos[tr]
            mask_tr = conj_tr.id_sujeito != s
            m = regressao_logistica(seed)
            m.fit(conj_tr.X[mask_tr], conj_tr.y[mask_tr])
            modelos[tr] = m
        for te in nomes:
            conj_te = bracos[te]
            mask_te = conj_te.id_sujeito == s
            if not mask_te.any():
                continue
            for tr in nomes:
                preds[(tr, te)][mask_te] = modelos[tr].predict(conj_te.X[mask_te])
        if k % 10 == 0 or k == len(sujeitos):
            print(f"\r[ml03] fold {k}/{len(sujeitos)}", end="", file=sys.stderr)
    print(file=sys.stderr)

    resultado: dict[tuple[str, str], MetricasAgregadas] = {}
    for tr in nomes:
        for te in nomes:
            conj_te = bracos[te]
            mask = np.isin(conj_te.id_sujeito, sujeitos)
            resultado[(tr, te)] = avaliar_por_sujeito(
                conj_te.y[mask], preds[(tr, te)][mask], conj_te.id_sujeito[mask],
                metricas=METRICAS_RELATORIO, seed=seed,
            )
    return resultado


def imprimir_matriz(matriz: dict[tuple[str, str], MetricasAgregadas], metrica: str) -> None:
    nomes = list(BRACOS)
    largura = 13
    print(f"\n{metrica.upper()} -- linhas = treino, colunas = teste")
    print(" " * (largura + 1) + "".join(f"{n:>{largura}}" for n in nomes))
    for tr in nomes:
        linha = [f"{matriz[(tr, te)].media[metrica]:>{largura}.3f}" for te in nomes]
        print(f"{tr:<{largura}}" + "".join(linha))


def imprimir_delta_kappa(matriz: dict[tuple[str, str], MetricasAgregadas]) -> None:
    nomes = list(BRACOS)
    largura = 13
    print("\nΔκ = κ(treino,treino) − κ(treino,teste) -- 0 na diagonal por definição")
    print(" " * (largura + 1) + "".join(f"{n:>{largura}}" for n in nomes))
    for tr in nomes:
        ref = matriz[(tr, tr)].media["kappa"]
        linha = []
        for te in nomes:
            d = ref - matriz[(tr, te)].media["kappa"]
            linha.append(f"{d:>{largura}.3f}")
        print(f"{tr:<{largura}}" + "".join(linha))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-sujeitos", type=int, default=None,
                     help="limita a N sujeitos (ordem alfabética) -- piloto rápido")
    ap.add_argument("--pasta", type=Path, default=None)
    args = ap.parse_args()

    cfg = carregar_config()
    fixar_seed(cfg.seed)

    kwargs_pasta = {"pasta": args.pasta} if args.pasta else {}
    sujeitos = sujeitos_com_posicoes(["cabeca", "pulso"], **kwargs_pasta)
    if args.n_sujeitos:
        sujeitos = sujeitos[: args.n_sujeitos]

    print(f"config hash={cfg.hash} · seed={cfg.seed} · sujeitos(cabeça∩pulso)={len(sujeitos)}")
    print("Carregando os três braços (cabeca, cabeca_e4, pulso) -- features E substituto de contagem, uma passada só...")

    bracos: dict[str, ConjuntoEpocas] = {}
    contagens: dict[str, tuple] = {}   # nome -> (c, y_c, id_c)
    for nome, (posicao, qualidade) in BRACOS.items():
        gravacoes = carregar_wearanize(
            posicao=posicao, qualidade=qualidade, sujeitos=sujeitos, **kwargs_pasta
        )
        conj, c, y_c, id_c = _processar_unificado(gravacoes, cfg)
        conj.meta.update(braco=nome, posicao=posicao, qualidade=qualidade)
        bracos[nome] = conj
        contagens[nome] = (c, y_c, id_c)
        faltando = set(sujeitos) - set(conj.id_sujeito.tolist())
        if faltando:
            print(f"[ml03] AVISO: braço {nome!r} não cobriu {sorted(faltando)}", file=sys.stderr)

    for nome, conj in bracos.items():
        print(f"  {nome:<10} {len(conj)} épocas · {len(set(conj.id_sujeito.tolist()))} sujeitos "
              f"· prevalência de sono {conj.y.mean():.1%}")

    print("\nML-02 por braço -- trivial e Sadeh calibrado (LOSO), cada um com IC 95% e")
    print("desvio-padrão ENTRE SUJEITOS (não é o resultado pooled):")
    baselines_por_braco: dict[str, dict[str, MetricasAgregadas]] = {}
    for nome, conj in bracos.items():
        c, y_c, id_c = contagens[nome]
        m_trivial = avaliar_por_sujeito(conj.y, sempre_dormindo(len(conj)), conj.id_sujeito,
                                         metricas=METRICAS_RELATORIO, seed=cfg.seed)
        pred_sadeh = _sadeh_calibrado_loso(c, y_c, id_c, cfg.seed)
        m_sadeh = avaliar_por_sujeito(y_c, pred_sadeh, id_c,
                                       metricas=METRICAS_RELATORIO, seed=cfg.seed)
        print(f"\n  === {nome} ===")
        print(f"    trivial      kappa={m_trivial.resumo('kappa')}  espec={m_trivial.resumo('especificidade')}")
        print(f"    Sadeh LOSO   kappa={m_sadeh.resumo('kappa')}  espec={m_sadeh.resumo('especificidade')}")
        baselines_por_braco[nome] = {"trivial": m_trivial, "sadeh_calibrado_loso": m_sadeh}

    print("\nRodando a matriz de transferência (LOSO, 3 modelos por fold) -- a diagonal É")
    print("o resultado da regressão logística por braço, não recalculado separadamente...")
    matriz = matriz_de_transferencia(bracos, cfg.seed)
    print("\n(logística por braço, LOSO -- é a diagonal da matriz abaixo)")
    for nome in BRACOS:
        m = matriz[(nome, nome)]
        print(f"    {nome:<10} kappa={m.resumo('kappa')}  espec={m.resumo('especificidade')}")

    for metrica in METRICAS_RELATORIO:
        imprimir_matriz(matriz, metrica)
    imprimir_delta_kappa(matriz)

    def k(tr: str, te: str) -> float:
        return matriz[(tr, te)].media["kappa"]

    print("\nCélulas de controle -- a leitura obrigatória do experimento:")
    print(
        "\n  (A) DIAGONAIS -- classificabilidade intrínseca de cada domínio, "
        "cada um com seu\n      próprio modelo (sem transferência nenhuma):"
    )
    print(f"      κ(cabeca,cabeca)      = {k('cabeca','cabeca'):.3f}   (posição=cabeça, qualidade=Zmax)")
    print(f"      κ(cabeca_e4,cabeca_e4)= {k('cabeca_e4','cabeca_e4'):.3f}   (posição=cabeça, qualidade=E4)")
    print(f"      κ(pulso,pulso)        = {k('pulso','pulso'):.3f}   (posição=pulso, qualidade=E4)")
    print(
        f"      custo intrínseco da QUALIDADE (mesma posição=cabeça): "
        f"{k('cabeca','cabeca') - k('cabeca_e4','cabeca_e4'):+.3f}"
    )
    print(
        f"      custo intrínseco da POSIÇÃO (mesma qualidade=E4): "
        f"{k('pulso','pulso') - k('cabeca_e4','cabeca_e4'):+.3f}"
    )

    print(
        "\n  (B) TRANSFERÊNCIA -- modelo treinado num domínio, aplicado sem "
        "reajuste noutro\n      (o desenho clássico do ML-03):"
    )
    print(
        f"      custo de DEGRADAR SÓ A QUALIDADE, mesma posição (treino=cabeça, "
        f"teste=cabeça_e4):\n"
        f"        κ(cabeca,cabeca)={k('cabeca','cabeca'):.3f}  "
        f"κ(cabeca,cabeca_e4)={k('cabeca','cabeca_e4'):.3f}  "
        f"Δκ={k('cabeca','cabeca') - k('cabeca','cabeca_e4'):+.3f}"
    )
    print(
        f"      custo de MUDAR SÓ A POSIÇÃO, mesma qualidade E4 (treino=pulso, "
        f"teste=cabeça_e4):\n"
        f"        κ(pulso,pulso)={k('pulso','pulso'):.3f}  "
        f"κ(pulso,cabeca_e4)={k('pulso','cabeca_e4'):.3f}  "
        f"Δκ={k('pulso','pulso') - k('pulso','cabeca_e4'):+.3f}"
    )
    print(
        f"      matriz INGÊNUA, as duas variáveis juntas -- as duas direções:\n"
        f"        treino=cabeça, teste=pulso: κ={k('cabeca','cabeca'):.3f}→{k('cabeca','pulso'):.3f}  "
        f"Δκ={k('cabeca','cabeca') - k('cabeca','pulso'):+.3f}\n"
        f"        treino=pulso, teste=cabeça: κ={k('pulso','pulso'):.3f}→{k('pulso','cabeca'):.3f}  "
        f"Δκ={k('pulso','pulso') - k('pulso','cabeca'):+.3f}"
    )

    saida = RAIZ / "experimentos" / "saida"
    saida.mkdir(parents=True, exist_ok=True)
    carimbo = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destino = saida / f"ml03_transferencia_{cfg.hash}_{carimbo}.json"
    destino.write_text(json.dumps({
        "experimento": "ML-03 transferencia entre posicoes (com controle de qualidade)",
        "hash_config": cfg.hash, "seed": cfg.seed, "utc": carimbo,
        "n_sujeitos": len(sujeitos), "sujeitos": sujeitos,
        "bracos": {n: {"posicao": p, "qualidade": q} for n, (p, q) in BRACOS.items()},
        "prevalencia_sono": {n: float(c.y.mean()) for n, c in bracos.items()},
        "baselines_por_braco": {
            nome: {chave: m.dict() for chave, m in bl.items()}
            for nome, bl in baselines_por_braco.items()
        },
        "matriz": {
            f"{tr}->{te}": m.dict() for (tr, te), m in matriz.items()
        },
        "nota": (
            "Delta-kappa e sempre relativo a diagonal da PROPRIA linha "
            "(mesmo modelo, testado na posicao em que foi treinado). "
            "As 9 celulas compartilham os mesmos folds LOSO -- ver docstring do script."
        ),
        "config": cfg.bruto,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nlog: {destino.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
