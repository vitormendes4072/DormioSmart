#!/usr/bin/env python3
"""Reproduz os números de `docs/DECISAO-ARQ-01-CADENCIA.md` (ARQ-01, partes a e b).

    python3 scripts/estudo_cadencia.py            # imprime o estudo inteiro
    python3 scripts/estudo_cadencia.py --conferir # só as asserções; sai != 0 se divergir

Mesma convenção de `scripts/calculos_tcc.py` e `scripts/estudo_buffer.py`: só
biblioteca padrão, e cada constante traz fonte e condição. As constantes que
já estão em `calculos_tcc.py` são IMPORTADAS de lá, não copiadas — se o Z.4
mudar, este estudo muda junto, e o `--conferir` daqui reprova se as duas
arquiteturas de referência deixarem de dar 23,9 mA e 1,91 mA.

Onde o valor não pôde ser conferido na fonte primária, a constante está
marcada `NAO_CONFERIDO` e entra como **parâmetro em faixa**, com a faixa
varrida — nunca como número citado.

Nada aqui foi medido na placa. É a parte (c) do ARQ-01, e é ela que fecha o
item.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from calculos_tcc import (  # noqa: E402
    ESP32_I_LIGHT_SLEEP_A,
    ESP32_I_MODEM_SLEEP_80MHZ_A,
    EPOCA_S,
    GRADE_COMUM_HZ,
    MPU_I_ACEL_BAIXO_CONSUMO_A,
    MPU_I_ACEL_SO_A,
    MPU_I_VLOGIC_A,
    NAO_CONFERIDO_I_RF_A,
    autonomia_h,
    cenario_continuo,
    cenario_wom,
    corrente_media_a,
    corrente_pullup_linha_baixa_a,
)

# ══════════════════════════════════════════════════════════════════════════
# CONSTANTES — cada uma com fonte
# ══════════════════════════════════════════════════════════════════════════

# --- MPU-6050: FIFO e relógio ----------------------------------------------
# TDK InvenSense, *MPU-6000/MPU-6050 Product Specification*, PS-MPU-6000A-00
# Rev. 3.2 (16/11/2011), §4 ("An on-chip 1024 Byte FIFO buffer…") e §5.1
# ("1024 byte FIFO buffer reduces power consumption by allowing host
# processor to read the data in bursts and then go into a low-power mode").
# ⚠️ Lida na Rev. 3.2; o `calculos_tcc.py` cita a Rev. 3.4. As duas revisões
# não divergem nos números que o projeto usa, mas a 3.4 não foi relida aqui.
MPU_FIFO_B = 1024
# Só acelerômetro na FIFO: 3 eixos × 16 bits.
BYTES_POR_AMOSTRA_ACEL = 6

# Mesma folha, §6.6, INTERNAL CLOCK SOURCE (CLK_SEL = 0..3):
# "Accelerometer Sample Rate 1 kHz". Com relógio externo de 32,768 kHz
# (CLK_SEL = 4): 1,024 kHz.
MPU_TAXA_ACEL_INTERNA_HZ = 1000.0
MPU_TAXA_ACEL_CLK_32K_HZ = 1024.0

# Mesma folha, §6.6, "Clock Frequency Initial Tolerance": CLK_SEL = 0 (o
# oscilador interno, o único disponível com o giroscópio desligado), 25 °C:
# −5 % a +5 %. "Frequency Variation over Temperature", CLK_SEL = 0: −15 % a
# +10 %. Com o giroscópio como referência (CLK_SEL = 1..3) cai para ±1 % —
# mas o giroscópio ligado custa 3,8 mA (§6.4), 7,6× o acelerômetro sozinho.
MPU_TOL_OSC_INTERNO_25C = (-0.05, 0.05)
MPU_TOL_OSC_INTERNO_TEMP = (-0.15, 0.10)

# ⚠️ NAO_CONFERIDO na fonte primária: a fórmula da taxa (registrador 25,
# SMPLRT_DIV) — "Sample Rate = Gyroscope Output Rate / (1 + SMPLRT_DIV)", com
# o acelerômetro limitado à taxa de 1 kHz acima — vem do *Register Map*
# RM-MPU-6000A-00 Rev. 4.2, lido só em cópia de terceiros (o PDF da TDK não
# baixou nesta sessão). É a fórmula que todas as bibliotecas usam; entra como
# dado porque o resultado que dela depende (não há 32 Hz exato) é robusto: ver
# `taxas_mpu`.
SMPLRT_DIV_MAX = 255

# ⚠️ NAO_CONFERIDO: se a FIFO e o DLPF funcionam no modo de baixo consumo
# (CYCLE = 1, LP_WAKE_CTRL). A folha de produto só dá as correntes desse modo
# (1,25/5/20/40 Hz, importadas de `calculos_tcc.py`); o comportamento da FIFO
# nele está no Register Map, que não foi conferido. Por isso a variante C-LP
# abaixo é CONDICIONAL.

# Degraus do DLPF do acelerômetro (Register Map, registrador 26, DLPF_CFG),
# os dois que importam aqui. 21 Hz é o do `FW-06` (MPU6050_BAND_21_HZ); 10 Hz
# é o degrau seguinte. Mesmo caveat de fonte da fórmula acima.
DLPF_21_HZ = 21.0
DLPF_10_HZ = 10.0

# --- ml/ --------------------------------------------------------------------
# `ml/config.yaml` e `ml/src/sinal.py::reamostrar`: corte = 0,8 × Nyquist do
# destino, Butterworth de 4ª ordem de fase zero, aplicado NA TAXA DE ORIGEM e
# só depois interpolado para a grade. `taxa_efetiva()` estima a taxa real a
# partir dos carimbos de tempo — o `ml/` já não supõe taxa exata da fonte.
CORTE_FRAC_NYQUIST = 0.8
CORTE_ML_HZ = CORTE_FRAC_NYQUIST * GRADE_COMUM_HZ / 2.0     # 12,8 Hz

# --- ESP32: sono leve -------------------------------------------------------
# ESP-IDF v6.1, *Sleep Modes — ESP32*: "Upon exit from Light-sleep, the
# digital peripherals, RAM, and CPUs resume operation and their internal
# states are preserved" — o acumulador de 18,8 KiB sobrevive, ao contrário
# do Deep Sleep. E: "Wi-Fi and Bluetooth connections are not maintained in
# Deep-sleep or Light-sleep mode" — cada POST paga a reassociação.
# A corrente (0,8 mA) é a da Tabela 4-2, importada de `calculos_tcc.py`.

# ⚠️ NAO_CONFERIDO: latência de saída do sono leve. A página do ESP-IDF diz
# só que "wakeup from light sleep takes some time"; guias de terceiros dão
# 1–3 ms, e há relato de perda de dado a ~90 µs do despertar. Faixa varrida.
NAO_CONFERIDO_T_DESPERTAR_S = (0.2e-3, 1e-3, 3e-3)

# ⚠️ NAO_CONFERIDO: custo de CPU por amostra (filtro, acumulador). O
# `DATA-07b` estimou ~29 000 MACs em `double` POR ÉPOCA no fechamento; por
# amostra é bem menos. Faixa larga, de propósito.
NAO_CONFERIDO_T_PROC_AMOSTRA_S = (10e-6, 50e-6, 200e-6)

# I²C: o `envio-continuo.ino` chama `Wire.begin(21, 22)` sem `setClock` —
# 100 kHz, o padrão do arduino-esp32. 400 kHz é o modo rápido que o MPU
# aceita (folha §6.6, "400kHz Fast Mode I2C"). 9 bits por byte (8 + ACK).
I2C_HZ = (100e3, 400e3)
BITS_POR_BYTE_I2C = 9
# Por despertar: endereço + registrador + leitura de FIFO_COUNT (2 B) +
# endereço do burst. Arredondado para cima.
BYTES_OVERHEAD_I2C = 8

# Pull-ups de 4,7 kΩ, metade do tempo em nível baixo, nas duas linhas — a
# mesma premissa do `calculos_tcc.py` (CALC-04). Só durante o tráfego.
I_PULLUP_TRAFEGO_A = 2 * corrente_pullup_linha_baixa_a(4700.0) * 0.5

# Esvaziar a FIFO quando estiver pela metade: margem para o despertar atrasar
# sem transbordar. Escolha de projeto, não dado.
FRACAO_ENCHIMENTO = 0.5

# --- Premissas de referência do Z.4.4 (as mesmas, para comparar) -----------
I_ESP_REF_A = ESP32_I_MODEM_SLEEP_80MHZ_A[0]   # 20 mA
I_RF_REF_A = NAO_CONFERIDO_I_RF_A[0]           # 100 mA
T_POST_REF_S = 1.0
POSTS_POR_H_EPOCA = 3600.0 / EPOCA_S           # 120: uma entrega por época
POSTS_POR_H_LOTE = 1.0                         # API-03: um lote por hora
WOM_DESPERTARES_H = 60.0                       # Z.4.4
WOM_T_ACORDADO_S = 0.5                         # Z.4.4
CAPACIDADE_REF_MAH = 2000.0                    # Z.4.4, bateria hipotética

# Taxas candidatas (b). 50 Hz = SMPLRT_DIV 19; 62,5 Hz = 15; 100 Hz = 9.
FS_FIFO_REF_HZ = 50.0
FS_TIMER_HZ = 64.0                              # 2 × a grade, decima por 2


# ══════════════════════════════════════════════════════════════════════════
# (b) — o que o sensor consegue entregar
# ══════════════════════════════════════════════════════════════════════════

def taxa_mpu_hz(div: int, base_hz: float = MPU_TAXA_ACEL_INTERNA_HZ) -> float:
    return base_hz / (1 + div)


def div_mais_proximo(alvo_hz: float, base_hz: float = MPU_TAXA_ACEL_INTERNA_HZ) -> int:
    return min(range(SMPLRT_DIV_MAX + 1),
               key=lambda d: abs(taxa_mpu_hz(d, base_hz) - alvo_hz))


def erro_relativo(div: int, alvo_hz: float,
                  base_hz: float = MPU_TAXA_ACEL_INTERNA_HZ) -> float:
    return taxa_mpu_hz(div, base_hz) / alvo_hz - 1.0


def amostras_na_fifo() -> int:
    return MPU_FIFO_B // BYTES_POR_AMOSTRA_ACEL


def autonomia_fifo_s(fs_hz: float) -> float:
    return amostras_na_fifo() / fs_hz


def nyquist_ok(fs_hz: float, banda_hz: float) -> bool:
    return fs_hz >= 2.0 * banda_hz


def inicio_do_alias_na_banda_hz(fs_hz: float) -> float:
    """Menor frequência de entrada que dobra para DENTRO dos 12,8 Hz do ml/.

    Uma componente em f > fs/2 aparece em fs − f. Ela só contamina as features
    se cair abaixo do corte de software (12,8 Hz), isto é, se f > fs − 12,8.
    O que dobra para a faixa entre 12,8 Hz e fs/2 o filtro de software remove.
    É este número — não 2 × banda do DLPF — que a amostragem precisa empurrar
    para onde o DLPF já atenuou.
    """
    return fs_hz - CORTE_ML_HZ


# ══════════════════════════════════════════════════════════════════════════
# (a) — corrente média das arquiteturas
# ══════════════════════════════════════════════════════════════════════════

def i_sensor_normal_a() -> float:
    return MPU_I_ACEL_SO_A + MPU_I_VLOGIC_A


def i_sensor_lp_a(hz: float = 40.0) -> float:
    return MPU_I_ACEL_BAIXO_CONSUMO_A[hz] + MPU_I_VLOGIC_A


def cenario_sono_leve(fs_hz: float, amostras_por_despertar: int, *,
                      i_esp_a: float = I_ESP_REF_A,
                      i_rf_a: float = I_RF_REF_A,
                      t_post_s: float = T_POST_REF_S,
                      posts_por_h: float = POSTS_POR_H_EPOCA,
                      i_placa_a: float = 0.0,
                      t_despertar_s: float = NAO_CONFERIDO_T_DESPERTAR_S[1],
                      i2c_hz: float = I2C_HZ[0],
                      t_proc_amostra_s: float = NAO_CONFERIDO_T_PROC_AMOSTRA_S[1],
                      i_sensor_a: float | None = None) -> float:
    """ESP32 em sono leve; acorda, lê `amostras_por_despertar` e volta.

    `amostras_por_despertar = 1` é a variante C1 (despertar por temporizador a
    cada amostra); `> 1` é a C2 (o MPU enche a FIFO, o ESP32 a esvazia).
    """
    if i_sensor_a is None:
        i_sensor_a = i_sensor_normal_a()
    despertares_h = fs_hz * 3600.0 / amostras_por_despertar
    bytes_ = amostras_por_despertar * BYTES_POR_AMOSTRA_ACEL + BYTES_OVERHEAD_I2C
    t_i2c = bytes_ * BITS_POR_BYTE_I2C / i2c_hz
    t_ativo = despertares_h * (t_despertar_s + t_i2c
                               + amostras_por_despertar * t_proc_amostra_s)
    t_rf = posts_por_h * t_post_s
    t_sono = 3600.0 - t_ativo - t_rf
    if t_sono < 0:
        raise ValueError("o ciclo de despertar não cabe na hora")
    return corrente_media_a([
        ("radio", i_rf_a + i_sensor_a + i_placa_a, t_rf),
        ("ativo", i_esp_a + i_sensor_a + I_PULLUP_TRAFEGO_A + i_placa_a, t_ativo),
        ("sono", ESP32_I_LIGHT_SLEEP_A + i_sensor_a + i_placa_a, t_sono),
    ])


def fracoes_c2(fs_hz: float = FS_FIFO_REF_HZ) -> tuple[float, float]:
    """(acordado lendo, sono leve) como fração da hora, premissas de referência."""
    n = amostras_c2(fs_hz)
    despertares_h = fs_hz * 3600.0 / n
    bytes_ = n * BYTES_POR_AMOSTRA_ACEL + BYTES_OVERHEAD_I2C
    t_ativo = despertares_h * (NAO_CONFERIDO_T_DESPERTAR_S[1]
                               + bytes_ * BITS_POR_BYTE_I2C / I2C_HZ[0]
                               + n * NAO_CONFERIDO_T_PROC_AMOSTRA_S[1])
    t_rf = POSTS_POR_H_EPOCA * T_POST_REF_S
    return t_ativo / 3600.0, (3600.0 - t_ativo - t_rf) / 3600.0


def amostras_c2(fs_hz: float = FS_FIFO_REF_HZ) -> int:
    del fs_hz  # o enchimento é em amostras, não em tempo
    return int(amostras_na_fifo() * FRACAO_ENCHIMENTO)


def arq_a(i_placa_a: float = 0.0, posts_por_h: float | None = None) -> float:
    """WoM do `sketch.ino`, pelo modelo do Z.4.4. `posts_por_h` = lote."""
    t_post = T_POST_REF_S
    if posts_por_h is not None:
        t_post = T_POST_REF_S * posts_por_h / WOM_DESPERTARES_H
    return cenario_wom(I_ESP_REF_A, I_RF_REF_A, t_post, WOM_DESPERTARES_H,
                       WOM_T_ACORDADO_S, i_placa_a)


def arq_b(i_placa_a: float = 0.0, posts_por_h: float = POSTS_POR_H_EPOCA) -> float:
    return cenario_continuo(I_ESP_REF_A, I_RF_REF_A, T_POST_REF_S, posts_por_h,
                            I_PULLUP_TRAFEGO_A, i_placa_a)


def arq_c1(i_placa_a: float = 0.0, posts_por_h: float = POSTS_POR_H_EPOCA,
           **kw) -> float:
    return cenario_sono_leve(FS_TIMER_HZ, 1, i_placa_a=i_placa_a,
                             posts_por_h=posts_por_h, **kw)


def arq_c2(i_placa_a: float = 0.0, posts_por_h: float = POSTS_POR_H_EPOCA,
           fs_hz: float = FS_FIFO_REF_HZ, **kw) -> float:
    return cenario_sono_leve(fs_hz, amostras_c2(fs_hz), i_placa_a=i_placa_a,
                             posts_por_h=posts_por_h, **kw)


def arq_c2_lp(i_placa_a: float = 0.0,
              posts_por_h: float = POSTS_POR_H_EPOCA) -> float:
    """CONDICIONAL: FIFO no modo de baixo consumo a 40 Hz com DLPF de 10 Hz."""
    return cenario_sono_leve(40.0, amostras_c2(40.0), i_placa_a=i_placa_a,
                             posts_por_h=posts_por_h,
                             i_sensor_a=i_sensor_lp_a(40.0))


def varredura_c2() -> tuple[float, float]:
    """Mínimo e máximo de C2 sobre todos os parâmetros em faixa."""
    vals = []
    for i_esp in ESP32_I_MODEM_SLEEP_80MHZ_A:
        for i_rf in NAO_CONFERIDO_I_RF_A:
            for t_post in (0.5, 2.0):
                for t_d in NAO_CONFERIDO_T_DESPERTAR_S:
                    for f in I2C_HZ:
                        for t_p in NAO_CONFERIDO_T_PROC_AMOSTRA_S:
                            vals.append(arq_c2(i_esp_a=i_esp, i_rf_a=i_rf,
                                               t_post_s=t_post,
                                               t_despertar_s=t_d, i2c_hz=f,
                                               t_proc_amostra_s=t_p))
    return min(vals), max(vals)


def varredura_b() -> tuple[float, float]:
    """A mesma varredura do Z.4.4, para pôr C2 ao lado."""
    vals = [cenario_continuo(i_esp, i_rf, t_post, POSTS_POR_H_EPOCA,
                             I_PULLUP_TRAFEGO_A, 0.0)
            for i_esp in ESP32_I_MODEM_SLEEP_80MHZ_A
            for i_rf in NAO_CONFERIDO_I_RF_A
            for t_post in (0.5, 2.0)]
    return min(vals), max(vals)


def fracao_radio(i_total_a: float, posts_por_h: float = POSTS_POR_H_EPOCA,
                 i_rf_a: float = I_RF_REF_A, t_post_s: float = T_POST_REF_S) -> float:
    """Parcela da corrente média que é o rádio (só o I_rf, não o resto)."""
    return i_rf_a * posts_por_h * t_post_s / 3600.0 / i_total_a


PLACAS_A = (0.0, 1e-3, 5e-3, 10e-3)


# ══════════════════════════════════════════════════════════════════════════
# Relatório
# ══════════════════════════════════════════════════════════════════════════

def _t(titulo: str) -> None:
    print(f"\n{titulo}\n{'─' * len(titulo)}")


def relatorio() -> None:
    print("ARQ-01 — CADÊNCIA DE AMOSTRAGEM E ARQUITETURA")
    print("=" * 74)

    _t("(b) · o que o MPU-6050 entrega")
    print(f"  taxa = {MPU_TAXA_ACEL_INTERNA_HZ:.0f} Hz / (1 + SMPLRT_DIV), "
          f"relógio interno")
    for alvo in (GRADE_COMUM_HZ, 2 * GRADE_COMUM_HZ):
        d = div_mais_proximo(alvo)
        print(f"  alvo {alvo:5.1f} Hz → div {d:2d} = {taxa_mpu_hz(d):7.3f} Hz "
              f"({erro_relativo(d, alvo) * 100:+.2f} %)")
    for alvo in (GRADE_COMUM_HZ, 2 * GRADE_COMUM_HZ):
        d = div_mais_proximo(alvo, MPU_TAXA_ACEL_CLK_32K_HZ)
        print(f"  com cristal de 32,768 kHz: alvo {alvo:4.0f} Hz → div {d:2d} = "
              f"{taxa_mpu_hz(d, MPU_TAXA_ACEL_CLK_32K_HZ):6.2f} Hz (exato)")
    print(f"  tolerância do oscilador interno: "
          f"{MPU_TOL_OSC_INTERNO_25C[0] * 100:+.0f}/"
          f"{MPU_TOL_OSC_INTERNO_25C[1] * 100:+.0f} % a 25 °C, "
          f"{MPU_TOL_OSC_INTERNO_TEMP[0] * 100:+.0f}/"
          f"{MPU_TOL_OSC_INTERNO_TEMP[1] * 100:+.0f} % na temperatura")
    print("  ⇒ nenhuma taxa ditada pelo MPU cai na grade; o firmware reamostra,"
          " como o ml/ já faz")
    print(f"  FIFO: {MPU_FIFO_B} B / {BYTES_POR_AMOSTRA_ACEL} B = "
          f"{amostras_na_fifo()} amostras")
    for fs in (40.0, 50.0, 62.5, 100.0):
        print(f"    a {fs:5.1f} Hz enche em {autonomia_fifo_s(fs):5.2f} s; "
              f"esvaziada pela metade a cada "
              f"{autonomia_fifo_s(fs) * FRACAO_ENCHIMENTO:4.2f} s")
    print(f"  corte do ml/: {CORTE_ML_HZ:.1f} Hz")
    for fs in (40.0, 50.0, 62.5, 100.0):
        print(f"    a {fs:5.1f} Hz, só entrada acima de "
              f"{inicio_do_alias_na_banda_hz(fs):5.1f} Hz dobra para dentro "
              f"dos {CORTE_ML_HZ:.1f} Hz")
    for banda in (DLPF_21_HZ, DLPF_10_HZ):
        print(f"    DLPF {banda:4.1f} Hz: Nyquist pede ≥ {2 * banda:4.0f} Hz; "
              f"40 Hz (teto do baixo consumo) "
              f"{'serve' if nyquist_ok(40.0, banda) else 'NÃO serve'}; "
              f"corta {'acima' if banda > CORTE_ML_HZ else 'ABAIXO'} dos "
              f"{CORTE_ML_HZ:.1f} Hz do ml/")

    _t("(a) · corrente média, só circuitos integrados, premissas do Z.4.4")
    linhas = [
        ("A  WoM, sem features", arq_a()),
        ("B  contínua, CPU ativa", arq_b()),
        ("C1 sono leve, 1 amostra/despertar (64 Hz)", arq_c1()),
        ("C2 sono leve + FIFO (50 Hz)", arq_c2()),
        ("C2-LP CONDICIONAL (40 Hz, DLPF 10 Hz)", arq_c2_lp()),
    ]
    for nome, i in linhas:
        print(f"  {nome:<44} {i * 1e3:6.2f} mA → "
              f"{autonomia_h(CAPACIDADE_REF_MAH, i):6.1f} h")
    print(f"  C2: {amostras_c2()} amostras por despertar, "
          f"{FS_FIFO_REF_HZ * 3600 / amostras_c2():.0f} despertares/h")
    ativo, sono = fracoes_c2()
    print(f"  C2 passa {ativo * 100:.1f} % da hora acordado lendo e "
          f"{sono * 100:.1f} % em sono leve")
    print(f"  rádio é {fracao_radio(arq_c2()) * 100:.0f} % de C2 e "
          f"{fracao_radio(arq_b()) * 100:.0f} % de B")
    lo, hi = varredura_c2()
    blo, bhi = varredura_b()
    print(f"  varredura dos parâmetros em faixa: C2 ∈ [{lo * 1e3:.2f}; "
          f"{hi * 1e3:.2f}] mA, B ∈ [{blo * 1e3:.1f}; {bhi * 1e3:.1f}] mA")

    _t("(a) · com lote (API-03): uma entrega por hora")
    for nome, f in (("A", lambda p: arq_a(p, POSTS_POR_H_LOTE)),
                    ("B", lambda p: arq_b(p, POSTS_POR_H_LOTE)),
                    ("C1", lambda p: arq_c1(p, POSTS_POR_H_LOTE)),
                    ("C2", lambda p: arq_c2(p, POSTS_POR_H_LOTE))):
        print(f"  {nome:<3} {f(0.0) * 1e3:6.2f} mA")

    _t("(a) · o consumo fixo da placa, somado  [PARÂM]")
    print("  I_placa   |      A |      B |     C1 |     C2 |  B/C2 | C2/A")
    for p in PLACAS_A:
        a, b, c1, c2 = arq_a(p), arq_b(p), arq_c1(p), arq_c2(p)
        print(f"  {p * 1e3:5.1f} mA | {a * 1e3:6.2f} | {b * 1e3:6.2f} | "
              f"{c1 * 1e3:6.2f} | {c2 * 1e3:6.2f} | {b / c2:5.2f} | "
              f"{c2 / a:4.2f}")


# ══════════════════════════════════════════════════════════════════════════
# Asserções — travam os números de docs/DECISAO-ARQ-01-CADENCIA.md
# ══════════════════════════════════════════════════════════════════════════

def conferir() -> int:
    falhas: list[str] = []

    def eq(rotulo: str, obtido: float, esperado: float, tol: float) -> None:
        if abs(obtido - esperado) > tol:
            falhas.append(f"{rotulo}: obtido {obtido!r}, documento diz {esperado!r}")

    def verdade(rotulo: str, cond: bool) -> None:
        if not cond:
            falhas.append(f"{rotulo}: deixou de valer")

    # Âncora no Z.4.4: se estas caírem, o modelo de referência mudou.
    eq("A (Z.4.4)", arq_a() * 1e3, 1.91, 0.01)
    eq("B (Z.4.4)", arq_b() * 1e3, 23.9, 0.1)

    # (b)
    eq("corte do ml/", CORTE_ML_HZ, 12.8, 1e-9)
    verdade("32 Hz não é taxa exata do MPU",
            abs(erro_relativo(div_mais_proximo(32.0), 32.0)) > 1e-6)
    verdade("64 Hz não é taxa exata do MPU",
            abs(erro_relativo(div_mais_proximo(64.0), 64.0)) > 1e-6)
    eq("div para 32 Hz", div_mais_proximo(32.0), 30, 0)
    eq("erro 32 Hz (%)", erro_relativo(30, 32.0) * 100, 0.81, 0.005)
    eq("div para 64 Hz", div_mais_proximo(64.0), 15, 0)
    eq("erro 64 Hz (%)", erro_relativo(15, 64.0) * 100, -2.34, 0.005)
    verdade("cristal de 32 kHz dá 32 Hz exato",
            taxa_mpu_hz(31, MPU_TAXA_ACEL_CLK_32K_HZ) == 32.0)
    eq("amostras na FIFO", amostras_na_fifo(), 170, 0)
    eq("FIFO a 50 Hz (s)", autonomia_fifo_s(50.0), 3.40, 0.005)
    eq("C2 amostras/despertar", amostras_c2(), 85, 0)
    verdade("DLPF 21 Hz não cabe em 40 Hz", not nyquist_ok(40.0, DLPF_21_HZ))
    verdade("DLPF 10 Hz cabe em 40 Hz", nyquist_ok(40.0, DLPF_10_HZ))
    verdade("DLPF 10 Hz corta abaixo do ml/", DLPF_10_HZ < CORTE_ML_HZ)
    eq("alias na banda a 40 Hz", inicio_do_alias_na_banda_hz(40.0), 27.2, 1e-9)
    eq("alias na banda a 50 Hz", inicio_do_alias_na_banda_hz(50.0), 37.2, 1e-9)
    eq("alias na banda a 62,5 Hz", inicio_do_alias_na_banda_hz(62.5), 49.7, 1e-9)

    # (a), sem placa
    eq("C1", arq_c1() * 1e3, 7.64, 0.01)
    eq("C2", arq_c2() * 1e3, 5.31, 0.01)
    eq("C2-LP", arq_c2_lp() * 1e3, 4.80, 0.01)
    eq("B/C2", arq_b() / arq_c2(), 4.50, 0.01)
    eq("rádio em C2 (%)", fracao_radio(arq_c2()) * 100, 63.0, 0.5)
    lo, hi = varredura_c2()
    eq("C2 mínimo", lo * 1e3, 3.20, 0.01)
    eq("C2 máximo", hi * 1e3, 18.55, 0.01)
    # A ordem que o documento afirma, em toda a varredura da placa.
    for p in PLACAS_A:
        verdade(f"A < C2 < C1 < B com placa {p * 1e3:.0f} mA",
                arq_a(p) < arq_c2(p) < arq_c1(p) < arq_b(p))

    # (a), com lote
    eq("A lote", arq_a(posts_por_h=POSTS_POR_H_LOTE) * 1e3, 0.27, 0.01)
    eq("B lote", arq_b(posts_por_h=POSTS_POR_H_LOTE) * 1e3, 21.24, 0.01)
    eq("C2 lote", arq_c2(posts_por_h=POSTS_POR_H_LOTE) * 1e3, 2.03, 0.01)
    eq("C2/A lote", arq_c2(posts_por_h=POSTS_POR_H_LOTE)
       / arq_a(posts_por_h=POSTS_POR_H_LOTE), 7.6, 0.05)

    ativo, sono = fracoes_c2()
    eq("C2 acordado (%)", ativo * 100, 3.1, 0.05)
    eq("C2 em sono leve (%)", sono * 100, 93.6, 0.05)

    # placa de 5 e 10 mA
    eq("B/A placa 5 mA", arq_b(5e-3) / arq_a(5e-3), 4.18, 0.01)
    eq("B/A placa 10 mA", arq_b(10e-3) / arq_a(10e-3), 2.85, 0.01)
    eq("B/C2 placa 5 mA", arq_b(5e-3) / arq_c2(5e-3), 2.80, 0.01)
    eq("C2/A placa 5 mA", arq_c2(5e-3) / arq_a(5e-3), 1.49, 0.01)

    if falhas:
        print("DIVERGÊNCIAS (o documento manda até prova em contrário):")
        for f in falhas:
            print(f"  ✗ {f}")
        return 1
    print("✓ todas as asserções batem com docs/DECISAO-ARQ-01-CADENCIA.md.")
    return 0


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--conferir", action="store_true",
                    help="só as asserções contra o documento")
    args = ap.parse_args()
    if args.conferir:
        return conferir()
    relatorio()
    print()
    return conferir()


if __name__ == "__main__":
    sys.exit(main())
