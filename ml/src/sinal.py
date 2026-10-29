"""Reamostragem para a grade comum, com anti-aliasing.

O erro que este módulo existe para impedir
------------------------------------------
Reamostrar para baixo SEM filtrar antes dobra a energia de alta frequência de
volta para dentro da banda (aliasing), e isso NÃO é reversível. O sinal de
85,70 Hz do Newcastle precisa passar por um passa-baixa em < 16 Hz antes de ser
decimado para 32 Hz. É um erro que não aparece em teste funcional: ele só
aparece como uma feature ligeiramente errada em todas as épocas.

Por que não `scipy.signal.decimate`
-----------------------------------
Ela só aceita fator inteiro. 85,70 -> 32 não é inteiro. E o Apple Watch nem
sequer amostra em grade regular (Walch et al. documentam lacunas e taxa efetiva
variável). A abordagem aqui — filtrar em tempo contínuo e depois interpolar para
a grade nova — funciona para taxa arbitrária E para timestamps irregulares, que
é o caso geral das bases.
"""

from __future__ import annotations

import numpy as np
from scipy.signal import butter, filtfilt

__all__ = ["reamostrar", "taxa_efetiva", "passa_baixa"]


def taxa_efetiva(t: np.ndarray) -> float:
    """Taxa mediana observada, em Hz. Mediana e não média: robusta a lacunas."""
    if t.size < 2:
        raise ValueError("série curta demais para estimar taxa")
    dt = np.diff(t)
    dt = dt[dt > 0]
    if dt.size == 0:
        raise ValueError("timestamps não crescentes")
    return float(1.0 / np.median(dt))


def passa_baixa(x: np.ndarray, fs: float, corte_hz: float, ordem: int = 4) -> np.ndarray:
    """Butterworth de fase zero (filtfilt), aplicado por coluna.

    Fase zero importa: um filtro causal desloca o sinal no tempo, e o
    alinhamento com o rótulo de PSG é em época de 30 s. Deslocar meio segundo
    já move amostras para a época vizinha.
    """
    nyq = fs / 2.0
    if corte_hz >= nyq:
        # Nada a filtrar: a banda pedida já cabe. Devolve cópia, não o original.
        return np.asarray(x, dtype=float).copy()
    wn = corte_hz / nyq
    b, a = butter(ordem, wn, btype="low")
    x = np.asarray(x, dtype=float)
    # filtfilt exige comprimento > 3 * max(len(a), len(b)); guarda de borda.
    if x.shape[0] <= 3 * max(len(a), len(b)):
        return x.copy()
    return filtfilt(b, a, x, axis=0)


def reamostrar(
    t: np.ndarray,
    a: np.ndarray,
    taxa_destino: float,
    corte_frac_nyquist: float = 0.8,
) -> tuple[np.ndarray, np.ndarray]:
    """Leva (t, a) para uma grade uniforme em `taxa_destino`, com anti-aliasing.

    Parameters
    ----------
    t : (n,) segundos, crescente. Pode ter lacunas.
    a : (n, 3) aceleração em g.
    taxa_destino : Hz da grade comum (config: taxa_comum_hz).
    corte_frac_nyquist : corte do passa-baixa como fração da Nyquist do destino.

    Returns
    -------
    t_novo : (m,) grade uniforme
    a_novo : (m, 3)

    Notas
    -----
    - O filtro é aplicado ANTES da interpolação, na taxa de origem. Essa ordem
      é o ponto inteiro da função.
    - Se a taxa de origem já for <= a de destino, não há risco de aliasing e o
      sinal é só reinterpolado (sem filtrar) — filtrar aqui só destruiria banda
      útil.
    - Lacunas são interpoladas linearmente. Isso é uma decisão: a alternativa
      (propagar NaN) inviabiliza a feature da época inteira. Walch et al. fazem
      o mesmo no dataset deles (<3% do tempo). Quem carrega o dado deve
      REPORTAR a fração interpolada — ver `carregar/base.py`.
    """
    t = np.asarray(t, dtype=float)
    a = np.asarray(a, dtype=float)
    if a.ndim != 2 or a.shape[1] != 3:
        raise ValueError(f"esperado (n, 3), recebido {a.shape}")
    if t.shape[0] != a.shape[0]:
        raise ValueError("t e a com comprimentos diferentes")

    fs_origem = taxa_efetiva(t)
    nyq_destino = taxa_destino / 2.0
    corte = corte_frac_nyquist * nyq_destino

    if fs_origem > taxa_destino:
        a_filtrado = passa_baixa(a, fs_origem, corte)
    else:
        a_filtrado = a.copy()

    n = int(np.floor((t[-1] - t[0]) * taxa_destino)) + 1
    t_novo = t[0] + np.arange(n) / taxa_destino
    a_novo = np.empty((n, 3), dtype=float)
    for k in range(3):
        a_novo[:, k] = np.interp(t_novo, t, a_filtrado[:, k])
    return t_novo, a_novo
