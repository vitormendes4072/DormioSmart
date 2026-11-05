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
                      i_sensor_a: float | None = None,
                      i_pullup_a: float = I_PULLUP_TRAFEGO_A) -> float:
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
        ("ativo", i_esp_a + i_sensor_a + i_pullup_a + i_placa_a, t_ativo),
        ("sono", ESP32_I_LIGHT_SLEEP_A + i_sensor_a + i_placa_a, t_sono),
    ])


def fracoes_c2(fs_hz: float = FS_FIFO_REF_HZ,
               i2c_hz: float = I2C_HZ[0]) -> tuple[float, float]:
    """(acordado lendo, sono leve) como fração da hora, premissas de referência."""
    n = amostras_c2(fs_hz)
    despertares_h = fs_hz * 3600.0 / n
    bytes_ = n * BYTES_POR_AMOSTRA_ACEL + BYTES_OVERHEAD_I2C
    t_ativo = despertares_h * (NAO_CONFERIDO_T_DESPERTAR_S[1]
                               + bytes_ * BITS_POR_BYTE_I2C / i2c_hz
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
# CALC-01 — a C2 como o `sketch.ino` a implementou (04/11)
# ══════════════════════════════════════════════════════════════════════════
#
# O C2 acima é o de 30/10, anterior ao firmware: um envio por época (ou "um
# lote por hora") de 1 s de rádio. O `sketch.ino` (FW-07 (b)) fixou outra
# coisa: um lote a cada 10 min, e cada envio LIGA o Wi-Fi, associa, faz TLS e
# o POST e DESLIGA (`WiFi.mode(WIFI_OFF)`). E grava cada época na flash
# (FW-08). Os parâmetros que o firmware fixa são LIDOS do firmware, não
# copiados: se o código mudar, o `--conferir` reprova.

RAIZ = Path(__file__).resolve().parent.parent


def _constante_do_firmware(arquivo: str, nome: str) -> int:
    """Valor inteiro de uma constante C++ (`... NOME = 10ull * 60ull * ...;`)."""
    import re
    texto = (RAIZ / arquivo).read_text(encoding="utf-8")
    m = re.search(rf"\b{nome}\s*=\s*([^;]+);", texto)
    if not m:
        raise SystemExit(f"constante {nome} não encontrada em {arquivo}")
    expr = re.sub(r"(\d+)u?ll?\b", r"\1", m.group(1))
    if not re.fullmatch(r"[\d\s*]+", expr):
        raise SystemExit(f"{nome} em {arquivo} não é produto de inteiros: {expr!r}")
    return math.prod(int(x) for x in expr.split("*"))


INTERVALO_DE_ENVIO_S = _constante_do_firmware(
    "firmware/sketch.ino", "INTERVALO_DE_ENVIO_US") / 1e6
INTERVALO_DE_DRENAGEM_S = _constante_do_firmware(
    "firmware/nucleo/cadeia_c2.h", "INTERVALO_DE_DRENAGEM_US") / 1e6
POSTS_POR_H_IMPL = 3600.0 / INTERVALO_DE_ENVIO_S             # 6

# ⚠️ NAO_CONFERIDO: duração de um envio inteiro — ligar o rádio, associar ao
# ponto de acesso, obter endereço, sincronizar o relógio (NTP, a cada envio),
# negociar o TLS (o firmware confere a cadeia, SEC-15) e o POST do lote. Não há
# medição; a faixa é estimativa. O teto do próprio firmware é bem maior
# (TIMEOUT_WIFI_MS 20 s + TIMEOUT_NTP_MS 5 s + TIMEOUT_POST_MS 8 s, e até
# LOTES_POR_VOLTA = 20 lotes por conexão): rede ruim, ou a descarga do que
# acumulou sem rede, custa mais que o pior caso da faixa — dito no texto.
NAO_CONFERIDO_T_ENVIO_S = (2.0, 4.0, 8.0)
T_ENVIO_REF_S = NAO_CONFERIDO_T_ENVIO_S[1]

# --- Flash (FW-08): um registro de 64 B por época --------------------------
# 64 B por registro (`registro_flash.h`); setor de apagamento de 4 KiB, logo um
# apagamento a cada 64 registros. ⚠️ NAO_CONFERIDO: tempos e corrente da flash
# SPI do módulo (a memória varia por lote do módulo; ordem de grandeza de
# folhas de NOR SPI comuns: programação de página ~0,7–3 ms, apagamento de
# setor ~45–400 ms, ~25 mA). Faixas largas, de propósito: o ponto é mostrar
# que o termo é pequeno, não estimá-lo bem.
BYTES_REGISTRO_FLASH = 64
BYTES_SETOR_FLASH = 4096
NAO_CONFERIDO_T_PROGRAMA_S = (0.7e-3, 3e-3)
NAO_CONFERIDO_T_APAGA_SETOR_S = (45e-3, 400e-3)
NAO_CONFERIDO_I_FLASH_A = (15e-3, 25e-3)
EPOCAS_POR_H = 3600.0 / EPOCA_S


def corrente_da_flash_a(t_prog_s: float = NAO_CONFERIDO_T_PROGRAMA_S[1],
                        t_apaga_s: float = NAO_CONFERIDO_T_APAGA_SETOR_S[1],
                        i_flash_a: float = NAO_CONFERIDO_I_FLASH_A[1],
                        i_esp_a: float = I_ESP_REF_A) -> float:
    """Acréscimo médio por gravar a época na flash, sobre o sono leve.

    Durante a escrita a CPU está acordada (I_esp) e a flash consome I_flash; o
    acréscimo é sobre o que o sono leve gastaria no mesmo intervalo.
    """
    apagamentos_h = EPOCAS_POR_H * BYTES_REGISTRO_FLASH / BYTES_SETOR_FLASH
    t_h = EPOCAS_POR_H * t_prog_s + apagamentos_h * t_apaga_s
    return (i_esp_a + i_flash_a - ESP32_I_LIGHT_SLEEP_A) * t_h / 3600.0


# --- I2C como o firmware o usa (CALC-04, 04/11) -----------------------------
# O C2 de 30/10 e a primeira versão do CALC-01 calculavam a leitura da FIFO a
# 100 kHz e com pull-ups de 4,7 kΩ. O `sketch.ino` chama `Wire.setClock(400000)`,
# e o GY-521 traz os pull-ups no próprio módulo, de 2,2 kΩ ou 10 kΩ conforme o
# lote (DIAG-02) — não 4,7 kΩ. A frequência é LIDA do firmware; o pull-up é
# faixa, e a referência é o lote de 2,2 kΩ, o pior para a energia.

def _clock_i2c_do_firmware() -> float:
    import re
    texto = (RAIZ / "firmware/sketch.ino").read_text(encoding="utf-8")
    m = re.search(r"Wire\.setClock\((\d+)\)", texto)
    if not m:
        raise SystemExit("Wire.setClock(...) não encontrado em firmware/sketch.ino")
    return float(m.group(1))


I2C_HZ_FIRMWARE = _clock_i2c_do_firmware()                   # 400 kHz
R_PULLUP_MODULO_OHM = (2200.0, 10000.0)                      # DIAG-02, por lote
R_PULLUP_REF_OHM = R_PULLUP_MODULO_OHM[0]


def i_pullup_trafego_a(r_ohm: float) -> float:
    """As duas linhas, metade do tempo em nível baixo, só durante o tráfego."""
    return 2 * corrente_pullup_linha_baixa_a(r_ohm) * 0.5


def c2_impl(i_placa_a: float = 0.0, t_envio_s: float = T_ENVIO_REF_S,
            i_rf_a: float = I_RF_REF_A, flash_a: float | None = None,
            r_pullup_ohm: float = R_PULLUP_REF_OHM, **kw) -> float:
    """A C2 do `sketch.ino`: lote a cada 10 min, envio com conexão, flash,
    I2C na frequência do firmware e pull-up do módulo."""
    if flash_a is None:
        flash_a = corrente_da_flash_a()
    kw.setdefault("i2c_hz", I2C_HZ_FIRMWARE)
    kw.setdefault("i_pullup_a", i_pullup_trafego_a(r_pullup_ohm))
    return arq_c2(i_placa_a, posts_por_h=POSTS_POR_H_IMPL, t_post_s=t_envio_s,
                  i_rf_a=i_rf_a, **kw) + flash_a


# Equação 3 do texto do TCC (Produto 5, 6.4.1): E = V_alim · I · t. A tensão de
# 3,3 V e a noite de 8 h são as do próprio texto; ficam aqui para a inserção do
# CALC-01 citar a energia da C2 com número saído do script.
V_ALIM_REF_V = 3.3
NOITE_S = 8 * 3600.0


def energia_da_noite_j(i_media_a: float) -> float:
    return V_ALIM_REF_V * i_media_a * NOITE_S


def decomposicao_c2_impl(t_envio_s: float = T_ENVIO_REF_S) -> dict[str, float]:
    """Parcelas da corrente média (A), premissas de referência, sem placa.

    Soma igual a `c2_impl(t_envio_s=...)` — o `--conferir` trava isso.
    """
    ativo, _ = fracoes_c2(i2c_hz=I2C_HZ_FIRMWARE)
    t_ativo = ativo * 3600.0
    t_rf = POSTS_POR_H_IMPL * t_envio_s
    t_sono = 3600.0 - t_ativo - t_rf
    return {
        "transdutor (sempre ligado, 50 Hz)": i_sensor_normal_a(),
        "ESP32 em sono leve": ESP32_I_LIGHT_SLEEP_A * t_sono / 3600.0,
        "ESP32 acordado esvaziando a FIFO":
            (I_ESP_REF_A + i_pullup_trafego_a(R_PULLUP_REF_OHM)) * t_ativo / 3600.0,
        "rádio (envio a cada 10 min)": I_RF_REF_A * t_rf / 3600.0,
        "flash (uma época por registro)": corrente_da_flash_a(),
    }


def varredura_c2_impl() -> tuple[float, float]:
    """Mínimo e máximo sobre todos os parâmetros em faixa, flash incluída."""
    flashes = [corrente_da_flash_a(tp, ta, i_f)
               for tp in NAO_CONFERIDO_T_PROGRAMA_S
               for ta in NAO_CONFERIDO_T_APAGA_SETOR_S
               for i_f in NAO_CONFERIDO_I_FLASH_A]
    vals = []
    for i_esp in ESP32_I_MODEM_SLEEP_80MHZ_A:
        for i_rf in NAO_CONFERIDO_I_RF_A:
            for t_env in NAO_CONFERIDO_T_ENVIO_S:
                for t_d in NAO_CONFERIDO_T_DESPERTAR_S:
                    for r in R_PULLUP_MODULO_OHM:
                        for t_p in NAO_CONFERIDO_T_PROC_AMOSTRA_S:
                            base = c2_impl(t_envio_s=t_env, i_rf_a=i_rf,
                                           flash_a=0.0, i_esp_a=i_esp,
                                           t_despertar_s=t_d, r_pullup_ohm=r,
                                           t_proc_amostra_s=t_p)
                            vals += [base + min(flashes), base + max(flashes)]
    return min(vals), max(vals)


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

    _t("CALC-01 · a C2 como o sketch.ino a implementou")
    print(f"  lido do firmware: envio a cada {INTERVALO_DE_ENVIO_S:.0f} s "
          f"({POSTS_POR_H_IMPL:.0f}/h), drenagem a {INTERVALO_DE_DRENAGEM_S:.2f} s "
          f"(o modelo: {amostras_c2()} amostras / {FS_FIFO_REF_HZ:.0f} Hz = "
          f"{amostras_c2() / FS_FIFO_REF_HZ:.2f} s)")
    print(f"  I2C do firmware: {I2C_HZ_FIRMWARE / 1e3:.0f} kHz; pull-up do módulo "
          f"{R_PULLUP_MODULO_OHM[0] / 1e3:.1f} ou {R_PULLUP_MODULO_OHM[1] / 1e3:.0f} kΩ "
          f"→ {c2_impl(r_pullup_ohm=R_PULLUP_MODULO_OHM[0]) * 1e3:.3f} ou "
          f"{c2_impl(r_pullup_ohm=R_PULLUP_MODULO_OHM[1]) * 1e3:.3f} mA")
    for t in NAO_CONFERIDO_T_ENVIO_S:
        i = c2_impl(t_envio_s=t)
        print(f"  envio de {t:3.0f} s [ESTIM]: {i * 1e3:5.2f} mA → "
              f"{autonomia_h(CAPACIDADE_REF_MAH, i):5.0f} h; rádio "
              f"{fracao_radio(i, POSTS_POR_H_IMPL, t_post_s=t) * 100:3.0f} %")
    d = decomposicao_c2_impl()
    total = sum(d.values())
    print(f"  parcelas, envio de {T_ENVIO_REF_S:.0f} s:")
    for nome, v in d.items():
        print(f"    {nome:<36} {v * 1e3:6.3f} mA  {v / total * 100:5.1f} %")
    lo, hi = varredura_c2_impl()
    print(f"  varredura de todos os parâmetros em faixa: [{lo * 1e3:.2f}; "
          f"{hi * 1e3:.2f}] mA")

    _t("(a) · o consumo fixo da placa, somado  [PARÂM]")
    print("  I_placa   | C2 implementada | autonomia (2 000 mA·h)")
    for p in PLACAS_A + (20e-3,):
        i = c2_impl(p)
        print(f"  {p * 1e3:5.1f} mA | {i * 1e3:8.2f} mA     | "
              f"{autonomia_h(CAPACIDADE_REF_MAH, i):6.0f} h")
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

    # CALC-01: a C2 implementada. Os dois primeiros cruzam o modelo com o
    # firmware — se o `sketch.ino` mudar o envio ou o núcleo mudar a drenagem,
    # o texto do Z.4.4b deixa de valer.
    eq("envio do firmware (s)", INTERVALO_DE_ENVIO_S, 600.0, 0)
    eq("drenagem: firmware = modelo (s)", INTERVALO_DE_DRENAGEM_S,
       amostras_c2() / FS_FIFO_REF_HZ, 1e-9)
    # CALC-04 (04/11): o I2C do firmware é 400 kHz, não 100 kHz — lido do
    # `sketch.ino`. Os números abaixo foram corrigidos por isso (eram 2,68 mA).
    eq("I2C do firmware (Hz)", I2C_HZ_FIRMWARE, 400e3, 0)
    eq("C2 implementada (mA)", c2_impl() * 1e3, 2.28, 0.01)
    eq("C2 impl., pull-up de 10 kΩ (mA)", c2_impl(r_pullup_ohm=10e3) * 1e3, 2.27, 0.01)
    eq("C2 impl., envio de 2 s (mA)", c2_impl(t_envio_s=2.0) * 1e3, 1.95, 0.01)
    eq("C2 impl., envio de 8 s (mA)", c2_impl(t_envio_s=8.0) * 1e3, 2.94, 0.01)
    eq("C2 impl. → autonomia (h)", autonomia_h(CAPACIDADE_REF_MAH, c2_impl()),
       878.0, 1.0)
    eq("rádio na C2 impl. (%)",
       fracao_radio(c2_impl(), POSTS_POR_H_IMPL, t_post_s=T_ENVIO_REF_S) * 100,
       29.3, 0.1)
    d = decomposicao_c2_impl()
    eq("parcelas somam a C2 impl.", sum(d.values()), c2_impl(), 1e-12)
    eq("parcela da FIFO, pull-up de 2,2 kΩ (mA)",
       d["ESP32 acordado esvaziando a FIFO"] * 1e3, 0.212, 0.0005)
    eq("maior parcela: sono leve (%)",
       d["ESP32 em sono leve"] / sum(d.values()) * 100, 34.5, 0.1)
    verdade("nenhuma parcela passa de 40 %",
            max(d.values()) / sum(d.values()) < 0.40)
    verdade("flash abaixo de 1 %",
            d["flash (uma época por registro)"] / sum(d.values()) < 0.01)
    lo, hi = varredura_c2_impl()
    eq("C2 impl. mínimo (mA)", lo * 1e3, 1.88, 0.01)
    eq("C2 impl. máximo (mA)", hi * 1e3, 5.19, 0.01)
    verdade("C2 impl. entre o lote por hora e o envio por época",
            arq_c2(posts_por_h=POSTS_POR_H_LOTE) < c2_impl() < arq_c2())
    for p in PLACAS_A:
        verdade(f"A < C2 impl. < B com placa {p * 1e3:.0f} mA",
                arq_a(p) < c2_impl(p) < arq_b(p))
    eq("C2 impl. com placa de 1 mA", c2_impl(1e-3) * 1e3, 3.28, 0.01)
    eq("C2 impl. com placa de 20 mA", c2_impl(20e-3) * 1e3, 22.28, 0.01)
    eq("energia de 8 h, C2 impl. (J)", energia_da_noite_j(c2_impl()), 217.0, 0.5)
    eq("C2 impl. → autonomia com 1 000 mA·h (h)", autonomia_h(1000.0, c2_impl()),
       439.0, 0.5)
    eq("energia de 8 h, placa de 1 mA (J)", energia_da_noite_j(c2_impl(1e-3)),
       312.0, 0.5)

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
