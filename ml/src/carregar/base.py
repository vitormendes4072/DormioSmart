"""Contrato que todo carregador de dataset cumpre.

O detalhe que decide se trocar de dataset custa um dia ou uma semana é a
**interface única**. Todo carregador devolve exatamente a mesma coisa, e
`carregar("newcastle")` / `carregar("walch")` / `carregar("wearanize")` são
intercambiáveis para tudo que vem depois.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

__all__ = ["Gravacao", "ConjuntoEpocas"]


@dataclass
class Gravacao:
    """Uma noite de um sujeito, ainda em sinal bruto."""

    id_sujeito: str
    t: np.ndarray                 # (n,) segundos, crescente
    a: np.ndarray                 # (n, 3) aceleração em **g**
    rotulos: np.ndarray           # (m,) 0 = vigília, 1 = sono; -1 = não pontuado
    t0_rotulo: float              # instante do início do primeiro rótulo, em `t`
    epoca_rotulo_s: float = 30.0
    #: Fração do sinal que foi interpolada (lacunas). Quem consome deve olhar:
    #: Walch et al. documentam <3% no dataset deles; acima disso, desconfiar.
    fracao_interpolada: float = 0.0
    meta: dict = field(default_factory=dict)


@dataclass
class ConjuntoEpocas:
    """Saída padrão do pipeline: o que os modelos consomem."""

    X: np.ndarray                 # (n_epocas, n_features)
    y: np.ndarray                 # (n_epocas,) 0 = vigília, 1 = sono
    id_sujeito: np.ndarray        # (n_epocas,) string — a chave do split
    nomes_features: tuple[str, ...]
    meta: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        n = self.X.shape[0]
        if not (self.y.shape[0] == n == self.id_sujeito.shape[0]):
            raise ValueError("X, y e id_sujeito com comprimentos diferentes")

    def __len__(self) -> int:
        return int(self.X.shape[0])
