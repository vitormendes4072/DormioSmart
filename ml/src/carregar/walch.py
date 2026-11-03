"""Carregador da coorte de Walch et al. (2019) — Apple Watch no pulso, PSG (ML-06).

Fonte
-----
Dados : PhysioNet, `sleep-accel` v1.0.0, Open Access, Open Data Commons
        Attribution License v1.0 — https://physionet.org/content/sleep-accel/1.0.0/
        DOI 10.13026/hmhs-py35 · zip de 576 850 847 bytes · 2,2 GB descompactados
        31 sujeitos · `motion/<id>_acceleration.txt` (tempo, x, y, z em g) e
        `labels/<id>_labeled_sleep.txt` (tempo, estágio), tempo em segundos
        desde o início da PSG.
Artigo : Walch, O.; Huang, Y.; Forger, D.; Goldstein, C. (2019). *Sleep stage
        prediction with raw acceleration and photoplethysmography heart rate
        data derived from a consumer wearable device.* Sleep 42(12), zsz180.
        DOI 10.1093/sleep/zsz180.

Tudo o que segue foi medido nos 31 arquivos em 2026-11-03, antes de escrever
este módulo (diário, 03/11 (viii)).

=============================================================================
ARMADILHA 1 — o movimento começa dias antes da PSG
=============================================================================
O arquivo de movimento traz o histórico do relógio: tempos NEGATIVOS, até
−533 391 s (seis dias) antes da PSG. Os rótulos começam em 0. Ler tudo e
reamostrar produziria uma grade de dias para usar oito horas — então o sinal é
recortado à janela dos rótulos, com `MARGEM_S` de folga, antes de qualquer
outra coisa.

=============================================================================
ARMADILHA 2 — o código 4 existe, e a página do PhysioNet não o define
=============================================================================
Contagem nos 31 sujeitos: −1: 438 · 0: 2 429 · 1: 1 821 · 2: 12 954 ·
3: 3 329 · **4: 356** · 5: 5 884. A página do dataset lista 0–3 e 5. O
repositório dos autores (`ojwalch/sleep_classifiers`, `source/sleep_stage.py`)
define 4 = N4 (pontuação de Rechtschaffen–Kales) e −1 = não pontuado. Daí
`ESTAGIOS_DE_SONO`: o 4 é sono. Tratá-lo como desconhecido descartaria 356
épocas de sono profundo, justamente as que mais se parecem com repouso.

=============================================================================
ARMADILHA 3 — tempo fora de ordem e repetido
=============================================================================
Em 11 dos 31 sujeitos há instantes não crescentes. `reamostrar` exige tempo
crescente; ordenar (estável) e descartar o instante repetido, ficando com a
primeira amostra, é o mínimo que não inventa nada.

=============================================================================
ARMADILHA 4 — a lacuna que a reamostragem esconde
=============================================================================
16 sujeitos têm lacunas acima de 1 s dentro da janela dos rótulos, até 1 277 s.
No `7749105` o movimento PARA aos 4 024 s da PSG e só volta depois do fim dela.

O perigo não está aqui, está depois: `reamostrar` interpola lacunas linearmente
(decisão documentada em `src/sinal.py`), e `fatiar_epocas` recebe uma grade
contínua — não tem mais como achar a lacuna. Sem tratamento, o `7749105`
entraria com ~7 h de sinal inventado, pareado com rótulo de PSG verdadeiro.

Por isso a lacuna é tratada AQUI, enquanto o tempo original ainda existe: toda
época que tenha lacuna maior que `LACUNA_MAXIMA_S`, ou que o movimento não
cubra inteira, tem o rótulo trocado para −1 (não pontuado), e sai do conjunto
em `processar_gravacoes`. A época fica sem verdade porque fica sem dado.

=============================================================================
ARMADILHA 5 — a taxa varia entre sujeitos, e dois estão a 10 Hz
=============================================================================
Mediana por sujeito: ~50 Hz em 24, ~66 Hz em 4, 33 Hz em 1 e **10 Hz em 2**
(`5383425` e `8258170`). A taxa comum do pipeline é 32 Hz; levar 10 Hz a 32 Hz
não cria o conteúdo de frequência que as features leem. `taxa_minima_hz`
deixa o chamador excluir esses sujeitos — a análise principal do ML-06 exclui,
a secundária inclui, e as duas são relatadas (adendo ao protocolo, diário
03/11 (viii)).
"""

from __future__ import annotations

import sys
from collections.abc import Iterable, Iterator
from pathlib import Path

import numpy as np

from .base import Gravacao

__all__ = [
    "carregar_walch", "ler_movimento", "ler_rotulos", "rotulos_binarios",
    "epocas_sem_dado", "PASTA_PADRAO",
]

PASTA_PADRAO = (Path(__file__).resolve().parents[2] / "dados" / "bruto" / "walch"
                / "motion-and-heart-rate-from-a-wrist-worn-wearable-and-labeled-sleep-from-"
                  "polysomnography-1.0.0")

EPOCA_S = 30.0
#: Folga do recorte em volta da janela dos rótulos (ARMADILHA 1).
MARGEM_S = 60.0
#: Lacuna acima disto dentro de uma época a deixa sem dado (ARMADILHA 4).
LACUNA_MAXIMA_S = 1.0
#: 0 = vigília; estes = sono (ARMADILHA 2). Todo o resto vira −1.
ESTAGIOS_DE_SONO = (1, 2, 3, 4, 5)


def ler_movimento(caminho: Path) -> tuple[np.ndarray, np.ndarray]:
    """(t, a): tempo em s desde a PSG, ordenado e sem repetição; a em g."""
    import pandas as pd

    d = pd.read_csv(caminho, sep=r"\s+", header=None, names=["t", "x", "y", "z"],
                    dtype=float).to_numpy()
    ordem = np.argsort(d[:, 0], kind="stable")       # ARMADILHA 3
    d = d[ordem]
    unicos = np.concatenate(([True], np.diff(d[:, 0]) > 0))
    d = d[unicos]
    return d[:, 0], d[:, 1:4]


def ler_rotulos(caminho: Path) -> tuple[float, np.ndarray]:
    """(t do primeiro rótulo, códigos). Exige passo de 30 s — senão é outro formato."""
    import pandas as pd

    d = pd.read_csv(caminho, sep=r"\s+", header=None, names=["t", "e"]).to_numpy()
    passos = np.diff(d[:, 0])
    if passos.size and not np.allclose(passos, EPOCA_S):
        raise ValueError(f"{caminho.name}: rótulos fora do passo de {EPOCA_S:g} s "
                         f"(passos vistos: {np.unique(passos)[:5]})")
    return float(d[0, 0]), d[:, 1].astype(int)


def rotulos_binarios(codigos: np.ndarray) -> np.ndarray:
    """0 → vigília (0); 1–5 → sono (1); qualquer outro → não pontuado (−1)."""
    codigos = np.asarray(codigos, dtype=int)
    y = np.full(codigos.shape, -1, dtype=int)
    y[codigos == 0] = 0
    y[np.isin(codigos, ESTAGIOS_DE_SONO)] = 1
    return y


def epocas_sem_dado(t: np.ndarray, t0: float, n: int, epoca_s: float = EPOCA_S,
                    lacuna_max_s: float = LACUNA_MAXIMA_S) -> np.ndarray:
    """Máscara (n,): True onde a época não tem dado medido (ARMADILHA 4).

    Sem dado = alguma lacuna maior que `lacuna_max_s` entre o início e o fim da
    época, ou o movimento não chegar perto o bastante de uma das pontas.
    """
    sem = np.zeros(n, dtype=bool)
    for k in range(n):
        ini, fim = t0 + k * epoca_s, t0 + (k + 1) * epoca_s
        i0 = int(np.searchsorted(t, ini, side="left"))
        i1 = int(np.searchsorted(t, fim, side="right"))
        trecho = t[i0:i1]
        if trecho.size < 2:
            sem[k] = True
            continue
        bordas = np.concatenate(([ini], trecho, [fim]))
        if np.max(np.diff(bordas)) > lacuna_max_s:
            sem[k] = True
    return sem


def carregar_walch(
    pasta: Path | str = PASTA_PADRAO,
    taxa_minima_hz: float | None = None,
    sujeitos: Iterable[str] | None = None,
) -> Iterator[Gravacao]:
    """Uma `Gravacao` por sujeito, já recortada e com as épocas sem dado em −1.

    `taxa_minima_hz` exclui (com aviso) os sujeitos de taxa mediana abaixo
    dela — ARMADILHA 5. `sujeitos` restringe aos IDs dados.
    """
    from ..sinal import taxa_efetiva

    pasta = Path(pasta)
    rotulos = sorted((pasta / "labels").glob("*_labeled_sleep.txt"))
    if not rotulos:
        raise FileNotFoundError(
            f"Nenhum rótulo em {pasta / 'labels'}.\n"
            "Baixe o sleep-accel 1.0.0 (Open Access, 577 MB):\n"
            "  https://physionet.org/content/sleep-accel/1.0.0/\n"
            "e descompacte em ml/dados/bruto/walch/ (mantém a pasta do pacote)."
        )
    filtro = set(sujeitos) if sujeitos is not None else None

    for caminho_rot in rotulos:
        sid = caminho_rot.name.split("_")[0]
        if filtro is not None and sid not in filtro:
            continue
        t0, codigos = ler_rotulos(caminho_rot)
        t, a = ler_movimento(pasta / "motion" / f"{sid}_acceleration.txt")

        fim_rotulos = t0 + codigos.shape[0] * EPOCA_S
        janela = (t >= t0 - MARGEM_S) & (t <= fim_rotulos + MARGEM_S)   # ARMADILHA 1
        t, a = t[janela], a[janela]
        if t.shape[0] < 2:
            print(f"[walch] pulando {sid}: sem movimento na janela dos rótulos",
                  file=sys.stderr)
            continue

        fs = taxa_efetiva(t)
        if taxa_minima_hz is not None and fs < taxa_minima_hz:
            print(f"[walch] excluindo {sid}: taxa mediana {fs:.1f} Hz < "
                  f"{taxa_minima_hz:g} Hz (ARMADILHA 5)", file=sys.stderr)
            continue

        y = rotulos_binarios(codigos)
        sem = epocas_sem_dado(t, t0, codigos.shape[0])
        y[sem] = -1                                                     # ARMADILHA 4

        yield Gravacao(
            id_sujeito=sid,
            t=t,
            a=a,
            rotulos=y,
            t0_rotulo=t0,
            epoca_rotulo_s=EPOCA_S,
            # Aqui é a fração de épocas SEM DADO, que saem do conjunto — não a
            # de sinal interpolado que entra. Lacunas de até 1 s dentro de uma
            # época que fica são interpoladas por `reamostrar`, como sempre.
            fracao_interpolada=float(sem.mean()),
            meta={
                "fonte": "walch2019",
                "taxa_origem_hz": fs,
                "epocas_sem_dado": int(sem.sum()),
                "epocas_rotuladas": int(codigos.shape[0]),
                "codigos": {int(c): int((codigos == c).sum()) for c in np.unique(codigos)},
            },
        )
