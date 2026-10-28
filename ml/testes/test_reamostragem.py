"""Teste da reamostragem: o anti-aliasing está lá e funciona.

O erro que este teste pega
--------------------------
Decimar sem filtrar antes dobra energia de alta frequência para dentro da banda.
É irreversível e **não aparece em teste funcional** — o pipeline roda, as
features saem, e todas estão ligeiramente erradas.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.sinal import passa_baixa, reamostrar, taxa_efetiva

FS_ORIGEM = 85.70    # Newcastle (van Hees et al., 2015)
FS_DESTINO = 32.0    # grade comum do config


def _tom(f_hz: float, fs: float, dur_s: float = 60.0) -> tuple[np.ndarray, np.ndarray]:
    t = np.arange(int(fs * dur_s)) / fs
    x = np.sin(2 * np.pi * f_hz * t)
    a = np.stack([x, 0.3 * x, 1.0 + 0.1 * x], axis=1)
    return t, a


def test_taxa_efetiva_robusta_a_lacuna():
    """A taxa é a MEDIANA dos intervalos — lacuna não deve distorcer.

    Importa para o Walch: o Apple Watch não amostra continuamente.
    """
    t = np.arange(1000) / 50.0
    t = np.delete(t, slice(400, 450))     # lacuna de 1 s
    assert taxa_efetiva(t) == pytest.approx(50.0, rel=1e-6)


def test_banda_util_preservada():
    """Um tom DENTRO da banda sobrevive à reamostragem."""
    f = 3.0                               # movimento humano: 0,3–3,5 Hz
    t, a = _tom(f, FS_ORIGEM)
    t2, a2 = reamostrar(t, a, FS_DESTINO)
    assert taxa_efetiva(t2) == pytest.approx(FS_DESTINO, rel=1e-6)
    esp = np.abs(np.fft.rfft(a2[:, 0] - a2[:, 0].mean()))
    freqs = np.fft.rfftfreq(a2.shape[0], 1 / FS_DESTINO)
    assert freqs[int(np.argmax(esp))] == pytest.approx(f, abs=0.2)


def test_aliasing_e_suprimido():
    """O teste que importa.

    Um tom de 30 Hz, com grade destino de 32 Hz (Nyquist 16 Hz), rebateria para
    |30 − 32| = 2 Hz — **bem no meio da banda do movimento humano**, onde faria
    o maior estrago possível. Com anti-aliasing, ele tem de sumir.
    """
    f_alta = 30.0
    t, a = _tom(f_alta, FS_ORIGEM)
    _, a2 = reamostrar(t, a, FS_DESTINO)

    x = a2[:, 0] - a2[:, 0].mean()
    esp = np.abs(np.fft.rfft(x))
    freqs = np.fft.rfftfreq(x.shape[0], 1 / FS_DESTINO)
    perto_de_2hz = esp[(freqs > 1.0) & (freqs < 3.0)].max()

    # Referência: a amplitude que o mesmo tom teria SEM filtrar (decimação nua)
    passo = FS_ORIGEM / FS_DESTINO
    idx = np.clip((np.arange(x.shape[0]) * passo).astype(int), 0, a.shape[0] - 1)
    nu = a[idx, 0] - a[idx, 0].mean()
    esp_nu = np.abs(np.fft.rfft(nu))
    perto_de_2hz_nu = esp_nu[(freqs > 1.0) & (freqs < 3.0)].max()

    assert perto_de_2hz < 0.05 * perto_de_2hz_nu, (
        f"aliasing NÃO suprimido: energia rebatida {perto_de_2hz:.3g} vs "
        f"{perto_de_2hz_nu:.3g} sem filtro. O passa-baixa não está sendo aplicado."
    )


def test_nao_filtra_ao_subir_de_taxa():
    """Subindo de taxa não há aliasing; filtrar só destruiria banda útil."""
    t, a = _tom(5.0, 20.0)
    _, a2 = reamostrar(t, a, 32.0)
    x = a2[:, 0] - a2[:, 0].mean()
    freqs = np.fft.rfftfreq(x.shape[0], 1 / 32.0)
    pico = freqs[int(np.argmax(np.abs(np.fft.rfft(x))))]
    assert pico == pytest.approx(5.0, abs=0.3)


def test_passa_baixa_nao_desloca_fase():
    """filtfilt é de fase zero. Um filtro causal deslocaria o sinal no tempo — e
    o alinhamento com o rótulo de PSG é em época de 30 s: meio segundo de
    deslocamento já joga amostras para a época vizinha."""
    fs = 100.0
    t = np.arange(int(fs * 10)) / fs
    x = np.sin(2 * np.pi * 1.0 * t)[:, None] * np.ones((1, 3))
    y = passa_baixa(x, fs, corte_hz=10.0)
    i0 = int(np.argmax(x[: int(fs * 2), 0]))
    i1 = int(np.argmax(y[: int(fs * 2), 0]))
    assert abs(i0 - i1) <= 1, "o filtro deslocou o sinal: não é de fase zero"
