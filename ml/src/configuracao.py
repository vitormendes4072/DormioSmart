"""Leitura do config.yaml + hash, para versionar o resultado junto do config.

Regra do METODOLOGIA.md: config versionado junto com o resultado. O hash aqui é
o que amarra um número de métrica a um conjunto exato de parâmetros — inclusive
a seed.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import yaml

__all__ = ["Config", "carregar_config", "fixar_seed"]

CAMINHO_PADRAO = Path(__file__).resolve().parents[1] / "config.yaml"


@dataclass
class Config:
    seed: int
    taxa_comum_hz: float
    corte_antialiasing_frac_nyquist: float
    epoca_s: float
    contexto_epocas: int
    g_ms2: float
    classes: dict
    baseline: dict
    validacao: dict
    sintetico: dict
    versao_config: int
    hash: str
    bruto: dict = field(repr=False, default_factory=dict)


def carregar_config(caminho: Path | str = CAMINHO_PADRAO) -> Config:
    caminho = Path(caminho)
    texto = caminho.read_text(encoding="utf-8")
    d = yaml.safe_load(texto)
    h = hashlib.sha256(texto.encode("utf-8")).hexdigest()[:12]
    return Config(
        seed=int(d["seed"]),
        taxa_comum_hz=float(d["taxa_comum_hz"]),
        corte_antialiasing_frac_nyquist=float(d["corte_antialiasing_frac_nyquist"]),
        epoca_s=float(d["epoca_s"]),
        contexto_epocas=int(d["contexto_epocas"]),
        g_ms2=float(d["g_ms2"]),
        classes=d["classes"],
        baseline=d["baseline"],
        validacao=d["validacao"],
        sintetico=d["sintetico"],
        versao_config=int(d["versao_config"]),
        hash=h,
        bruto=d,
    )


def fixar_seed(seed: int) -> None:
    """Fixa TUDO que sorteia. Chamar no início de todo experimento."""
    random.seed(seed)
    np.random.seed(seed)
