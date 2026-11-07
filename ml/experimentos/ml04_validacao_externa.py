"""ML-04 — validação externa: treina no Wearanize+, testa em coorte independente.

O que este experimento responde
----------------------------------------------------------------
Tudo que veio antes (ML-02, ML-03, ML-03b) é leave-one-subject-out DENTRO do
Wearanize+. Isso controla vazamento entre sujeitos, e não controla nada
entre COORTES: mesmo aparelho, mesmo protocolo de PSG, mesmo laboratório,
mesma pontuadora. Um modelo pode ir bem em LOSO e desabar em outro hospital
com outro acelerômetro — é o modo de falha padrão da literatura de
actigrafia, e é o que a banca vai perguntar.

Aqui o modelo é ajustado nos 92 sujeitos do Wearanize+ **de uma vez** e
aplicado ao Newcastle 2015 **sem reajuste de nada**: sem refazer scaler no
domínio de teste, sem recalibrar limiar, sem olhar rótulo do Newcastle em
momento nenhum antes de medir. É transferência a frio.

⚠️ O que NÃO é comparável, e por quê
----------------------------------------------------------------
Os números do Newcastle não podem ser lidos lado a lado com os do LOSO como
se fossem a mesma escala. A prevalência de sono é diferente (Newcastle
~70%, Wearanize+ ~85%), e kappa depende da prevalência. A leitura honesta é
o SINAL: o modelo continua acima do trivial na coorte nova, ou não?

Por isso toda tabela de saída traz o baseline trivial ("sempre dormindo")
medido no PRÓPRIO Newcastle, ao lado. É a única referência que não
atravessa coortes.

As duas fases
----------------------------------------------------------------
    python -m experimentos.ml04_validacao_externa --preparar   # repetir até COMPLETO
    python -m experimentos.ml04_validacao_externa --rodar

`--preparar` extrai as features do Newcastle uma gravação por vez e guarda
um .npz por gravação. É retomável pelo mesmo motivo do
`experimentos/_retomada.py`: ler 55 .bin de ~12 h não cabe numa chamada de
shell, e ler tudo de novo a cada interrupção já custou caro nesta sessão.

Punho
----------------------------------------------------------------
O Newcastle tem os dois punhos de quase todo participante. O braço "pulso"
do Wearanize+ é um Empatica E4, usado no punho não dominante, e o protocolo
do Newcastle (van Hees et al. 2015) também especifica o não dominante — que
o dataset não identifica arquivo a arquivo. `--punho esquerdo` (padrão) fixa
um lado para não misturar dois registros do mesmo sujeito na mesma medida;
`--punho ambos` mede os dois e serve para dimensionar quanto o lado importa.

Segunda coorte: Walch et al. (2019) — ML-06
----------------------------------------------------------------
    python -m experimentos.ml04_validacao_externa --coorte walch --preparar
    python -m experimentos.ml04_validacao_externa --coorte walch --rodar
    python -m experimentos.ml04_validacao_externa --coorte walch --rodar --incluir-baixa-taxa

O mesmo modelo, as mesmas configurações e o mesmo protocolo, com outro destino:
Apple Watch no pulso, 31 sujeitos, outro centro. A previsão e o adendo ao
protocolo foram registrados ANTES de rodar (diário, 03/11 (vii) e (viii)). A
análise principal exclui os 2 sujeitos de 10 Hz; `--incluir-baixa-taxa` é a
secundária. Os números do Newcastle não mudam com esta opção: o caminho dele é
o mesmo de antes.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

for _fluxo in (sys.stdout, sys.stderr):
    if hasattr(_fluxo, "reconfigure"):
        _fluxo.reconfigure(encoding="utf-8")

from src.avaliar import avaliar_epoca, avaliar_por_sujeito                 # noqa: E402
from src.carregar.wearanize import sujeitos_com_posicoes                   # noqa: E402
from src.configuracao import carregar_config, fixar_seed                   # noqa: E402
from src.cache_temporal import (VERSAO, caminho_base, ler_base, ler_features, salvar_features, segmentos_de)
from src.epocas import empilhar_contexto, fatiar_epocas, aplicar_por_segmento                    # noqa: E402
from src.features import features_de_epoca                                 # noqa: E402
from src.modelos import suavizar_hmm, transicoes_hmm                       # noqa: E402
from src.sinal import reamostrar                                           # noqa: E402

from experimentos.ml03b_ablacao import (                                   # noqa: E402
    METRICAS, NOMES_BRACOS, normalizar_por_sujeito,
)

PASTA_FEATURES = RAIZ / "dados" / "processado" / "newcastle_features_ml17-v1"
PASTA_FEATURES_WALCH = RAIZ / "dados" / "processado" / "walch_features_ml17-v1"

DADOS_BRUTOS = None
DADOS_WEARANIZE = None
PASTA_CACHE = RAIZ / "dados" / "processado"
PASTA_SAIDA = RAIZ / "experimentos" / "saida" / VERSAO

#: As configurações comparadas. A chave vira coluna na tabela de saída.
#: `contexto`: nº de épocas vizinhas empilhadas. `hmm`: Viterbi por cima.
CONFIGS = {
    "base_ctx2":      dict(contexto=2,  hmm=False),
    "item8b_hmm":     dict(contexto=2,  hmm=True),
    "item9_ctx11":    dict(contexto=11, hmm=False),
    "item9b_ctx11_hmm": dict(contexto=11, hmm=True),
}


# =========================================================================
# Fase 1 — extrair as features do Newcastle, uma gravação por chamada
# =========================================================================

def preparar(cfg, orcamento_s: float, punho: str,
             exceto: tuple[str, ...] = (), so: tuple[str, ...] = ()) -> tuple[int, int, int]:
    from src.carregar.newcastle import carregar_newcastle

    PASTA_FEATURES.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    feitas = existentes = 0

    def _lado(nome: str) -> str:
        return "direito" if "right" in nome.lower() else "esquerdo"

    def _alvo(id_sujeito: str, lado: str) -> Path:
        return PASTA_FEATURES / f"{cfg.hash}_{id_sujeito}_{lado}.npz"

    def _marcador(caminho: Path) -> Path:
        return PASTA_FEATURES / f"{cfg.hash}_{caminho.stem}.rejeitada"

    aprovados: list[Path] = []

    def aceitar(caminho, id_sujeito) -> bool:
        """Filtra ANTES de decodificar o .bin — ver `aceitar=` em
        src/carregar/newcastle.py. Sem isto, retomar relê tudo."""
        nonlocal existentes
        lado = _lado(caminho.name)
        if punho != "ambos" and lado != punho:
            return False
        if id_sujeito in exceto or (so and id_sujeito not in so):
            return False
        if _alvo(id_sujeito, lado).exists() or _marcador(caminho).exists():
            existentes += 1
            return False
        # Conta APROVADAS, não salvas: uma gravação que o carregador vai
        # rejeitar custa a mesma decodificação de uma que ele aceita, e se o
        # orçamento só contasse as salvas uma sequência de rejeições
        # estouraria a chamada sem nunca acionar o freio.
        if aprovados and (time.time() - t0) > orcamento_s:
            return False
        aprovados.append(caminho)
        return True

    processados: set[str] = set()
    for gr in carregar_newcastle(aceitar=aceitar, **({"pasta": DADOS_BRUTOS} if DADOS_BRUTOS else {})):
        processados.add(gr.meta.get("arquivo", ""))
        arquivo = gr.meta.get("arquivo", f"{gr.id_sujeito}.bin")
        lado = _lado(arquivo)
        alvo = _alvo(gr.id_sujeito, lado)

        t, a = reamostrar(gr.t, gr.a, cfg.taxa_comum_hz, cfg.corte_antialiasing_frac_nyquist)
        a_ep, idx = fatiar_epocas(t, a, gr.t0_rotulo, int(gr.rotulos.shape[0]),
                                  cfg.epoca_s, cfg.taxa_comum_hz)
        if a_ep.shape[0] == 0:
            print(f"  {gr.id_sujeito}/{lado}: nenhuma época — pulado", file=sys.stderr)
            continue
        y_ep = gr.rotulos[idx]
        ok = y_ep >= 0
        if not ok.any():
            print(f"  {gr.id_sujeito}/{lado}: nenhuma época pontuada — pulado", file=sys.stderr)
            continue

        X, _ = features_de_epoca(a_ep, fs=cfg.taxa_comum_hz)
        salvar_features(alvo, cfg, X=X[ok], y=y_ep[ok], id=gr.id_sujeito, lado=lado,
                        indice_epoca=idx[ok], gravacao=np.repeat(arquivo, int(ok.sum())))
        feitas += 1
        print(f"  {gr.id_sujeito}/{lado}: {int(ok.sum())} épocas -> {alvo.name}", file=sys.stderr)
        del gr, t, a, a_ep, X

    # Cache NEGATIVO. O carregador rejeita algumas gravações (o ncl029 tem o
    # PSG começando depois do fim do acelerômetro — ARMADILHA 5), e só
    # descobre isso DEPOIS de decodificar o .bin inteiro. Sem marcar a
    # rejeição, cada chamada seguinte paga a decodificação de novo antes de
    # chegar em trabalho útil, e com um .bin de 24 h isso sozinho estoura o
    # orçamento da chamada. O marcador guarda o motivo, para não virar um
    # arquivo mudo que esconde dado descartado.
    rejeitadas = 0
    for caminho in aprovados:
        if caminho.name in processados:
            continue
        marcador = _marcador(caminho)
        if not marcador.exists():
            marcador.write_text(
                "rejeitada pelo carregador (ver aviso '[newcastle] pulando' no log "
                "e ARMADILHA 5 em src/carregar/newcastle.py)\n", encoding="utf-8")
            rejeitadas += 1
            print(f"  {caminho.name}: rejeitada — marcada para não redecodificar",
                  file=sys.stderr)

    return feitas, existentes, rejeitadas


def carregar_features_newcastle(cfg, punho: str):
    arquivos = sorted(PASTA_FEATURES.glob(f"{cfg.hash}_*.npz"))
    Xs, ys, ids, segmentos = [], [], [], []
    for caminho in arquivos:
        d = ler_features(caminho, cfg)
        lado = str(d["lado"])
        if punho != "ambos" and lado != punho:
            continue
        sujeito = str(d["id"])
        # Com `--punho ambos` os dois registros do mesmo participante viram
        # sujeitos distintos de propósito: são noites diferentes do mesmo
        # aparelho em lados diferentes, e agregá-los numa métrica só
        # esconderia justamente a variação que o argumento existe para medir.
        rotulo = sujeito if punho != "ambos" else f"{sujeito}_{lado}"
        Xs.append(d["X"])
        ys.append(d["y"].astype(int))
        ids.append(np.full(d["y"].shape[0], rotulo, dtype=object))
        segmentos.append(np.char.add(caminho.name + ":", segmentos_de(d).astype(str)))
    if not Xs:
        raise FileNotFoundError(
            f"Nenhuma feature em {PASTA_FEATURES} para punho={punho}. "
            "Rode --preparar até dizer COMPLETO."
        )
    return np.concatenate(Xs), np.concatenate(ys), np.concatenate(ids), np.concatenate(segmentos)


def _variante_walch(incluir_baixa_taxa: bool) -> str:
    return "todos" if incluir_baixa_taxa else "principal"


def preparar_walch(cfg, incluir_baixa_taxa: bool) -> int:
    """Features da Walch, um .npz por sujeito. O mesmo caminho do Newcastle:
    reamostrar -> fatiar -> features, e só as épocas pontuadas. As épocas sem
    dado medido já chegam como −1 do carregador (ARMADILHA 4 de
    `src/carregar/walch.py`) e saem aqui, como as não pontuadas."""
    from src.carregar.walch import carregar_walch

    PASTA_FEATURES_WALCH.mkdir(parents=True, exist_ok=True)
    feitas = 0
    taxa_min = None if incluir_baixa_taxa else cfg.taxa_comum_hz
    variante = _variante_walch(incluir_baixa_taxa)
    for gr in carregar_walch(taxa_minima_hz=taxa_min, **({"pasta": DADOS_BRUTOS} if DADOS_BRUTOS else {})):
        alvo = PASTA_FEATURES_WALCH / f"{cfg.hash}_{variante}_{gr.id_sujeito}.npz"
        if alvo.exists():
            continue
        t, a = reamostrar(gr.t, gr.a, cfg.taxa_comum_hz, cfg.corte_antialiasing_frac_nyquist)
        a_ep, idx = fatiar_epocas(t, a, gr.t0_rotulo, int(gr.rotulos.shape[0]),
                                  cfg.epoca_s, cfg.taxa_comum_hz)
        y_ep = gr.rotulos[idx]
        ok = y_ep >= 0
        if a_ep.shape[0] == 0 or not ok.any():
            print(f"  {gr.id_sujeito}: nenhuma época pontuada com dado — pulado", file=sys.stderr)
            continue
        X, _ = features_de_epoca(a_ep, fs=cfg.taxa_comum_hz)
        salvar_features(alvo, cfg, X=X[ok], y=y_ep[ok], id=gr.id_sujeito,
                            indice_epoca=idx[ok], gravacao=np.repeat(gr.id_sujeito, int(ok.sum())),
                            taxa_origem_hz=gr.meta["taxa_origem_hz"],
                            epocas_sem_dado=gr.meta["epocas_sem_dado"])
        feitas += 1
        print(f"  {gr.id_sujeito}: {int(ok.sum())} épocas ({gr.meta['epocas_sem_dado']} sem dado, "
              f"{gr.meta['taxa_origem_hz']:.1f} Hz) -> {alvo.name}", file=sys.stderr)
    return feitas


def carregar_features_walch(cfg, incluir_baixa_taxa: bool):
    variante = _variante_walch(incluir_baixa_taxa)
    arquivos = sorted(PASTA_FEATURES_WALCH.glob(f"{cfg.hash}_{variante}_*.npz"))
    if not arquivos:
        raise FileNotFoundError(
            f"Nenhuma feature da Walch ({variante}) em {PASTA_FEATURES_WALCH}. "
            "Rode --coorte walch --preparar antes.")
    Xs, ys, ids, segmentos = [], [], [], []
    for caminho in arquivos:
        d = ler_features(caminho, cfg)
        Xs.append(d["X"])
        ys.append(d["y"].astype(int))
        ids.append(np.full(d["y"].shape[0], str(d["id"]), dtype=object))
        segmentos.append(np.char.add(caminho.name + ":", segmentos_de(d).astype(str)))
    return np.concatenate(Xs), np.concatenate(ys), np.concatenate(ids), np.concatenate(segmentos)


# =========================================================================
# Fase 2 — treinar no Wearanize+ inteiro, aplicar ao Newcastle a frio
# =========================================================================

def _base_wearanize(sujeitos, cfg):
    caminho = caminho_base(sujeitos, cfg, PASTA_CACHE)
    if not caminho.exists():
        raise FileNotFoundError(f'cache temporal {caminho.name} ausente; prepare com ml03b_otimizacoes')
    return ler_base(caminho, sujeitos, cfg)

def _trivial(y, ids, seed):
    """"Sempre dormindo" medido no próprio Newcastle. A única âncora que não
    atravessa coortes — e a linha que faz a tabela ser honesta."""
    return avaliar_por_sujeito(y, np.ones_like(y), ids, metricas=METRICAS, seed=seed)


def rodar(cfg, seed: int, punho: str, destino: Path, coorte: str = "newcastle",
          incluir_baixa_taxa: bool = False, *, dados_dreamt: Path | None = None) -> dict:
    sujeitos = sujeitos_com_posicoes(["cabeca", "pulso"], **({"pasta": DADOS_WEARANIZE} if DADOS_WEARANIZE else {}))
    base = _base_wearanize(sujeitos, cfg)

    # Os nomes `_ncl` ficam: o Newcastle foi a primeira coorte, e o caminho
    # dele não muda. Com `coorte="walch"` eles carregam a Walch.
    metricas = METRICAS
    extra = {}
    confusoes = {}
    if coorte == "dreamt":
        import hashlib
        from ferramentas.baixar_dreamt import CSV_ESPERADOS
        from src.carregar.dreamt import carregar_features_dreamt
        if dados_dreamt is None:
            raise ValueError("DREAMT exige caminho explícito")
        if {p.relative_to(dados_dreamt).as_posix() for p in
                (dados_dreamt / "data_64Hz").glob("*_whole_df.csv")} != CSV_ESPERADOS:
            raise ValueError("DREAMT exige os 100 CSVs da versão 2.2.0")
        manifesto = json.loads((RAIZ / 'experimentos/saida/ml17/manifesto.json').read_text(encoding='utf-8'))
        esperados = manifesto['execucoes']['depois/newcastle']['hash_entradas']
        hashes = {}
        for nome, b in base.items():
            h = hashlib.sha256(np.asarray(b['X'], dtype='<f8').tobytes())
            h.update(np.asarray(b['y'], dtype='<i8').tobytes())
            h.update(json.dumps(b['id'].tolist()).encode())
            hashes[nome] = h.hexdigest()
        if len(sujeitos) != 92 or set(hashes) != set(NOMES_BRACOS) or any(
                h != esperados[f'wearanize/{nome}']['sha256'] for nome, h in hashes.items()):
            raise ValueError("treino Wearanize diferente dos dados congelados na ML-17")
        dados, qualidade, exclusoes = carregar_features_dreamt(dados_dreamt, cfg)
        X_ncl_bruto, y_ncl, ids_ncl = dados["X"], dados["y"], dados["id"]
        seg_ncl = segmentos_de(dados)
        metricas = (*METRICAS, "f1_sono", "f1_vigilia")
        extra = {"qualidade": dict(qualidade, segmentos=int(seg_ncl[-1]) + 1),
                 "exclusoes_locais": exclusoes,
                 "sha256_manifesto_dreamt": hashlib.sha256((dados_dreamt / "SHA256SUMS.txt").read_bytes()).hexdigest(),
                 "sha256_treino": hashes}
    elif coorte == "walch":
        X_ncl_bruto, y_ncl, ids_ncl, seg_ncl = carregar_features_walch(cfg, incluir_baixa_taxa)
    else:
        X_ncl_bruto, y_ncl, ids_ncl, seg_ncl = carregar_features_newcastle(cfg, punho)
    # Normalização por sujeito: é função só de X, não usa rótulo nenhum, e é
    # por isso que pode ser aplicada ao domínio de teste sem vazamento — foi
    # a conclusão do item 5 da ablação, e é o que torna a transferência a
    # frio possível sem tocar no rótulo do Newcastle.
    X_ncl = normalizar_por_sujeito(X_ncl_bruto, ids_ncl)

    n_suj_ncl = len(set(ids_ncl.tolist()))
    print(f"{coorte}: {X_ncl.shape[0]} épocas · {n_suj_ncl} sujeitos · "
          f"prevalência de sono {y_ncl.mean():.3f}", file=sys.stderr)
    print(f"Wearanize+ (treino): {len(sujeitos)} sujeitos", file=sys.stderr)

    trivial = (_trivial(y_ncl, ids_ncl, seed) if coorte != "dreamt" else
               avaliar_por_sujeito(y_ncl, np.ones_like(y_ncl), ids_ncl, metricas=metricas, seed=seed))
    print(f"\n[âncora] trivial 'sempre dormindo' NA COORTE ({coorte}): "
          f"kappa={trivial.media['kappa']:.3f}  espec={trivial.media['especificidade']:.3f}  "
          f"acur={trivial.media['acuracia']:.3f}")

    resultado = {
        "experimento": (f"ML-04 -- validacao externa (treina Wearanize+, testa {coorte})"
                        if coorte != "newcastle" else
                        "ML-04 -- validacao externa (treina Wearanize+, testa Newcastle)"),
        "hash_config": cfg.hash, "seed": seed,
        "utc": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "treino": {"dataset": "wearanize", "n_sujeitos": len(sujeitos),
                   "reajuste_no_teste": "nenhum"},
        "teste": {"dataset": coorte,
                  **({"punho": punho} if coorte == "newcastle" else
                     {"variante": _variante_walch(incluir_baixa_taxa)} if coorte == "walch" else {}),
                  "n_sujeitos": n_suj_ncl,
                  "n_epocas": int(X_ncl.shape[0]),
                  "prevalencia_sono": float(y_ncl.mean())},
        f"trivial_no_{coorte}": trivial.dict(),
        "resultados": {},
        **extra,
    }
    if coorte == "dreamt":
        confusoes["trivial"] = avaliar_epoca(y_ncl, np.ones_like(y_ncl)).dict()

    for nome_braco in NOMES_BRACOS:
        Xw = normalizar_por_sujeito(base[nome_braco]["X"], base[nome_braco]["id"])
        yw = base[nome_braco]["y"]
        idw = base[nome_braco]["id"]
        resultado["resultados"][nome_braco] = {}
        print(f"\n=== treino: {nome_braco} -> teste: {coorte} ===")

        for nome_cfg, opcoes in CONFIGS.items():
            ctx = int(opcoes["contexto"])
            Xw_ctx = empilhar_contexto(Xw, ctx, segmentos=segmentos_de(base[nome_braco]))
            Xn_ctx = empilhar_contexto(X_ncl, ctx, segmentos=seg_ncl)

            clf = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=seed)
            clf.fit(Xw_ctx, yw)

            A = transicoes_hmm(yw, idw, segmentos=segmentos_de(base[nome_braco]))[0] if opcoes["hmm"] else None
            pred = _prever(clf, Xn_ctx, y_ncl, ids_ncl, opcoes["hmm"], A, segmentos=seg_ncl)

            m = avaliar_por_sujeito(y_ncl, pred, ids_ncl, metricas=metricas, seed=seed)
            resultado["resultados"][nome_braco][nome_cfg] = m.dict()
            if coorte == "dreamt":
                confusoes[f"{nome_braco}/{nome_cfg}"] = avaliar_epoca(y_ncl, pred).dict()

            d_kappa = m.media["kappa"] - trivial.media["kappa"]
            print(f"  {nome_cfg:<20} kappa={m.media['kappa']:.3f} "
                  f"[{m.ic95_baixo['kappa']:.3f}, {m.ic95_alto['kappa']:.3f}]  "
                  f"espec={m.media['especificidade']:.3f} "
                  f"[{m.ic95_baixo['especificidade']:.3f}, {m.ic95_alto['especificidade']:.3f}]  "
                  f"Δkappa vs. trivial={d_kappa:+.3f} "
                  f"({'acima do trivial' if m.ic95_baixo['kappa'] > trivial.media['kappa'] else 'IC inclui o trivial'})")

    if coorte == "dreamt":
        resultado["confusoes"] = confusoes
        texto = json.dumps(resultado, indent=2, ensure_ascii=False)
        with destino.open("x", encoding="utf-8") as f:
            f.write(texto)
    else:
        destino.write_text(json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nsalvo em {destino}")
    return resultado


def _prever(clf, X_ctx, y_alvo, ids, usa_hmm: bool, A, *, segmentos=None):
    if not usa_hmm:
        return clf.predict(X_ctx)
    segmentos = ids if segmentos is None else segmentos
    return aplicar_por_segmento(clf.predict_proba(X_ctx)[:, 1], segmentos,
                                lambda p: suavizar_hmm(p, A))

def lados(cfg, seed: int, destino: Path) -> dict:
    """Quanto o lado do corpo importa — com participante como unidade.

    Ver o cabeçalho de `experimentos/_lados.py` para por que isto não é um
    `--punho ambos` com n = 53.
    """
    from experimentos._lados import (
        alinhar_por_sujeito, bootstrap_agregado, bootstrap_pareado_intra_sujeito,
    )

    sujeitos = sujeitos_com_posicoes(["cabeca", "pulso"], **({"pasta": DADOS_WEARANIZE} if DADOS_WEARANIZE else {}))
    base = _base_wearanize(sujeitos, cfg)

    dados_lado = {}
    for lado in ("esquerdo", "direito"):
        Xb, yl, idl, segl = carregar_features_newcastle(cfg, lado)
        # Cada gravação é normalizada contra ela mesma. É o que um produto
        # real faz (não tem o outro punho à mão), e mantém os dois lados
        # independentes um do outro no pré-processamento.
        dados_lado[lado] = (normalizar_por_sujeito(Xb, idl), yl, idl, segl)
        print(f"{lado}: {Xb.shape[0]} épocas · {len(set(idl.tolist()))} participantes",
              file=sys.stderr)

    so_esq = sorted(set(dados_lado["esquerdo"][2].tolist())
                    - set(dados_lado["direito"][2].tolist()))
    print(f"sem punho direito: {so_esq or 'nenhum'}", file=sys.stderr)

    resultado = {
        "experimento": "ML-04b -- efeito do lado do corpo, participante como unidade",
        "hash_config": cfg.hash, "seed": seed,
        "utc": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "treino": {"dataset": "wearanize", "n_sujeitos": len(sujeitos),
                   "reajuste_no_teste": "nenhum"},
        "unidade_de_agrupamento": "participante",
        "censo": {
            "n_esquerdo": len(set(dados_lado["esquerdo"][2].tolist())),
            "n_direito": len(set(dados_lado["direito"][2].tolist())),
            "sem_punho_direito": so_esq,
        },
        "resultados": {},
    }

    for nome_braco in NOMES_BRACOS:
        Xw = normalizar_por_sujeito(base[nome_braco]["X"], base[nome_braco]["id"])
        yw, idw = base[nome_braco]["y"], base[nome_braco]["id"]
        resultado["resultados"][nome_braco] = {}
        print(f"\n=== treino: {nome_braco} ===")

        for nome_cfg, opcoes in CONFIGS.items():
            ctx = int(opcoes["contexto"])
            clf = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=seed)
            clf.fit(empilhar_contexto(Xw, ctx, segmentos=segmentos_de(base[nome_braco])), yw)
            A = transicoes_hmm(yw, idw, segmentos=segmentos_de(base[nome_braco]))[0] if opcoes["hmm"] else None

            metricas_lado = {}
            for lado, (Xl, yl, idl, segl) in dados_lado.items():
                pred = _prever(clf, empilhar_contexto(Xl, ctx, segmentos=segl), yl, idl, opcoes["hmm"], A, segmentos=segl)
                metricas_lado[lado] = avaliar_por_sujeito(
                    yl, pred, idl, metricas=METRICAS, seed=seed)

            entrada = {
                "a_esquerdo_isolado": metricas_lado["esquerdo"].dict(),
                "b_direito_isolado": metricas_lado["direito"].dict(),
                "c_efeito_do_lado_intra_sujeito": {},
                "d_INCORRETO_empilhado": {},
            }
            print(f"  {nome_cfg}:")
            for metrica in ("kappa", "especificidade"):
                par = bootstrap_pareado_intra_sujeito(
                    metricas_lado["esquerdo"], metricas_lado["direito"], metrica, seed=seed)
                entrada["c_efeito_do_lado_intra_sujeito"][metrica] = par

                # A versão errada: empilha as duas gravações de cada
                # participante como se fossem observações independentes.
                # Só serve para medir o estreitamento indevido do IC.
                ve, vd, _ = alinhar_por_sujeito(
                    metricas_lado["esquerdo"], metricas_lado["direito"], metrica)
                empilhado = bootstrap_agregado(np.concatenate([ve, vd]), seed=seed)
                entrada["d_INCORRETO_empilhado"][metrica] = empilhado

                print(f"    {metrica:<15} esq={par['media_a']:.3f}  dir={par['media_b']:.3f}  "
                      f"Δ(esq−dir)={par['delta_medio']:+.4f} "
                      f"IC95 [{par['ic95_baixo']:+.4f}, {par['ic95_alto']:+.4f}] "
                      f"n={par['n_participantes']} -> "
                      f"{'DIFERENÇA REAL' if par['significativo'] else 'IC inclui zero'}")
            resultado["resultados"][nome_braco][nome_cfg] = entrada

    destino.write_text(json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nsalvo em {destino.relative_to(RAIZ)}")
    return resultado


def comparar(destino: Path) -> None:
    """Confronta as configurações ENTRE SI na coorte externa, pareado.

    Aqui o pareamento é entre configurações rodadas sobre os MESMOS sujeitos
    do Newcastle, e é ainda mais necessário do que no LOSO: com 27 sujeitos
    os IC individuais são largos (±0,08 em kappa) e se sobrepõem quase
    sempre, de modo que comparar IC individuais não decidiria nada.
    """
    from experimentos.ml03b_otimizacoes import _bootstrap_pareado

    d = json.loads(destino.read_text(encoding="utf-8"))
    print(f"\n### comparação pareada entre configurações ({destino.name})")
    print(f"    teste: {d['teste']['dataset']} · n={d['teste']['n_sujeitos']} sujeitos\n")
    for braco, por_cfg in d["resultados"].items():
        print(f"  treino={braco}  (referência: base_ctx2)")
        ref = por_cfg["base_ctx2"]
        for nome_cfg, m in por_cfg.items():
            if nome_cfg == "base_ctx2":
                continue
            linha = [f"    {nome_cfg:<18}"]
            for metrica in ("kappa", "especificidade"):
                par = _bootstrap_pareado(ref, m, metrica)
                if par is None:
                    linha.append(f"{metrica}: (sem par)")
                    continue
                veredito = ("GANHO" if (par["significativo"] and par["melhora"])
                            else "PERDA" if par["significativo"] else "dentro do IC")
                linha.append(f"Δ{metrica[:5]}={par['delta_medio']:+.3f} "
                             f"[{par['ic95_baixo']:+.3f},{par['ic95_alto']:+.3f}] {veredito}")
            print("  ".join(linha))
        print()


def main() -> int:
    global DADOS_BRUTOS, DADOS_WEARANIZE, PASTA_CACHE, PASTA_FEATURES, PASTA_FEATURES_WALCH, PASTA_SAIDA
    ap = argparse.ArgumentParser()
    ap.add_argument("--comparar", action="store_true",
                    help="lê o .json já salvo e compara as configurações entre si, pareado")
    ap.add_argument("--lados", action="store_true",
                    help="efeito do lado do corpo, com PARTICIPANTE como unidade de "
                         "agrupamento (ver experimentos/_lados.py)")
    ap.add_argument("--preparar", action="store_true",
                    help="extrai features do Newcastle (retomável; repita até COMPLETO)")
    ap.add_argument("--rodar", action="store_true")
    ap.add_argument("--punho", choices=("esquerdo", "direito", "ambos"), default="esquerdo")
    ap.add_argument("--coorte", choices=("newcastle", "walch", "dreamt"), default="newcastle",
                    help="destino da validação externa")
    ap.add_argument("--incluir-baixa-taxa", action="store_true",
                    help="walch: inclui os 2 sujeitos de 10 Hz (análise secundária)")
    ap.add_argument("--orcamento-s", type=float, default=75.0)
    ap.add_argument("--exceto", nargs="*", default=[],
                    help="IDs a pular nesta passada (ex.: ncl034, cujo .bin de 282 MB "
                         "pica ~3,6 GB de RSS na decodificação e precisa de uma chamada só dele)")
    ap.add_argument("--so", nargs="*", default=[],
                    help="processa SOMENTE estes IDs")
    ap.add_argument('--dados-brutos', type=Path, help='raiz da coorte de destino, sem junction')
    ap.add_argument('--dados-wearanize', type=Path, help='raiz dos dados de treino')
    ap.add_argument('--cache', type=Path, default=PASTA_CACHE)
    ap.add_argument('--saida-dir', type=Path)
    args = ap.parse_args()
    if args.coorte == "dreamt":
        if args.dados_brutos is None:
            ap.error("dreamt exige --dados-brutos")
        if args.dados_wearanize is None or args.saida_dir is None:
            ap.error("dreamt exige --dados-wearanize e --saida-dir")
        if args.saida_dir.resolve().is_relative_to(RAIZ.resolve()):
            ap.error("dreamt exige --saida-dir fora do repositório")
        if args.preparar or args.lados or args.incluir_baixa_taxa or args.so or args.exceto:
            ap.error("dreamt avalia a coorte completa, sem seleção pela CLI")
    DADOS_BRUTOS, DADOS_WEARANIZE = args.dados_brutos, args.dados_wearanize
    PASTA_CACHE, PASTA_SAIDA = args.cache, args.saida_dir or PASTA_SAIDA
    PASTA_FEATURES = PASTA_CACHE / ('newcastle_features_' + VERSAO)
    PASTA_FEATURES_WALCH = PASTA_CACHE / ('walch_features_' + VERSAO)
    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)

    cfg = carregar_config()
    fixar_seed(cfg.seed)

    if args.coorte == "dreamt":
        from threadpoolctl import threadpool_limits
        destino = PASTA_SAIDA / f"ml04_validacao_externa_{cfg.hash}_dreamt.json"
        if not args.comparar:
            if destino.exists():
                ap.error("saída DREAMT já existe. Use outro --saida-dir ou --comparar")
            with threadpool_limits(limits=1):
                rodar(cfg, cfg.seed, args.punho, destino, coorte="dreamt",
                      dados_dreamt=args.dados_brutos)
        comparar(destino)
        return 0

    if args.coorte == "walch":
        if args.preparar:
            feitas = preparar_walch(cfg, args.incluir_baixa_taxa)
            print(f"\n+{feitas} sujeitos extraídos — COMPLETO")
            return 0
        destino = (PASTA_SAIDA / f"ml04_validacao_externa_{cfg.hash}_walch_"
                   f"{_variante_walch(args.incluir_baixa_taxa)}.json")
        if args.rodar:
            rodar(cfg, cfg.seed, args.punho, destino, coorte="walch",
                  incluir_baixa_taxa=args.incluir_baixa_taxa)
            comparar(destino)
            return 0
        if args.comparar:
            comparar(destino)
            return 0
        ap.error("com --coorte walch: --preparar, --rodar ou --comparar")

    if args.preparar:
        feitas, existentes, rejeitadas = preparar(
            cfg, args.orcamento_s, args.punho,
            exceto=tuple(args.exceto), so=tuple(args.so))
        prontos = len(list(PASTA_FEATURES.glob(f"{cfg.hash}_*.npz")))
        print(f"\n+{feitas} extraídas · +{rejeitadas} rejeitadas · "
              f"{prontos} gravações em cache")
        if feitas or rejeitadas:
            print("INCOMPLETO (ou pode ser o fim) — rode de novo; "
                  "quando disser '+0 extraídas · +0 rejeitadas', acabou.")
            return 2
        print("COMPLETO — nada novo a extrair.")
        return 0

    destino = (PASTA_SAIDA
               / f"ml04_validacao_externa_{cfg.hash}_{args.punho}.json")

    if args.rodar:
        rodar(cfg, cfg.seed, args.punho, destino)
        comparar(destino)
        return 0

    if args.comparar:
        comparar(destino)
        return 0

    if args.lados:
        lados(cfg, cfg.seed, PASTA_SAIDA
              / f"ml04b_efeito_do_lado_{cfg.hash}.json")
        return 0

    ap.error("escolha --preparar, --rodar, --comparar ou --lados")


if __name__ == "__main__":
    raise SystemExit(main())
