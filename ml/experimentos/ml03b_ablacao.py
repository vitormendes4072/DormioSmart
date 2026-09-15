"""ML-03b -- ablação: H1 (artefato de escala) vs H2 (ruído como regularização)
na assimetria de transferência do ML-03, mais otimizações de especificidade.

Uso:
    python -m experimentos.ml03b_ablacao
    python -m experimentos.ml03b_ablacao --n-sujeitos 10   # piloto rápido

=============================================================================
POR QUE ESTE SCRIPT EXISTE
=============================================================================
O ML-03 mediu uma assimetria não prevista: um modelo treinado em "cabeça"
(Zmax original, 256 Hz / 12 bits) transfere mal para qualquer outro domínio
(Δκ +0,33 a +0,35), mas um modelo treinado em "cabeça_e4" ou "pulso" (ambos
na grade do Empatica, 32 Hz / 8 bits) transfere quase sem perda entre si e de
volta para a cabeça original. Duas explicações competem, e a diferença entre
elas muda o que o TCC afirma:

  H1 -- artefato de escala. `StandardScaler` (dentro do pipeline de
        `regressao_logistica`) é ajustado na distribuição do domínio de
        TREINO; aplicado a um domínio de distribuição diferente, joga as
        features fora da faixa em que o classificador foi calibrado. Se for
        isso, é bug metodológico a corrigir, não achado.
  H2 -- ruído como regularização. Treinar em dado mais grosseiro equivale, na
        prática, a treinar com injeção de ruído -- um regularizador
        conhecido -- e produz um classificador genuinamente mais robusto a
        mudança de domínio. Se for isso, é resultado real.

Cinco experimentos tentam separar as duas, e TODOS rodam (não só o primeiro
que der sinal):

  1. Reajustar só o SCALER no domínio de teste, mantendo os coeficientes do
     classificador (ajustados no domínio de treino). Se a assimetria some,
     é H1. Se persiste, é evidência de H2.
  2. Sem scaler nenhum -- regressão logística sobre features cruas.
  3. Random Forest -- invariante a escala por construção. O falseador mais
     limpo: se a assimetria desaparecer aqui, H1 confirmada; se persistir,
     H1 está morta (não há scaler para culpar).
  4. Caracterização numérica da divergência entre domínios: média, desvio e
     diferença padronizada (Cohen's d) de cada uma das 8 features, por par de
     domínios -- para medir, não presumir, se a cabeça está mais longe das
     outras duas do que elas entre si.
  5. Normalização por SUJEITO (z-score dentro de cada sujeito, usando só as
     próprias épocas dele) em vez de por domínio. Não usa rótulo nenhum do
     sujeito de teste -- só a estatística da própria série de movimento --
     então não é vazamento. Se resolver a assimetria, é diagnóstico E é a
     correção certa para o produto (cada usuário tem sua própria linha de
     base).

=============================================================================
Depois: quatro otimizações voltadas à especificidade
=============================================================================
  6. `class_weight="balanced"` -- JÁ é o padrão em `regressao_logistica()`
     (src/modelos.py). Aqui mede-se o CONTRAFACTUAL: o que aconteceria sem.
  7. Limiar de decisão por índice de Youden, escolhido no TREINO de cada
     fold (nunca no teste).
  8. Suavização temporal (mediana móvel, por sujeito).
  9. Janela de contexto mais larga (a atual é ±2 épocas; o Sadeh usa ~11 min
     ≈ ±11 épocas de 30 s).

Cada item roda nos três braços (diagonal -- mesmo domínio treino/teste) e
reporta κ, especificidade e IC 95% ao lado do valor de referência, com a
pergunta explícita: o ganho é maior que o IC, ou está dentro do ruído?
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

from sklearn.linear_model import LogisticRegression                         # noqa: E402
from sklearn.preprocessing import StandardScaler                            # noqa: E402

from src.avaliar import MetricasAgregadas, avaliar_por_sujeito, split_por_sujeito  # noqa: E402
from src.baseline import calibrar_escala, sadeh, sempre_dormindo            # noqa: E402
from src.carregar.base import ConjuntoEpocas                                # noqa: E402
from src.carregar.wearanize import carregar_wearanize, sujeitos_com_posicoes  # noqa: E402
from src.configuracao import carregar_config, fixar_seed                    # noqa: E402
from src.epocas import empilhar_contexto, fatiar_epocas                     # noqa: E402
from src.features import NOMES_FEATURES, features_de_epoca                  # noqa: E402
from src.modelos import random_forest, regressao_logistica, suavizar_mediana  # noqa: E402
from src.sinal import reamostrar                                            # noqa: E402
from src.baseline import substituto_de_contagem                             # noqa: E402

BRACOS: dict[str, tuple[str, str]] = {
    "cabeca": ("cabeca", "original"),
    "cabeca_e4": ("cabeca", "e4"),
    "pulso": ("pulso", "original"),
}
NOMES_BRACOS = list(BRACOS)
METRICAS = ("acuracia", "especificidade", "kappa")


# =========================================================================
# Carregamento -- uma vez só, sem empilhar contexto (para poder variar a
# janela no item 9 sem reler os EDFs)
# =========================================================================

def carregar_base(sujeitos: list[str], cfg, pasta=None) -> dict[str, dict]:
    """Por braço: X (n_epocas, 8) SEM contexto, y, id_sujeito, e o substituto
    de contagem c/y_c/id_c -- tudo numa passada só sobre o dado bruto."""
    kwargs = {"pasta": pasta} if pasta else {}
    lo, hi = cfg.baseline["banda_contagem_hz"]
    saida: dict[str, dict] = {}
    for nome, (posicao, qualidade) in BRACOS.items():
        gravacoes = carregar_wearanize(posicao=posicao, qualidade=qualidade, sujeitos=sujeitos, **kwargs)
        Xs, ys, ids, cs, ys_c, ids_c = [], [], [], [], [], []
        for gr in gravacoes:
            t, a = reamostrar(gr.t, gr.a, cfg.taxa_comum_hz, cfg.corte_antialiasing_frac_nyquist)
            a_ep, idx = fatiar_epocas(t, a, gr.t0_rotulo, int(gr.rotulos.shape[0]),
                                      cfg.epoca_s, cfg.taxa_comum_hz)
            if a_ep.shape[0] == 0:
                continue
            y_ep = gr.rotulos[idx]
            ok = y_ep >= 0
            if not ok.any():
                continue
            y_ok = y_ep[ok]
            ids_ok = np.full(int(ok.sum()), gr.id_sujeito, dtype=object)

            X, _ = features_de_epoca(a_ep, fs=cfg.taxa_comum_hz)
            Xs.append(X[ok]); ys.append(y_ok); ids.append(ids_ok)

            c = substituto_de_contagem(a_ep, cfg.taxa_comum_hz, (float(lo), float(hi)),
                                       float(cfg.baseline["escala_contagem"]))
            cs.append(c[ok]); ys_c.append(y_ok); ids_c.append(ids_ok)

        saida[nome] = dict(
            X=np.concatenate(Xs), y=np.concatenate(ys), id=np.concatenate(ids),
            c=np.concatenate(cs), y_c=np.concatenate(ys_c), id_c=np.concatenate(ids_c),
        )
        print(f"  {nome:<10} {saida[nome]['X'].shape[0]} épocas · "
              f"{len(set(saida[nome]['id'].tolist()))} sujeitos", file=sys.stderr)
    return saida


def montar_X(base: dict, nome: str, n_vizinhas: int) -> np.ndarray:
    return empilhar_contexto(base[nome]["X"], n_vizinhas)


# =========================================================================
# Item 4 -- caracterização numérica da divergência entre domínios
# =========================================================================

def caracterizar_divergencia(base: dict) -> dict:
    """Média, desvio e Cohen's d por feature, para cada par de braços --
    sobre as 8 features SEM contexto (o contexto só duplicaria a mesma
    informação deslocada)."""
    stats = {}
    for nome in NOMES_BRACOS:
        X = base[nome]["X"]
        stats[nome] = {"media": X.mean(axis=0), "desvio": X.std(axis=0, ddof=1)}

    pares = [("cabeca", "cabeca_e4"), ("cabeca", "pulso"), ("cabeca_e4", "pulso")]
    resultado = {"por_feature": {}, "distancia_multivariada": {}}
    # z-score global por feature (pooled nos 3 braços) para a distância multivariada
    tudo = np.concatenate([base[n]["X"] for n in NOMES_BRACOS], axis=0)
    escala_global = tudo.std(axis=0, ddof=1)
    escala_global[escala_global < 1e-12] = 1.0

    for a, b in pares:
        d_por_feature = []
        for i, feat in enumerate(NOMES_FEATURES):
            ma, sa = stats[a]["media"][i], stats[a]["desvio"][i]
            mb, sb = stats[b]["media"][i], stats[b]["desvio"][i]
            sp = np.sqrt((sa**2 + sb**2) / 2.0)
            d = abs(ma - mb) / sp if sp > 1e-12 else float("nan")
            d_por_feature.append(float(d))
        resultado["por_feature"][f"{a}~{b}"] = dict(zip(NOMES_FEATURES, d_por_feature))
        # distância euclidiana entre os vetores de média, em unidades de dp GLOBAL
        va = (stats[a]["media"] - stats[b]["media"]) / escala_global
        resultado["distancia_multivariada"][f"{a}~{b}"] = float(np.linalg.norm(va))

    resultado["estatisticas_por_braco"] = {
        nome: {"media": stats[nome]["media"].tolist(), "desvio": stats[nome]["desvio"].tolist()}
        for nome in NOMES_BRACOS
    }
    return resultado


# =========================================================================
# Matriz de transferência genérica -- parametrizada pelo "modo" de
# treino/predição, para reusar o mesmo laço de folds nos itens 1, 2 e 3
# =========================================================================

def matriz_generica(Xs: dict[str, np.ndarray], ys: dict[str, np.ndarray],
                     ids: dict[str, np.ndarray], seed: int, modo: str) -> dict:
    """modo: "logistica" (com scaler normal), "sem_scaler", "rf" (Random
    Forest), ou "rescaler_teste" (scaler refeito no domínio de teste,
    coeficientes do classificador vindos do domínio de treino)."""
    nomes = list(Xs)
    conjuntos_sujeitos = [set(ids[n].tolist()) for n in nomes]
    sujeitos = sorted(set.intersection(*conjuntos_sujeitos))

    preds = {(tr, te): np.zeros(Xs[te].shape[0], dtype=int) for tr in nomes for te in nomes}

    for k, s in enumerate(sujeitos, 1):
        ajustes = {}   # tr -> (objeto que sabe prever)
        scalers_teste = {}  # te -> StandardScaler fit no domínio de teste, excluindo s

        for tr in nomes:
            mask_tr = ids[tr] != s
            X_tr, y_tr = Xs[tr][mask_tr], ys[tr][mask_tr]
            if modo == "logistica":
                m = regressao_logistica(seed)
                m.fit(X_tr, y_tr)
                ajustes[tr] = ("pipeline", m)
            elif modo == "sem_scaler":
                # max_iter baixo DE PROPÓSITO: sobre features cruas (escalas
                # bem diferentes entre si) o LBFGS não converge nem com 2000
                # iterações -- confirmado rodando contra o dado real, onde
                # isso tornou esta única célula mais lenta que o resto do
                # script inteiro somado. 300 ainda não converge (o aviso
                # continua saindo, e é esperado), mas falha rápido em vez de
                # gastar as 2000 iterações inteiras 276 vezes -- não muda a
                # comparação qualitativa entre braços, que é o que este modo
                # existe para medir.
                clf = LogisticRegression(max_iter=300, class_weight="balanced", random_state=seed)
                clf.fit(X_tr, y_tr)
                ajustes[tr] = ("cru", clf)
            elif modo == "rf":
                m = random_forest(seed)
                m.fit(X_tr, y_tr)
                ajustes[tr] = ("cru", m)
            elif modo == "rescaler_teste":
                scaler_src = StandardScaler().fit(X_tr)
                clf = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=seed)
                clf.fit(scaler_src.transform(X_tr), y_tr)
                ajustes[tr] = ("clf_puro", clf)
            else:
                raise ValueError(modo)

        if modo == "rescaler_teste":
            for te in nomes:
                mask_te_outros = ids[te] != s
                scalers_teste[te] = StandardScaler().fit(Xs[te][mask_te_outros])

        for te in nomes:
            mask_te = ids[te] == s
            if not mask_te.any():
                continue
            X_te_s = Xs[te][mask_te]
            for tr in nomes:
                tipo, obj = ajustes[tr]
                if tipo in ("pipeline", "cru"):
                    preds[(tr, te)][mask_te] = obj.predict(X_te_s)
                elif tipo == "clf_puro":
                    X_te_z = scalers_teste[te].transform(X_te_s)
                    preds[(tr, te)][mask_te] = obj.predict(X_te_z)
        if k % 20 == 0 or k == len(sujeitos):
            print(f"\r[{modo}] fold {k}/{len(sujeitos)}", end="", file=sys.stderr)
    print(file=sys.stderr)

    resultado = {}
    for tr in nomes:
        for te in nomes:
            mask = np.isin(ids[te], sujeitos)
            resultado[(tr, te)] = avaliar_por_sujeito(
                ys[te][mask], preds[(tr, te)][mask], ids[te][mask], metricas=METRICAS, seed=seed,
            )
    return resultado


def imprimir_matriz_kappa(matriz: dict, titulo: str) -> None:
    largura = 13
    print(f"\n{titulo}")
    print(" " * (largura + 1) + "".join(f"{n:>{largura}}" for n in NOMES_BRACOS))
    for tr in NOMES_BRACOS:
        linha = [f"{matriz[(tr, te)].media['kappa']:>{largura}.3f}" for te in NOMES_BRACOS]
        print(f"{tr:<{largura}}" + "".join(linha))
    print("  Δκ por linha (κ_diag − κ_transf):")
    for tr in NOMES_BRACOS:
        ref = matriz[(tr, tr)].media["kappa"]
        linha = [f"{ref - matriz[(tr, te)].media['kappa']:>{largura}.3f}" for te in NOMES_BRACOS]
        print(f"{tr:<{largura}}" + "".join(linha))


# =========================================================================
# Item 5 -- normalização por sujeito
# =========================================================================

def normalizar_por_sujeito(X: np.ndarray, ids: np.ndarray) -> np.ndarray:
    """z-score de cada sujeito usando SÓ as próprias épocas -- não usa rótulo,
    não é vazamento: é a estatística de movimento do próprio sujeito, que um
    produto real também tem disponível sem precisar da verdade de PSG."""
    Xn = np.empty_like(X, dtype=float)
    for s in set(ids.tolist()):
        m = ids == s
        media = X[m].mean(axis=0)
        desvio = X[m].std(axis=0, ddof=1)
        desvio[desvio < 1e-9] = 1.0
        Xn[m] = (X[m] - media) / desvio
    return Xn


# =========================================================================
# Item 7 -- limiar por índice de Youden, escolhido no treino
# =========================================================================

def _limiar_youden(y_true: np.ndarray, proba: np.ndarray, n_candidatos: int = 199) -> float:
    """Maximiza sensibilidade+especificidade-1 sobre uma grade de limiares.

    Vetorizado sobre a grade inteira de uma vez (broadcasting), não um laço
    Python por limiar -- com dezenas de milhares de épocas por fold de treino,
    testar cada valor ÚNICO de probabilidade seria O(n²) e levaria horas.
    """
    y = np.asarray(y_true, dtype=int)
    candidatos = np.linspace(0.0, 1.0, n_candidatos)
    pred = proba[:, None] >= candidatos[None, :]           # (n, n_candidatos)
    pos = (y == 1)[:, None]
    vp = np.count_nonzero(pred & pos, axis=0)
    fn = np.count_nonzero(~pred & pos, axis=0)
    vn = np.count_nonzero(~pred & ~pos, axis=0)
    fp = np.count_nonzero(pred & ~pos, axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        sens = np.where((vp + fn) > 0, vp / np.maximum(vp + fn, 1), 0.0)
        espec = np.where((vn + fp) > 0, vn / np.maximum(vn + fp, 1), 0.0)
    j = sens + espec - 1.0
    return float(candidatos[int(np.argmax(j))])


def diagonal_com_limiar_youden(X: np.ndarray, y: np.ndarray, ids: np.ndarray, seed: int) -> MetricasAgregadas:
    pred = np.zeros_like(y)
    for _, tr, te in split_por_sujeito(ids):
        m = regressao_logistica(seed)
        m.fit(X[tr], y[tr])
        proba_treino = m.predict_proba(X[tr])[:, 1]
        limiar = _limiar_youden(y[tr], proba_treino)
        proba_teste = m.predict_proba(X[te])[:, 1]
        pred[te] = (proba_teste >= limiar).astype(int)
    return avaliar_por_sujeito(y, pred, ids, metricas=METRICAS, seed=seed)


# =========================================================================
# Diagonal padrão (referência) + variantes 6, 8, 9
# =========================================================================

def diagonal_padrao(X, y, ids, seed) -> tuple[MetricasAgregadas, np.ndarray]:
    pred = np.zeros_like(y)
    for _, tr, te in split_por_sujeito(ids):
        m = regressao_logistica(seed)
        m.fit(X[tr], y[tr])
        pred[te] = m.predict(X[te])
    return avaliar_por_sujeito(y, pred, ids, metricas=METRICAS, seed=seed), pred


def diagonal_sem_balanceamento(X, y, ids, seed) -> MetricasAgregadas:
    """Mesma estrutura da referência (scaler ajustado no treino), só troca
    `class_weight="balanced"` por `None` -- isola o efeito desse UM parâmetro."""
    pred = np.zeros_like(y)
    for _, tr, te in split_por_sujeito(ids):
        scaler = StandardScaler().fit(X[tr])
        clf = LogisticRegression(max_iter=2000, class_weight=None, random_state=seed)
        clf.fit(scaler.transform(X[tr]), y[tr])
        pred[te] = clf.predict(scaler.transform(X[te]))
    return avaliar_por_sujeito(y, pred, ids, metricas=METRICAS, seed=seed)


def diagonal_suavizada(pred_bruta: np.ndarray, y: np.ndarray, ids: np.ndarray, seed: int) -> MetricasAgregadas:
    suave = np.zeros_like(pred_bruta)
    for s in sorted(set(ids.tolist())):
        m = ids == s
        suave[m] = suavizar_mediana(pred_bruta[m])
    return avaliar_por_sujeito(y, suave, ids, metricas=METRICAS, seed=seed)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-sujeitos", type=int, default=None)
    ap.add_argument("--pasta", type=Path, default=None)
    ap.add_argument("--contexto-largo", type=int, default=11,
                     help="nº de épocas vizinhas p/ o item 9 (padrão ±11 ~ janela do Sadeh)")
    args = ap.parse_args()

    cfg = carregar_config()
    fixar_seed(cfg.seed)
    seed = cfg.seed

    sujeitos = sujeitos_com_posicoes(["cabeca", "pulso"], **({"pasta": args.pasta} if args.pasta else {}))
    if args.n_sujeitos:
        sujeitos = sujeitos[: args.n_sujeitos]
    print(f"config hash={cfg.hash} · seed={seed} · sujeitos={len(sujeitos)}")

    # Cache em disco do carregamento bruto (a etapa mais cara -- ~20 min lendo
    # 92 EDFs de ~500 MB a 256 Hz). Um processo em segundo plano já morreu no
    # meio deste script uma vez (sessão encerrada por fora) -- sem isto, cada
    # nova tentativa paga de novo o mesmo custo antes de chegar ao que
    # realmente pode falhar (o item 2, que não converge). O cache é só um
    # pickle; se o hash do config ou a lista de sujeitos mudar, o nome do
    # arquivo muda junto, então nunca serve dado velho por engano.
    import hashlib
    import pickle
    cache_chave = hashlib.sha256(
        (cfg.hash + "|" + ",".join(sujeitos)).encode("utf-8")
    ).hexdigest()[:16]
    cache_caminho = RAIZ / "dados" / "processado" / f"_cache_base_wearanize_{cache_chave}.pkl"
    if cache_caminho.exists():
        print(f"Cache encontrado ({cache_caminho.name}), pulando releitura dos EDFs...", file=sys.stderr)
        with open(cache_caminho, "rb") as fh:
            base = pickle.load(fh)
    else:
        print("Carregando os três braços (sem empilhar contexto ainda)...", file=sys.stderr)
        base = carregar_base(sujeitos, cfg, pasta=args.pasta)
        cache_caminho.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_caminho, "wb") as fh:
            pickle.dump(base, fh, protocol=pickle.HIGHEST_PROTOCOL)
        print(f"Cache salvo em {cache_caminho.name}", file=sys.stderr)

    resultado_json: dict = {
        "experimento": "ML-03b -- ablacao H1/H2 + otimizacoes de especificidade",
        "hash_config": cfg.hash, "seed": seed, "n_sujeitos": len(sujeitos),
    }

    saida = RAIZ / "experimentos" / "saida"
    saida.mkdir(parents=True, exist_ok=True)
    carimbo = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destino = saida / f"ml03b_ablacao_{cfg.hash}_{carimbo}.json"

    def salvar(parcial: bool) -> None:
        """Grava o que já foi calculado depois de CADA item -- se o processo
        precisar ser interrompido (o item 2, sem scaler, não converge e pode
        ser lento), o resultado parcial não se perde."""
        resultado_json["parcial"] = parcial
        resultado_json["config"] = cfg.bruto
        destino.write_text(json.dumps(resultado_json, indent=2, ensure_ascii=False), encoding="utf-8")

    # ---------------------------------------------------------------
    # Item 4 -- caracterização da divergência (não precisa de modelo)
    # ---------------------------------------------------------------
    print("\n" + "=" * 70)
    print("ITEM 4 -- divergência entre domínios (Cohen's d por feature)")
    print("=" * 70)
    divergencia = caracterizar_divergencia(base)
    for par, dist in divergencia["distancia_multivariada"].items():
        print(f"  distância multivariada {par}: {dist:.3f} (unidades de dp global)")
    print("\n  Cohen's d por feature (cabeca~cabeca_e4 vs cabeca~pulso vs cabeca_e4~pulso):")
    for feat in NOMES_FEATURES:
        d1 = divergencia["por_feature"]["cabeca~cabeca_e4"][feat]
        d2 = divergencia["por_feature"]["cabeca~pulso"][feat]
        d3 = divergencia["por_feature"]["cabeca_e4~pulso"][feat]
        print(f"    {feat:<16} cabeca~cabeca_e4={d1:6.3f}  cabeca~pulso={d2:6.3f}  cabeca_e4~pulso={d3:6.3f}")
    resultado_json["item4_divergencia"] = divergencia
    salvar(parcial=True)

    # ---------------------------------------------------------------
    # Referência: matriz padrão (contexto=2, com scaler, balanceado)
    # ---------------------------------------------------------------
    print("\n" + "=" * 70)
    print("REFERÊNCIA -- matriz padrão (contexto=±2, com scaler, balanceado)")
    print("=" * 70)
    Xs_ref = {n: montar_X(base, n, cfg.contexto_epocas) for n in NOMES_BRACOS}
    ys_ref = {n: base[n]["y"] for n in NOMES_BRACOS}
    ids_ref = {n: base[n]["id"] for n in NOMES_BRACOS}
    matriz_ref = matriz_generica(Xs_ref, ys_ref, ids_ref, seed, modo="logistica")
    imprimir_matriz_kappa(matriz_ref, "REFERÊNCIA")
    resultado_json["referencia"] = {f"{a}->{b}": m.dict() for (a, b), m in matriz_ref.items()}
    salvar(parcial=True)

    # ---------------------------------------------------------------
    # Item 1 -- rescaler no domínio de teste
    # ---------------------------------------------------------------
    print("\n" + "=" * 70)
    print("ITEM 1 -- scaler refeito no domínio de TESTE, coeficientes do TREINO")
    print("=" * 70)
    matriz_rescaler = matriz_generica(Xs_ref, ys_ref, ids_ref, seed, modo="rescaler_teste")
    imprimir_matriz_kappa(matriz_rescaler, "RESCALER-NO-TESTE")
    resultado_json["item1_rescaler_teste"] = {f"{a}->{b}": m.dict() for (a, b), m in matriz_rescaler.items()}
    salvar(parcial=True)

    # ---------------------------------------------------------------
    # Item 3 -- Random Forest (invariante a escala) -- ANTES do item 2 de
    # propósito: é o falseador mais limpo (sem scaler para culpar), e o item
    # 2 (logística sem scaler) é lento por não convergir -- se algo travar ou
    # precisar ser interrompido, o resultado que decide entre H1 e H2 já
    # está seguro.
    # ---------------------------------------------------------------
    print("\n" + "=" * 70)
    print("ITEM 3 -- Random Forest (invariante a escala por construção)")
    print("=" * 70)
    matriz_rf = matriz_generica(Xs_ref, ys_ref, ids_ref, seed, modo="rf")
    imprimir_matriz_kappa(matriz_rf, "RANDOM FOREST")
    resultado_json["item3_random_forest"] = {f"{a}->{b}": m.dict() for (a, b), m in matriz_rf.items()}
    salvar(parcial=True)

    # ---------------------------------------------------------------
    # Item 2 -- sem scaler nenhum
    # ---------------------------------------------------------------
    print("\n" + "=" * 70)
    print("ITEM 2 -- regressão logística SEM scaler (features cruas)")
    print("=" * 70)
    matriz_sem_scaler = matriz_generica(Xs_ref, ys_ref, ids_ref, seed, modo="sem_scaler")
    imprimir_matriz_kappa(matriz_sem_scaler, "SEM SCALER")
    resultado_json["item2_sem_scaler"] = {f"{a}->{b}": m.dict() for (a, b), m in matriz_sem_scaler.items()}
    salvar(parcial=True)

    # ---------------------------------------------------------------
    # Item 5 -- normalização por sujeito
    # ---------------------------------------------------------------
    print("\n" + "=" * 70)
    print("ITEM 5 -- normalização por SUJEITO (z-score individual) + logística sem scaler extra")
    print("=" * 70)
    Xs_suj = {n: montar_X(
        {n: dict(X=normalizar_por_sujeito(base[n]["X"], base[n]["id"]))}, n, cfg.contexto_epocas
    ) for n in NOMES_BRACOS}
    matriz_suj = matriz_generica(Xs_suj, ys_ref, ids_ref, seed, modo="sem_scaler")
    imprimir_matriz_kappa(matriz_suj, "NORMALIZAÇÃO POR SUJEITO")
    resultado_json["item5_normalizacao_por_sujeito"] = {f"{a}->{b}": m.dict() for (a, b), m in matriz_suj.items()}
    salvar(parcial=True)

    # ---------------------------------------------------------------
    # Itens 6-9 -- otimizações de especificidade, na DIAGONAL de cada braço
    # ---------------------------------------------------------------
    print("\n" + "=" * 70)
    print("ITENS 6-9 -- otimizações de especificidade (diagonal por braço)")
    print("=" * 70)
    resultado_json["otimizacoes"] = {}
    for nome in NOMES_BRACOS:
        X = Xs_ref[nome]
        y, ids = ys_ref[nome], ids_ref[nome]
        print(f"\n  === {nome} ===")

        ref = matriz_ref[(nome, nome)]
        print(f"    referência (contexto=±2, balanceado): kappa={ref.resumo('kappa')}  espec={ref.resumo('especificidade')}")

        m6 = diagonal_sem_balanceamento(X, y, ids, seed)
        print(f"    (6) SEM class_weight=balanced:         kappa={m6.resumo('kappa')}  espec={m6.resumo('especificidade')}")

        m7 = diagonal_com_limiar_youden(X, y, ids, seed)
        print(f"    (7) limiar por Youden (escolhido no treino): kappa={m7.resumo('kappa')}  espec={m7.resumo('especificidade')}")

        _, pred_bruta = diagonal_padrao(X, y, ids, seed)
        m8 = diagonal_suavizada(pred_bruta, y, ids, seed)
        print(f"    (8) suavização temporal (mediana móvel):     kappa={m8.resumo('kappa')}  espec={m8.resumo('especificidade')}")

        X_largo = montar_X(base, nome, args.contexto_largo)
        m9, _ = diagonal_padrao(X_largo, base[nome]["y"], base[nome]["id"], seed)
        print(f"    (9) contexto largo (±{args.contexto_largo} épocas):        kappa={m9.resumo('kappa')}  espec={m9.resumo('especificidade')}")

        resultado_json["otimizacoes"][nome] = {
            "referencia": ref.dict(),
            "sem_balanceamento": m6.dict(),
            "limiar_youden": m7.dict(),
            "suavizacao_temporal": m8.dict(),
            f"contexto_largo_{args.contexto_largo}": m9.dict(),
        }

    salvar(parcial=False)
    print(f"\nlog: {destino.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
