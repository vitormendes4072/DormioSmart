"""ML-03b -- otimizacoes de especificidade (itens 6-9), sobre normalizacao
por sujeito como base.

Por que uma base diferente da "referencia" do ml03b_ablacao.py
----------------------------------------------------------------
A ablacao (ver ml03b_ablacao.py) mostrou que normalizacao por sujeito
(item 5) recupera a assimetria de transferencia tao bem quanto reajustar o
scaler no dominio de teste, sem usar rotulo nenhum do sujeito de teste --
e por isso e a escolha certa para o produto real. Estes quatro itens
medem otimizacoes de especificidade EM CIMA dessa base, nao da referencia
antiga (scaler por dominio).

Por que um script separado do ml03b_ablacao.py
----------------------------------------------------------------
A sessao em segundo plano do ml03b_ablacao.py foi interrompida tres vezes
por limites externos (fora do controle do script). A causa raiz nao era o
script -- era rodar horas em segundo plano sem pontos de salvamento
granulares o bastante. Aqui cada item e uma chamada de processo SEPARADA,
em primeiro plano, que carrega o cache (rapido, ja existe em disco),
calcula UM item, salva e sai. Uma interrupcao custa no maximo um item, e
o item errado nunca fica destrancado leitura.

Uso (uma chamada por item):
    python -m experimentos.ml03b_otimizacoes --item baseline
    python -m experimentos.ml03b_otimizacoes --item 6
    python -m experimentos.ml03b_otimizacoes --item 7
    python -m experimentos.ml03b_otimizacoes --item 8
    python -m experimentos.ml03b_otimizacoes --item 9
    python -m experimentos.ml03b_otimizacoes --item resumo   # so imprime o que ja tem

Os quatro itens, todos sobre features normalizadas por sujeito:
  6. `class_weight="balanced"` vs `None` -- mede o contrafactual: o ganho
     de especificidade que vem SO desse parametro.
  7. Limiar de decisao por indice de Youden, escolhido no TREINO de cada
     fold (nunca no teste) -- em vez do 0.5 default do `.predict()`.
  8. Suavizacao temporal (mediana movel, janela 5) sobre a predicao bruta
     do mesmo modelo do baseline.
  8b. Suavizacao temporal por HMM de 2 estados (Viterbi), com a matriz de
     transicao contada nos rotulos do TREINO de cada dobra. E a versao
     forte do item 8: o custo de trocar de estado e calibrado nos dados em
     vez de arbitrado por uma janela fixa.
  9. Janela de contexto mais larga (padrao +-11 epocas ~ 11 min, a escala
     do Sadeh) em vez de +-2.

Sobre o criterio de "ganho"
----------------------------------------------------------------
Cada comparacao sai com DOIS testes, lado a lado:
  [IC disjunto] os dois IC95 individuais nao se sobrepoem -- conservador
                demais para um desenho pareado, fica como piso;
  [pareado]     IC95 bootstrap da DIFERENCA sobre os mesmos sujeitos --
                remove a variancia entre sujeitos, que e comum aos dois
                bracos, e e o veredito formal.
Em ambos, ganho dentro do IC nao e ganho.

Confirmacao pedida: a matriz N=92 do ml03b_ablacao.py (referencia e itens
1-5) NAO aplica suavizacao nenhuma -- as predicoes vem direto de
`.predict()` dentro de `matriz_generica`, sem nenhuma chamada a
`suavizar_mediana` no caminho. O item 8 aqui e a primeira vez que a
suavizacao entra na comparacao.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

for _fluxo in (sys.stdout, sys.stderr):
    if hasattr(_fluxo, "reconfigure"):
        _fluxo.reconfigure(encoding="utf-8")

from src.avaliar import avaliar_por_sujeito, split_por_sujeito              # noqa: E402
from src.carregar.wearanize import sujeitos_com_posicoes                   # noqa: E402
from src.configuracao import carregar_config, fixar_seed                   # noqa: E402
from src.epocas import empilhar_contexto                                   # noqa: E402
from src.modelos import suavizar_hmm, suavizar_mediana, transicoes_hmm     # noqa: E402

from experimentos._retomada import loso_com_retomada                       # noqa: E402
from experimentos.ml03b_ablacao import (                                   # noqa: E402
    METRICAS, NOMES_BRACOS, _limiar_youden, carregar_base, normalizar_por_sujeito,
)

ITENS_VALIDOS = ("baseline", "6", "7", "8", "8b", "9", "resumo")


def _carregar_base_com_cache(sujeitos: list[str], cfg, pasta=None) -> dict:
    import hashlib
    import pickle
    cache_chave = hashlib.sha256(
        (cfg.hash + "|" + ",".join(sujeitos)).encode("utf-8")
    ).hexdigest()[:16]
    cache_caminho = RAIZ / "dados" / "processado" / f"_cache_base_wearanize_{cache_chave}.pkl"
    if cache_caminho.exists():
        print(f"Cache encontrado ({cache_caminho.name}), pulando releitura dos EDFs...", file=sys.stderr)
        with open(cache_caminho, "rb") as fh:
            return pickle.load(fh)
    print("Cache nao encontrado -- carregando do zero (pode demorar ~20 min)...", file=sys.stderr)
    base = carregar_base(sujeitos, cfg, pasta=pasta)
    cache_caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_caminho, "wb") as fh:
        pickle.dump(base, fh, protocol=pickle.HIGHEST_PROTOCOL)
    return base


def _diagonal(X: np.ndarray, y: np.ndarray, ids: np.ndarray, seed: int, class_weight):
    pred = np.zeros_like(y)
    for _, tr, te in split_por_sujeito(ids):
        clf = LogisticRegression(max_iter=2000, class_weight=class_weight, random_state=seed)
        clf.fit(X[tr], y[tr])
        pred[te] = clf.predict(X[te])
    return avaliar_por_sujeito(y, pred, ids, metricas=METRICAS, seed=seed), pred


def _diagonal_youden(X: np.ndarray, y: np.ndarray, ids: np.ndarray, seed: int):
    pred = np.zeros_like(y)
    for _, tr, te in split_por_sujeito(ids):
        clf = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=seed)
        clf.fit(X[tr], y[tr])
        limiar = _limiar_youden(y[tr], clf.predict_proba(X[tr])[:, 1])
        pred[te] = (clf.predict_proba(X[te])[:, 1] >= limiar).astype(int)
    return avaliar_por_sujeito(y, pred, ids, metricas=METRICAS, seed=seed)


def _dobra_logistica(X_tr, y_tr, X_te, ids_tr, seed):
    clf = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=seed)
    clf.fit(X_tr, y_tr)
    return clf.predict(X_te)


def _dobra_hmm(X_tr, y_tr, X_te, ids_tr, seed):
    clf = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=seed)
    clf.fit(X_tr, y_tr)
    A, _ = transicoes_hmm(y_tr, ids_tr)
    # `prior_implicito=None`: com class_weight="balanced" a probabilidade já
    # vem sob prior uniforme. Ver o aviso em src.modelos.suavizar_hmm.
    return suavizar_hmm(clf.predict_proba(X_te)[:, 1], A)


def _diagonal_hmm(X: np.ndarray, y: np.ndarray, ids: np.ndarray, seed: int):
    """LOSO com Viterbi de 2 estados por cima da logística.

    A matriz de transição é contada nos rótulos do TREINO da própria dobra —
    nunca nos do sujeito de teste (seria vazamento, e do tipo que mais
    infla: a transição carrega quase toda a informação de quanto o sujeito
    acordou). Uma matriz por dobra, como qualquer outro parâmetro ajustado.
    """
    pred = np.zeros_like(y)
    for _, tr, te in split_por_sujeito(ids):
        clf = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=seed)
        clf.fit(X[tr], y[tr])
        A, _ = transicoes_hmm(y[tr], ids[tr])
        # `prior_implicito=None`: com class_weight="balanced" a probabilidade
        # já vem sob prior uniforme. Ver o aviso em src.modelos.suavizar_hmm.
        pred[te] = suavizar_hmm(clf.predict_proba(X[te])[:, 1], A)
    return avaliar_por_sujeito(y, pred, ids, metricas=METRICAS, seed=seed), pred


def _bootstrap_pareado(base_dict: dict, novo_dict: dict, metrica: str,
                       n_bootstrap: int = 2000, seed: int = 0) -> dict | None:
    """IC95 da DIFERENÇA, reamostrando os mesmos sujeitos nos dois braços.

    Por que isto e não só comparar os dois IC: os dois braços rodam sobre os
    MESMOS 92 sujeitos, e a variância entre sujeitos (dp ~0,16 em kappa) é
    comum aos dois. Exigir que os IC individuais não se sobreponham é um
    teste conservador demais — descarta como ruído um efeito que o par
    reproduz em quase todo sujeito. O IC da diferença pareada remove a
    variância comum, que é a razão de existir do desenho pareado.

    Os dois testes são reportados lado a lado de propósito; o veredito
    formal do projeto continua sendo o pareado, e o conservador fica como
    piso.
    """
    suj_b = base_dict.get("sujeitos")
    suj_n = novo_dict.get("sujeitos")
    if not suj_b or not suj_n or list(suj_b) != list(suj_n):
        return None
    a = np.asarray(base_dict["por_sujeito"][metrica], dtype=float)
    b = np.asarray(novo_dict["por_sujeito"][metrica], dtype=float)
    ok = ~(np.isnan(a) | np.isnan(b))
    if ok.sum() < 2:
        return None
    d = b[ok] - a[ok]
    rng = np.random.default_rng(seed)
    medias = rng.choice(d, size=(n_bootstrap, d.size), replace=True).mean(axis=1)
    lo, hi = float(np.percentile(medias, 2.5)), float(np.percentile(medias, 97.5))
    return {
        "delta_medio": float(d.mean()), "ic95_baixo": lo, "ic95_alto": hi,
        "n_pares": int(ok.sum()), "significativo": bool(lo > 0.0 or hi < 0.0),
        "melhora": bool(lo > 0.0),
    }


def _ganho_sem_sobreposicao_de_ic(base_dict: dict, novo_dict: dict, metrica: str) -> tuple[bool, bool]:
    """(ha_diferenca_fora_do_ruido, e_melhora) -- conservador: só conta como
    diferença real se os dois IC95 não se sobrepõem. Ganho dentro do IC não
    é ganho, como pedido."""
    b_lo, b_hi = base_dict["ic95_baixo"][metrica], base_dict["ic95_alto"][metrica]
    n_lo, n_hi = novo_dict["ic95_baixo"][metrica], novo_dict["ic95_alto"][metrica]
    sem_sobreposicao = (n_lo > b_hi) or (b_lo > n_hi)
    return sem_sobreposicao, (n_lo > b_hi)


def _imprime_comparacao(nome_braco: str, rotulo_item: str, base_dict: dict | None, novo_dict: dict) -> None:
    print(f"    kappa={novo_dict['media']['kappa']:.3f} "
          f"[{novo_dict['ic95_baixo']['kappa']:.3f}, {novo_dict['ic95_alto']['kappa']:.3f}]  "
          f"espec={novo_dict['media']['especificidade']:.3f} "
          f"[{novo_dict['ic95_baixo']['especificidade']:.3f}, {novo_dict['ic95_alto']['especificidade']:.3f}]")
    if base_dict is None:
        return
    for metrica in ("kappa", "especificidade"):
        diferenca, melhora = _ganho_sem_sobreposicao_de_ic(base_dict, novo_dict, metrica)
        delta = novo_dict["media"][metrica] - base_dict["media"][metrica]
        veredito = ("GANHO REAL (fora do IC)" if (diferenca and melhora)
                    else "PERDA REAL (fora do IC)" if (diferenca and not melhora)
                    else "dentro do IC -- nao conta como ganho")
        print(f"      Δ{metrica}={delta:+.3f} vs. baseline -> [IC disjunto] {veredito}")
        par = _bootstrap_pareado(base_dict, novo_dict, metrica)
        if par is not None:
            vp = ("GANHO REAL" if (par["significativo"] and par["melhora"])
                  else "PERDA REAL" if par["significativo"]
                  else "dentro do IC -- nao conta como ganho")
            print(f"        [pareado] Δ={par['delta_medio']:+.3f} "
                  f"IC95 [{par['ic95_baixo']:+.3f}, {par['ic95_alto']:+.3f}] "
                  f"n={par['n_pares']} -> {vp}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--item", required=True, choices=ITENS_VALIDOS)
    ap.add_argument("--n-sujeitos", type=int, default=None)
    ap.add_argument("--pasta", type=Path, default=None)
    ap.add_argument("--contexto-largo", type=int, default=11,
                     help="nº de épocas vizinhas p/ o item 9 (padrão ±11 ~ janela do Sadeh)")
    ap.add_argument("--orcamento-s", type=float, default=115.0,
                     help="teto de segundos de cálculo por chamada (itens 8b e 9, que "
                          "rodam com checkpoint por dobra). Rode de novo até dizer COMPLETO.")
    args = ap.parse_args()
    t_inicio = time.time()
    incompleto = False

    cfg = carregar_config()
    fixar_seed(cfg.seed)
    seed = cfg.seed

    sujeitos = sujeitos_com_posicoes(["cabeca", "pulso"], **({"pasta": args.pasta} if args.pasta else {}))
    if args.n_sujeitos:
        sujeitos = sujeitos[: args.n_sujeitos]

    destino = RAIZ / "experimentos" / "saida" / f"ml03b_otimizacoes_{cfg.hash}_{len(sujeitos)}suj.json"

    if destino.exists():
        with open(destino, encoding="utf-8") as fh:
            resultado = json.load(fh)
    else:
        resultado = {
            "experimento": "ML-03b -- otimizacoes 6-9 sobre normalizacao por sujeito",
            "hash_config": cfg.hash, "seed": seed, "n_sujeitos": len(sujeitos),
            "base": "normalizacao_por_sujeito (item 5 do ml03b_ablacao.py)",
            "itens": {},
        }

    if args.item == "resumo":
        print(f"arquivo: {destino.name}")
        print(f"n_sujeitos: {resultado['n_sujeitos']}")
        print("itens presentes:", list(resultado["itens"].keys()))
        base_dict_por_braco = resultado["itens"].get("baseline")
        for it, por_braco in resultado["itens"].items():
            print(f"\n=== {it} ===")
            for braco, m in por_braco.items():
                base_dict = base_dict_por_braco[braco] if (base_dict_por_braco and it != "baseline") else None
                print(f"  {braco}:")
                _imprime_comparacao(braco, it, base_dict, m)
        return 0

    print(f"config hash={cfg.hash} seed={seed} sujeitos={len(sujeitos)} item={args.item}")
    base = _carregar_base_com_cache(sujeitos, cfg, pasta=args.pasta)

    Xn = {n: normalizar_por_sujeito(base[n]["X"], base[n]["id"]) for n in NOMES_BRACOS}
    y = {n: base[n]["y"] for n in NOMES_BRACOS}
    ids = {n: base[n]["id"] for n in NOMES_BRACOS}

    base_dict_por_braco = resultado["itens"].get("baseline")

    # Parte do que já existe: nos itens com checkpoint, uma chamada anterior
    # pode ter fechado um braço e parado no meio do seguinte. Reescrever o
    # dicionário do zero apagaria o braço fechado.
    resultado_item: dict[str, dict] = dict(resultado["itens"].get(args.item, {}))
    print(f"\n=== item {args.item} ===")
    for nome in NOMES_BRACOS:
        print(f"  {nome}:")
        base_dict = base_dict_por_braco[nome] if base_dict_por_braco else None

        if args.item in ("8b", "9") and nome in resultado_item:
            print("    já completo em chamada anterior — pulando")
            _imprime_comparacao(nome, args.item, base_dict, resultado_item[nome])
            continue

        if args.item == "baseline":
            X_ctx = empilhar_contexto(Xn[nome], cfg.contexto_epocas)
            m, _ = _diagonal(X_ctx, y[nome], ids[nome], seed, class_weight="balanced")
            resultado_item[nome] = m.dict()
            _imprime_comparacao(nome, args.item, None, m.dict())

        elif args.item == "6":
            X_ctx = empilhar_contexto(Xn[nome], cfg.contexto_epocas)
            m, _ = _diagonal(X_ctx, y[nome], ids[nome], seed, class_weight=None)
            resultado_item[nome] = m.dict()
            _imprime_comparacao(nome, args.item, base_dict, m.dict())

        elif args.item == "7":
            X_ctx = empilhar_contexto(Xn[nome], cfg.contexto_epocas)
            m = _diagonal_youden(X_ctx, y[nome], ids[nome], seed)
            resultado_item[nome] = m.dict()
            _imprime_comparacao(nome, args.item, base_dict, m.dict())

        elif args.item == "8":
            X_ctx = empilhar_contexto(Xn[nome], cfg.contexto_epocas)
            _, pred_bruta = _diagonal(X_ctx, y[nome], ids[nome], seed, class_weight="balanced")
            suave = np.zeros_like(pred_bruta)
            for s in sorted(set(ids[nome].tolist())):
                m_ids = ids[nome] == s
                suave[m_ids] = suavizar_mediana(pred_bruta[m_ids])
            m = avaliar_por_sujeito(y[nome], suave, ids[nome], metricas=METRICAS, seed=seed)
            resultado_item[nome] = m.dict()
            _imprime_comparacao(nome, args.item, base_dict, m.dict())

        elif args.item in ("8b", "9"):
            # Os dois itens caros. Rodam por dobra, com checkpoint em disco:
            # a chamada processa o que couber no orçamento e sai; a próxima
            # retoma. Ver experimentos/_retomada.py.
            if args.item == "8b":
                X_ctx = empilhar_contexto(Xn[nome], cfg.contexto_epocas)
                dobra, rotulo_ctx = _dobra_hmm, f"ctx{cfg.contexto_epocas}_hmm"
            else:
                X_ctx = empilhar_contexto(Xn[nome], args.contexto_largo)
                dobra, rotulo_ctx = _dobra_logistica, f"ctx{args.contexto_largo}"

            chave = f"{cfg.hash}|{args.item}|{nome}|{rotulo_ctx}|{len(sujeitos)}suj"
            restante = args.orcamento_s - (time.time() - t_inicio)
            if restante < 10:
                print(f"    (orçamento da chamada esgotado antes de {nome} — rode de novo)")
                incompleto = True
                continue

            pred, completo, feitas, total = loso_com_retomada(
                chave, X_ctx, y[nome], ids[nome], dobra, seed, orcamento_s=restante)
            if not completo:
                print(f"    {feitas}/{total} dobras — parcial salvo, rode de novo para continuar")
                incompleto = True
                continue

            m = avaliar_por_sujeito(y[nome], pred, ids[nome], metricas=METRICAS, seed=seed)
            resultado_item[nome] = m.dict()
            print(f"    {feitas}/{total} dobras — COMPLETO")
            _imprime_comparacao(nome, args.item, base_dict, m.dict())

    resultado["itens"][args.item] = resultado_item
    destino.write_text(json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nsalvo em {destino.relative_to(RAIZ)}")
    if incompleto:
        faltam = [n for n in NOMES_BRACOS if n not in resultado_item]
        print(f"INCOMPLETO — faltam os braços: {', '.join(faltam)}. "
              f"Rode o mesmo comando de novo (retoma do checkpoint).")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
