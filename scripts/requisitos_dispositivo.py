#!/usr/bin/env python3
"""Números dos requisitos do dispositivo (`docs/REQUISITOS-DISPOSITIVO.md`, REQ-01).

    python3 scripts/requisitos_dispositivo.py            # imprime os números
    python3 scripts/requisitos_dispositivo.py --conferir # só as asserções; sai != 0 se divergir

Não cria modelo novo: deriva os números dos requisitos do modelo de energia já
conferido (`estudo_cadencia.py`, que importa `calculos_tcc.py`) e do próprio
firmware (`firmware/partitions.csv`, `firmware/nucleo/fila_flash.h`). Se o
firmware ou o modelo mudarem, o `--conferir` daqui reprova junto.

Nada aqui foi medido na placa. As correntes são especificação de fabricante,
e as que não puderam ser conferidas entram em faixa (ver `estudo_cadencia.py`).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from estudo_cadencia import (  # noqa: E402
    EPOCA_S,
    INTERVALO_DE_ENVIO_S,
    NAO_CONFERIDO_I_RF_A,
    NAO_CONFERIDO_T_ENVIO_S,
    PLACAS_A,
    V_ALIM_REF_V,
    c2_impl,
    varredura_c2_impl,
)

RAIZ = Path(__file__).resolve().parent.parent

# ── Uso ────────────────────────────────────────────────────────────────────
# Decisão de projeto PROPOSTA no REQ-01, a confirmar com o orientador: o
# dispositivo fica ligado o tempo todo (não há botão de liga/desliga no
# projeto) e deve passar uma semana sem recarga.
DIAS_SEM_RECARGA = 7
HORAS_SEM_RECARGA = DIAS_SEM_RECARGA * 24.0
NOITE_H = 8.0


def capacidade_necessaria_mah(i_media_a: float, horas: float = HORAS_SEM_RECARGA) -> float:
    """Capacidade (mAh) que sustenta `horas` a `i_media_a`, pela Equação 2."""
    return i_media_a * 1e3 * horas


def potencia_media_w(i_media_a: float) -> float:
    return V_ALIM_REF_V * i_media_a


def epocas_por_noite(horas: float = NOITE_H) -> int:
    return int(round(horas * 3600.0 / EPOCA_S))


def epocas_por_lote() -> int:
    return int(round(INTERVALO_DE_ENVIO_S / EPOCA_S))


# ── Armazenamento sem rede, lido do firmware ──────────────────────────────

def _tamanho_da_particao_dormio() -> int:
    for linha in (RAIZ / "firmware/partitions.csv").read_text(encoding="utf-8").splitlines():
        campos = [c.strip() for c in linha.split(",")]
        if campos and campos[0] == "dormio":
            return int(campos[4], 16)
    raise SystemExit("partição `dormio` não encontrada em firmware/partitions.csv")


def _constante_da_fila(nome: str) -> int:
    texto = (RAIZ / "firmware/nucleo/fila_flash.h").read_text(encoding="utf-8")
    m = re.search(rf"const uint32_t {nome} = (\d+);", texto)
    if not m:
        raise SystemExit(f"{nome} não encontrado em firmware/nucleo/fila_flash.h")
    return int(m.group(1))


def registros_utilizaveis() -> int:
    """Um setor fica sempre livre para o log circular girar (`fila_flash.h`)."""
    setor = _constante_da_fila("TAMANHO_DO_SETOR_BYTES")
    registro = 64
    setores = _tamanho_da_particao_dormio() // setor
    return (setores - 1) * (setor // registro)


def horas_sem_rede() -> float:
    return registros_utilizaveis() * EPOCA_S / 3600.0


# ── Relatório ──────────────────────────────────────────────────────────────

def relatorio() -> None:
    ref = c2_impl()
    lo, hi = varredura_c2_impl()
    print(f"Corrente média da C2 implementada: {ref * 1e3:.2f} mA "
          f"(varredura {lo * 1e3:.2f}–{hi * 1e3:.2f} mA)")
    print(f"\nAutonomia exigida: {DIAS_SEM_RECARGA} dias ligado = {HORAS_SEM_RECARGA:.0f} h")
    print("Capacidade necessária (mAh), por consumo fixo da placa:")
    print("  placa  | referência | pior caso da varredura")
    for p in PLACAS_A:
        print(f"  {p * 1e3:4.0f} mA | {capacidade_necessaria_mah(ref + p):10.0f} | "
              f"{capacidade_necessaria_mah(hi + p):10.0f}")
    print(f"\nPotência média: {potencia_media_w(ref) * 1e3:.1f} mW "
          f"(pior caso + placa de 10 mA: {potencia_media_w(hi + 10e-3) * 1e3:.1f} mW)")
    print(f"Pico do rádio: {potencia_media_w(NAO_CONFERIDO_I_RF_A[1]):.2f} W, "
          f"por {NAO_CONFERIDO_T_ENVIO_S[0]:.0f} a {NAO_CONFERIDO_T_ENVIO_S[2]:.0f} s "
          f"a cada {INTERVALO_DE_ENVIO_S / 60:.0f} min")
    print(f"\nÉpocas por noite de {NOITE_H:.0f} h: {epocas_por_noite()}; por lote: {epocas_por_lote()}")
    print(f"Fila na flash: {registros_utilizaveis()} registros = {horas_sem_rede():.1f} h "
          f"({horas_sem_rede() / 24:.1f} dias) sem rede")


# ── Asserções — travam os números de docs/REQUISITOS-DISPOSITIVO.md ────────

def conferir() -> int:
    falhas: list[str] = []
    conferidos = 0

    def eq(rotulo: str, obtido: float, esperado: float, tol: float) -> None:
        nonlocal conferidos
        conferidos += 1
        if abs(obtido - esperado) > tol:
            falhas.append(f"{rotulo}: obtido {obtido!r}, documento diz {esperado!r}")

    ref = c2_impl()
    lo, hi = varredura_c2_impl()
    eq("corrente de referência (mA)", ref * 1e3, 2.28, 0.005)
    eq("varredura, mínimo (mA)", lo * 1e3, 1.88, 0.005)
    eq("varredura, máximo (mA)", hi * 1e3, 5.19, 0.005)

    eq("horas sem recarga", HORAS_SEM_RECARGA, 168.0, 0)
    eq("capacidade, referência, sem placa (mAh)", capacidade_necessaria_mah(ref), 383, 0.5)
    eq("capacidade, referência, placa 10 mA (mAh)", capacidade_necessaria_mah(ref + 10e-3), 2063, 0.5)
    eq("capacidade, pior caso, sem placa (mAh)", capacidade_necessaria_mah(hi), 872, 0.5)
    eq("capacidade, pior caso, placa 10 mA (mAh)", capacidade_necessaria_mah(hi + 10e-3), 2552, 0.5)
    # A tabela inteira do RD-10, linha a linha.
    tabela = {0e-3: (383, 872), 1e-3: (551, 1040), 5e-3: (1223, 1712), 10e-3: (2063, 2552)}
    eq("linhas da tabela = consumos de placa do modelo", len(tabela), len(PLACAS_A), 0)
    for p in PLACAS_A:
        r, w = tabela[p]
        eq(f"tabela, placa {p * 1e3:.0f} mA, referência", capacidade_necessaria_mah(ref + p), r, 0.5)
        eq(f"tabela, placa {p * 1e3:.0f} mA, pior caso", capacidade_necessaria_mah(hi + p), w, 0.5)
    eq("pico do rádio, mínimo da faixa (W)", potencia_media_w(NAO_CONFERIDO_I_RF_A[0]), 0.33, 0.005)

    eq("potência média, referência (mW)", potencia_media_w(ref) * 1e3, 7.5, 0.05)
    eq("potência média, pior caso + placa 10 mA (mW)", potencia_media_w(hi + 10e-3) * 1e3, 50.1, 0.05)
    eq("pico do rádio, máximo da faixa (W)", potencia_media_w(NAO_CONFERIDO_I_RF_A[1]), 0.79, 0.005)
    eq("faixa da corrente do rádio (mA)", NAO_CONFERIDO_I_RF_A[0] * 1e3, 100, 0)

    eq("épocas por noite", epocas_por_noite(), 960, 0)
    eq("épocas por lote", epocas_por_lote(), 20, 0)
    eq("registros utilizáveis na flash", registros_utilizaveis(), 32704, 0)
    eq("horas sem rede", horas_sem_rede(), 272.5, 0.05)

    if falhas:
        print("REPROVADO:")
        for f in falhas:
            print("  -", f)
        return 1
    print(f"OK — {conferidos} números dos requisitos conferidos contra o modelo e o firmware.")
    return 0


def main() -> int:
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--conferir", action="store_true", help="só as asserções")
    args = ap.parse_args()
    if args.conferir:
        return conferir()
    relatorio()
    return conferir()


if __name__ == "__main__":
    raise SystemExit(main())
