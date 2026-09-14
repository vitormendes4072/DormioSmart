"""Interface única de carregamento.

    X, y, id_sujeito = carregar("newcastle")

Todo carregador devolve a mesma coisa, e trocar de dataset vira trocar uma
string. É o detalhe que decide se a Fase 2 custa um dia ou uma semana.
"""

from __future__ import annotations

import numpy as np

from ..configuracao import Config, carregar_config
from ..epocas import empilhar_contexto, fatiar_epocas
from ..features import NOMES_FEATURES, features_de_epoca
from ..sinal import reamostrar
from .base import ConjuntoEpocas, Gravacao

__all__ = ["carregar", "processar_gravacoes", "DATASETS"]

DATASETS = ("newcastle", "sintetico")


def processar_gravacoes(gravacoes: list[Gravacao], cfg: Config) -> ConjuntoEpocas:
    """Bruto -> épocas de 30 s -> 8 features -> contexto ±N. O caminho inteiro."""
    Xs, ys, ids = [], [], []
    descartadas = 0

    for gr in gravacoes:
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
            "n_gravacoes": len(gravacoes),
            "epocas_descartadas_sem_cobertura": descartadas,
            "hash_config": cfg.hash,
        },
    )


def carregar(nome: str, cfg: Config | None = None) -> ConjuntoEpocas:
    """`carregar("newcastle")` ou `carregar("sintetico")`."""
    cfg = cfg or carregar_config()
    nome = nome.lower().strip()

    if nome == "newcastle":
        from .newcastle import carregar_newcastle
        gravacoes = carregar_newcastle()
    elif nome == "sintetico":
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
    return conj
