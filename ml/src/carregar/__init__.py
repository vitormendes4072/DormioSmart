"""Interface única de carregamento.

    X, y, id_sujeito = carregar("newcastle")
    X, y, id_sujeito = carregar("wearanize", posicao="pulso")

Todo carregador devolve a mesma coisa, e trocar de dataset vira trocar uma
string. É o detalhe que decide se a Fase 2 custa um dia ou uma semana.

O `ML-03` — treinar numa posição de sensor e testar em outra — é o motivo de
`carregar()` aceitar `**opcoes`: o Wearanize+ é o único dataset com mais de uma
posição, e a posição é parâmetro dele, não um dataset separado. Datasets de uma
posição só ignoram o argumento (e levantam erro se algo for passado por engano).
"""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np

from ..configuracao import Config, carregar_config
from ..epocas import empilhar_contexto, fatiar_epocas
from ..features import NOMES_FEATURES, features_de_epoca
from ..sinal import reamostrar
from .base import ConjuntoEpocas, Gravacao

__all__ = ["carregar", "processar_gravacoes", "DATASETS", "POSICOES_WEARANIZE"]

DATASETS = ("newcastle", "sintetico", "wearanize")

#: Posições de sensor do Wearanize+. Só este dataset aceita `posicao=`.
POSICOES_WEARANIZE = ("cabeca", "pulso", "coxa")


def processar_gravacoes(gravacoes: Iterable[Gravacao], cfg: Config) -> ConjuntoEpocas:
    """Bruto -> épocas de 30 s -> 8 features -> contexto ±N. O caminho inteiro.

    `gravacoes` é consumido uma vez, em ordem — pode ser um generator. Isso
    importa para o Newcastle: `carregar_newcastle()` produz uma gravação por
    vez para não ter as 55 (4,6 GB brutos) na memória simultaneamente (ver
    ARMADILHA 4 em `src/carregar/newcastle.py`). Por isso `n_gravacoes` é
    contado no laço, não com `len()`.
    """
    Xs, ys, ids = [], [], []
    descartadas = 0
    n_gravacoes = 0

    for gr in gravacoes:
        n_gravacoes += 1
        t, a = reamostrar(
            gr.t, gr.a,
            taxa_destino=cfg.taxa_comum_hz,
            corte_frac_nyquist=cfg.corte_antialiasing_frac_nyquist,
        )
        a_ep, idx = fatiar_epocas(
            t, a,
            t0_rotulo=gr.t0_rotulo,
            n_rotulos=int(gr.rotulos.shape[0]),
            epoca_s=cfg.epoca_s,
            fs=cfg.taxa_comum_hz,
        )
        if a_ep.shape[0] == 0:
            continue
        descartadas += int(gr.rotulos.shape[0]) - a_ep.shape[0]

        X, _ = features_de_epoca(a_ep, fs=cfg.taxa_comum_hz)
        y = gr.rotulos[idx]

        # Épocas não pontuadas (-1) saem: não há verdade para comparar.
        ok = y >= 0
        X, y = X[ok], y[ok]
        if X.shape[0] == 0:
            continue

        X = empilhar_contexto(X, cfg.contexto_epocas)
        Xs.append(X)
        ys.append(y)
        ids.append(np.full(X.shape[0], gr.id_sujeito, dtype=object))

    if not Xs:
        raise ValueError("nenhuma época válida — verifique o alinhamento dos rótulos")

    nomes: list[str] = []
    for d in range(-cfg.contexto_epocas, cfg.contexto_epocas + 1):
        suf = "" if d == 0 else f"__{d:+d}"
        nomes.extend(f"{n}{suf}" for n in NOMES_FEATURES)

    return ConjuntoEpocas(
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


def carregar(nome: str, cfg: Config | None = None, **opcoes) -> ConjuntoEpocas:
    """`carregar("newcastle")`, `carregar("sintetico")`, `carregar("wearanize", ...)`.

    Opções aceitas por dataset
    --------------------------
    wearanize :
        posicao   : "cabeca" (padrão) | "pulso" | "coxa"
        pontuador : 1 (padrão) ou 2 — a segunda pontuação manual existe em 96
                    dos 100 sujeitos; comparar as duas dá o teto inter-avaliador
        sujeitos  : lista de IDs, para fixar o mesmo N entre células da matriz
                    do ML-03 (ver `carregar.wearanize.sujeitos_com_posicoes`)
    newcastle, sintetico :
        nenhuma — passar `posicao=` aqui é erro, e é sinalizado como tal em vez
        de ser ignorado em silêncio.

    Exemplo — a célula que é o resultado original do trabalho::

        from src.carregar.wearanize import sujeitos_com_posicoes
        comuns = sujeitos_com_posicoes(["pulso", "cabeca"])   # N = 92
        treino = carregar("wearanize", posicao="pulso",  sujeitos=comuns)
        teste  = carregar("wearanize", posicao="cabeca", sujeitos=comuns)
    """
    cfg = cfg or carregar_config()
    nome = nome.lower().strip()

    if nome == "newcastle":
        if opcoes:
            raise TypeError(
                f"carregar('newcastle') não aceita {sorted(opcoes)}. "
                "O Newcastle tem só uma posição (punho)."
            )
        from .newcastle import carregar_newcastle
        gravacoes = carregar_newcastle()
    elif nome == "wearanize":
        from .wearanize import carregar_wearanize
        desconhecidas = set(opcoes) - {"posicao", "pontuador", "sujeitos", "pasta"}
        if desconhecidas:
            raise TypeError(f"opções desconhecidas para 'wearanize': {sorted(desconhecidas)}")
        gravacoes = carregar_wearanize(
            posicao=opcoes.get("posicao", "cabeca"),
            pontuador=int(opcoes.get("pontuador", 1)),
            sujeitos=opcoes.get("sujeitos"),
            **({"pasta": opcoes["pasta"]} if "pasta" in opcoes else {}),
        )
    elif nome == "sintetico":
        if opcoes:
            raise TypeError(f"carregar('sintetico') não aceita {sorted(opcoes)}.")
        from .sintetico import gerar_sinteticos
        s = cfg.sintetico
        gravacoes = gerar_sinteticos(
            n_sujeitos=int(s["n_sujeitos"]),
            horas_por_noite=float(s["horas_por_noite"]),
            taxa_origem_hz=float(s["taxa_origem_hz"]),
            fracao_sono=float(s["fracao_sono"]),
            fracao_vigilia_quieta=float(s["fracao_vigilia_quieta"]),
            ruido_mg=float(s["ruido_mg"]),
            epoca_s=cfg.epoca_s,
            seed=cfg.seed,
        )
    else:
        raise ValueError(f"dataset desconhecido: {nome!r}. Disponíveis: {DATASETS}")

    conj = processar_gravacoes(gravacoes, cfg)
    conj.meta["dataset"] = nome
    # A posição vai para o meta porque o ML-03 compara conjuntos que só diferem
    # nisso: um resultado sem a posição registrada é um resultado sem sentido.
    if nome == "wearanize":
        conj.meta["posicao"] = opcoes.get("posicao", "cabeca")
        conj.meta["pontuador"] = int(opcoes.get("pontuador", 1))
    return conj
