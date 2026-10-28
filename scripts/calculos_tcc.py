#!/usr/bin/env python3
"""Reproduz, número a número, os modelos de `docs/CALCULOS-TCC.md` (CALC-01..04).

    python3 scripts/calculos_tcc.py            # imprime tudo
    python3 scripts/calculos_tcc.py --conferir # só as asserções; sai != 0 se algo divergir

Não depende de nada além da biblioteca padrão. Nenhuma constante aqui é
inventada: cada uma traz, no comentário, a fonte e a CONDIÇÃO DE MEDIÇÃO.
Onde o valor não pôde ser conferido na fonte, a constante está marcada
`NAO_CONFERIDO` e entra no documento como parâmetro, não como número.

O bloco `conferir()` ao final trava os valores que já estavam escritos em
outros documentos do repositório. Se alguém mudar uma constante e o número
publicado deixar de sair, este script falha — que é o ponto dele existir.
"""

from __future__ import annotations

import argparse
import math
import sys

# ══════════════════════════════════════════════════════════════════════════
# CONSTANTES — cada uma com fonte e condição de medição
# ══════════════════════════════════════════════════════════════════════════

# --- MPU-6050 -------------------------------------------------------------
# TDK InvenSense, *MPU-6000/MPU-6050 Product Specification*, PS-MPU-6000A-00
# Rev. 3.4 (19/08/2013). Todas as linhas abaixo: VDD = 2,375–3,46 V,
# VLOGIC = 1,8 V ± 5% ou VDD, TA = 25 °C.

# §6.2, NOISE PERFORMANCE — "Power Spectral Density @10Hz, AFS_SEL=0 & ODR=1kHz".
# CONDIÇÃO: 10 Hz, fundo de escala ±2 g, taxa de saída 1 kHz. Valor TÍPICO.
MPU_RUIDO_UG_POR_RAIZ_HZ = 400.0

# §6.2, ACCELEROMETER SENSITIVITY — Sensitivity Scale Factor, em LSB/g.
MPU_LSB_POR_G = {2: 16384.0, 4: 8192.0, 8: 4096.0, 16: 2048.0}

# §6.2 — LOW PASS FILTER RESPONSE, faixa programável, em Hz.
MPU_DLPF_FAIXA_HZ = (5.0, 260.0)
# §6.2 — OUTPUT DATA RATE, faixa programável, em Hz.
MPU_ODR_FAIXA_HZ = (4.0, 1000.0)

# §6.4, VDD POWER SUPPLY — correntes de operação, em ampères.
MPU_I_GIRO_ACEL_DMP_A = 3.9e-3      # giroscópio + acelerômetro + DMP
MPU_I_GIRO_ACEL_A = 3.8e-3          # giroscópio + acelerômetro, DMP desligado
MPU_I_ACEL_SO_A = 500e-6            # só acelerômetro, DMP e giroscópio desligados
MPU_I_ACEL_BAIXO_CONSUMO_A = {      # "Accelerometer Low Power Mode Current"
    1.25: 10e-6,
    5.0: 20e-6,
    20.0: 60e-6,
    40.0: 110e-6,
}
MPU_I_OCIOSO_A = 5e-6               # "Full-Chip Idle Mode Supply Current"
MPU_I_VLOGIC_A = 100e-6             # VLOGIC REFERENCE VOLTAGE — Normal Operating Current

# §6.4 — "START-UP TIME FOR REGISTER READ/WRITE", em segundos (típ. / máx.).
MPU_PARTIDA_S = (20e-3, 100e-3)

# §6.6, Primary I2C I/O (SCL, SDA) — corrente de dreno em nível baixo.
MPU_IOL_A = 3e-3                    # IOL a VOL = 0,4 V
MPU_VOL_V = 0.4

# --- ESP32 ----------------------------------------------------------------
# Espressif, *ESP32 Series Datasheet*, Tabela 4-2 "Power consumption by
# power modes". CONDIÇÃO: a tabela é de consumo do CHIP, não do módulo nem
# da placa de desenvolvimento.
ESP32_I_MODEM_SLEEP_80MHZ_A = (20e-3, 31e-3)   # 80 MHz, dual-core
ESP32_I_MODEM_SLEEP_240MHZ_A = (30e-3, 68e-3)  # 240 MHz, dual-core
ESP32_I_LIGHT_SLEEP_A = 0.8e-3
ESP32_I_DEEP_SLEEP_RTC_A = 10e-6               # RTC timer + RTC memory
ESP32_I_DEEP_SLEEP_ULP_A = 150e-6              # ULP ligado
ESP32_I_HIBERNACAO_A = 5e-6                    # só RTC timer
ESP32_I_DESLIGADO_A = 1e-6                     # CHIP_PU em nível baixo

# ⚠️ NAO_CONFERIDO nesta sessão: a corrente de transmissão Wi-Fi está na
# Tabela 5-4 da mesma folha de dados, que a versão HTML publicada não
# reproduz. Entra no modelo como FAIXA PARAMÉTRICA declarada, não como
# número citado. Trocar por valor de folha de dados (ou medido) quando houver.
NAO_CONFERIDO_I_RF_A = (100e-3, 240e-3)

# ⚠️ NAO_CONFERIDO: consumo fixo da placa DevKit V1 (regulador linear
# AMS1117-3.3 + ponte USB-serial CP2102/CH340). É o parâmetro que decide o
# CALC-01 e é o que o `HW-02` precisa medir. Faixa usada só para a análise
# de sensibilidade.
NAO_CONFERIDO_I_PLACA_A = (1e-3, 20e-3)

# --- Projeto --------------------------------------------------------------
V_LOGICA_V = 3.3                    # `firmware/diagram.json`: imu1:VCC ← esp:3V3
R_PULLDOWN_OHM = 10_000.0           # BOM (`docs/HARDWARE.md`) e diagram.json (r1 = 10000)
EPOCA_S = 30.0                      # `DATA-02`, fechado
BANDA_FILTRO_HZ = 21.0              # `FW-06`: MPU6050_BAND_21_HZ nos três sketches
GRADE_COMUM_HZ = 32.0               # `ML-DATASETS-E-PLANO.md` §7, decisão 2
LIMIAR_MOVIMENTO_MS2 = 1.2          # `DATA-CONTRACT.md` §2.1 — PROVISÓRIO
GRAVIDADE_CONTRATO_MS2 = 9.81       # valor usado no firmware e no contrato
GRAVIDADE_PADRAO_MS2 = 9.80665      # `ml/src/features.py`, LIMIAR_P_FRAC_G
BYTES_POR_EPOCA = 32                # `firmware/nucleo/epoca.h`, travado por static_assert

# Resoluções de outros aparelhos, para o piso de ENMO comparado (§2.2).
Q_GENEACTIV_MG = 3.9                # ActivInsights, GENEActiv Product Information Sheet
Q_EMPATICA_MG = 1000.0 / 64.0       # E4: 8 bits da faixa ±2 g → 1/64 g


# ══════════════════════════════════════════════════════════════════════════
# CALC-02 — física do acelerômetro
# ══════════════════════════════════════════════════════════════════════════

def resolucao_mg_por_lsb(fundo_de_escala_g: int) -> float:
    """Passo de quantização, em mg/LSB, a partir do fator de escala da folha."""
    return 1000.0 / MPU_LSB_POR_G[fundo_de_escala_g]


def sigma_termico_mg(banda_hz: float) -> float:
    """Desvio-padrão do ruído térmico integrado numa banda, em mg.

    σ = densidade × √banda. Ruído branco: a densidade é constante na banda,
    então a integral da PSD é densidade²·B e a raiz é densidade·√B.
    """
    return MPU_RUIDO_UG_POR_RAIZ_HZ * math.sqrt(banda_hz) / 1000.0


def sigma_quantizacao_mg(q_mg: float) -> float:
    """Desvio-padrão de quantização uniforme: q/√12."""
    return q_mg / math.sqrt(12.0)


def nyquist_hz(banda_hz: float) -> float:
    return 2.0 * banda_hz


# ══════════════════════════════════════════════════════════════════════════
# CALC-03 — índice de atividade: piso de ENMO e o limiar
# ══════════════════════════════════════════════════════════════════════════

def piso_enmo_gaussiano_mg(sigma_mg: float) -> float:
    """E[max(δ,0)] para δ ~ N(0, σ²) — o retificador do ENMO vira viés.

    E[max(δ,0)] = ∫₀^∞ x·φ(x/σ)/σ dx = σ/√(2π).
    """
    return sigma_mg / math.sqrt(2.0 * math.pi)


def piso_enmo_uniforme_mg(q_mg: float) -> float:
    """E[max(δ,0)] para δ ~ U(−q/2, +q/2) — quantização com dither.

    E[max(δ,0)] = (1/q)·∫₀^{q/2} x dx = q/8.
    """
    return q_mg / 8.0


def k_implicado_pelo_limiar(limiar_ms2: float, sigma_mg: float) -> float:
    """Quantos σ de ruído cabem no limiar `|total − g| > limiar`.

    Converte σ de mg para m/s² com a gravidade padrão e divide.
    """
    sigma_ms2 = sigma_mg * 1e-3 * GRAVIDADE_PADRAO_MS2
    return limiar_ms2 / sigma_ms2


# ══════════════════════════════════════════════════════════════════════════
# CALC-04 — análise elétrica
# ══════════════════════════════════════════════════════════════════════════

def corrente_pulldown_a(v: float = V_LOGICA_V, r: float = R_PULLDOWN_OHM) -> float:
    """Corrente pelo pull-down COM O BOTÃO FECHADO. Aberto, é zero."""
    return v / r


def potencia_pulldown_w(v: float = V_LOGICA_V, r: float = R_PULLDOWN_OHM) -> float:
    return v * v / r


def pullup_minimo_ohm(v: float = V_LOGICA_V) -> float:
    """R mínimo do pull-up de I2C: o dreno tem de puxar a linha até VOL.

    R ≥ (V_DD − V_OL) / I_OL, com I_OL e V_OL da folha do escravo.
    """
    return (v - MPU_VOL_V) / MPU_IOL_A


def pullup_maximo_ohm(t_subida_s: float, c_barramento_f: float) -> float:
    """R máximo do pull-up, pelo tempo de subida RC do barramento.

    A especificação I2C mede t_r entre 0,3·V_DD e 0,7·V_DD. Para uma
    exponencial de constante RC, esse trecho vale ln(0,7/0,3)·RC =
    0,8473·RC, de onde R_máx = t_r / (0,8473·C_b).
    """
    return t_subida_s / (math.log(0.7 / 0.3) * c_barramento_f)


def corrente_pullup_linha_baixa_a(r_ohm: float, v: float = V_LOGICA_V) -> float:
    """Corrente que o pull-up entrega enquanto a linha está em nível baixo."""
    return (v - MPU_VOL_V) / r_ohm


# ══════════════════════════════════════════════════════════════════════════
# CALC-01 — energia e autonomia
# ══════════════════════════════════════════════════════════════════════════

def corrente_media_a(estados: list[tuple[str, float, float]]) -> float:
    """I_média = Σ(I_i·t_i) / Σ(t_i). `estados` = [(nome, I em A, t em s)]."""
    carga = sum(i * t for _, i, t in estados)
    tempo = sum(t for _, _, t in estados)
    return carga / tempo


def autonomia_h(capacidade_mah: float, i_media_a: float) -> float:
    """C/I. Ignora, de propósito, o efeito Peukert e o corte do protetor."""
    return (capacidade_mah / 1000.0) / i_media_a


def cenario_continuo(i_esp_a: float, i_rf_a: float, t_post_s: float,
                     posts_por_h: float, i_pullup_a: float,
                     i_placa_a: float) -> float:
    """Arquitetura do `envio-continuo.ino`: amostra sempre, rádio em rajada."""
    t_rf = posts_por_h * t_post_s
    t_resto = 3600.0 - t_rf
    i_sensor = MPU_I_ACEL_SO_A + MPU_I_VLOGIC_A
    return corrente_media_a([
        ("radio", i_rf_a + i_sensor + i_pullup_a + i_placa_a, t_rf),
        ("amostragem", i_esp_a + i_sensor + i_pullup_a + i_placa_a, t_resto),
    ])


def cenario_wom(i_esp_ativo_a: float, i_rf_a: float, t_post_s: float,
                despertares_por_h: float, t_acordado_s: float,
                i_placa_a: float) -> float:
    """Arquitetura do `sketch.ino`: Deep Sleep + despertar por movimento."""
    t_ativo = despertares_por_h * t_acordado_s
    t_rf = despertares_por_h * t_post_s
    t_sleep = 3600.0 - t_ativo - t_rf
    i_wom = MPU_I_ACEL_BAIXO_CONSUMO_A[20.0]
    return corrente_media_a([
        ("radio", i_rf_a + i_wom + i_placa_a, t_rf),
        ("ativo", i_esp_ativo_a + MPU_I_ACEL_SO_A + i_placa_a, t_ativo),
        ("sleep", ESP32_I_DEEP_SLEEP_RTC_A + i_wom + i_placa_a, t_sleep),
    ])


# ══════════════════════════════════════════════════════════════════════════
# Relatório
# ══════════════════════════════════════════════════════════════════════════

def _t(titulo: str) -> None:
    print(f"\n{titulo}\n{'─' * len(titulo)}")


def relatorio() -> None:
    print("MODELOS QUANTITATIVOS DO TCC — CALC-01 a CALC-04")
    print("=" * 74)
    print("Reproduz docs/CALCULOS-TCC.md. Valores marcados [PARÂM] não vêm de")
    print("folha de dados conferida: são faixas declaradas, a medir.")

    # ---------------- CALC-02 ----------------
    _t("CALC-02 · resolução (folha de dados, §6.2)")
    for fs in (2, 4, 8, 16):
        q = resolucao_mg_por_lsb(fs)
        print(f"  ±{fs:>2} g → {MPU_LSB_POR_G[fs]:>8.0f} LSB/g → "
              f"{q:7.4f} mg/LSB = {q * 1e-3 * GRAVIDADE_PADRAO_MS2 * 1e3:6.3f} mm/s²")

    _t("CALC-02 · ruído por banda (400 µg/√Hz @10 Hz, ±2 g, ODR 1 kHz)")
    for banda in (16.0, 21.0, 44.0, 94.0, 184.0, 260.0):
        s = sigma_termico_mg(banda)
        print(f"  B = {banda:6.1f} Hz → σ = {s:6.3f} mg   "
              f"(Nyquist: f_s ≥ {nyquist_hz(banda):6.1f} Hz)")

    s21 = sigma_termico_mg(BANDA_FILTRO_HZ)
    s260 = sigma_termico_mg(MPU_DLPF_FAIXA_HZ[1])
    print(f"\n  razão 260 Hz / 21 Hz = {s260 / s21:.3f}×  (= √(260/21) = "
          f"{math.sqrt(260 / 21):.3f})")

    _t("CALC-02 · quantização é desprezível diante do térmico")
    for fs in (2, 8):
        q = resolucao_mg_por_lsb(fs)
        sq = sigma_quantizacao_mg(q)
        print(f"  ±{fs:>2} g: q = {q:6.4f} mg → σ_q = q/√12 = {sq:6.4f} mg "
              f"→ σ_térmico/σ_q = {s21 / sq:6.1f}×")

    _t("CALC-02 · amostragem")
    print(f"  filtro {BANDA_FILTRO_HZ:.0f} Hz → Nyquist f_s ≥ "
          f"{nyquist_hz(BANDA_FILTRO_HZ):.0f} Hz  (é o `FW-05`)")
    print(f"  grade comum do ML = {GRADE_COMUM_HZ:.0f} Hz → banda efetiva "
          f"{GRADE_COMUM_HZ / 2:.0f} Hz")
    corte_ml = 0.8 * GRADE_COMUM_HZ / 2  # ml/src/sinal.py, corte_frac_nyquist=0.8
    print(f"  corte anti-aliasing do ml/src/sinal.py: 0,8 × Nyquist = "
          f"{corte_ml:.1f} Hz")
    print(f"  ⚠️ banda do firmware ({BANDA_FILTRO_HZ:.0f} Hz) > banda do ml/ "
          f"({corte_ml:.1f} Hz): o FW-05 precisa fechar essa margem")
    print(f"  amostras por época de {EPOCA_S:.0f} s a "
          f"{nyquist_hz(BANDA_FILTRO_HZ):.0f} Hz: "
          f"{nyquist_hz(BANDA_FILTRO_HZ) * EPOCA_S:.0f}")
    print(f"  a {GRADE_COMUM_HZ:.0f} Hz (grade comum): "
          f"{GRADE_COMUM_HZ * EPOCA_S:.0f}")

    # ---------------- CALC-03 ----------------
    _t("CALC-03 · piso de ENMO imposto pelo ruído (confere §2.2)")
    s16 = sigma_termico_mg(GRADE_COMUM_HZ / 2)
    print(f"  MPU6050    σ = {s16:5.3f} mg (térmico, B = 16 Hz) → "
          f"piso = σ/√(2π) = {piso_enmo_gaussiano_mg(s16):5.3f} mg")
    sq_gen = sigma_quantizacao_mg(Q_GENEACTIV_MG)
    print(f"  GENEActiv  σ = {sq_gen:5.3f} mg (quantização, q = "
          f"{Q_GENEACTIV_MG:.2f} mg) → piso ≥ q/8 = "
          f"{piso_enmo_uniforme_mg(Q_GENEACTIV_MG):5.3f} mg")
    sq_e4 = sigma_quantizacao_mg(Q_EMPATICA_MG)
    print(f"  Empatica E4 σ = {sq_e4:5.3f} mg (quantização, q = "
          f"{Q_EMPATICA_MG:.3f} mg) → piso ≥ q/8 = "
          f"{piso_enmo_uniforme_mg(Q_EMPATICA_MG):5.3f} mg")
    print(f"\n  razão E4 / MPU6050 = "
          f"{piso_enmo_uniforme_mg(Q_EMPATICA_MG) / piso_enmo_gaussiano_mg(s16):.2f}×")
    print(f"  critério do CAL-01 no ROADMAP: 0,02 m/s² = "
          f"{0.02 / GRAVIDADE_PADRAO_MS2 * 1000:.2f} mg  vs  σ(21 Hz) = "
          f"{s21:.2f} mg")

    _t("CALC-03 · o limiar `g ± k·σ` NÃO gera o limiar em uso")
    k = k_implicado_pelo_limiar(LIMIAR_MOVIMENTO_MS2, s21)
    print(f"  limiar do contrato: |total − {GRAVIDADE_CONTRATO_MS2}| > "
          f"{LIMIAR_MOVIMENTO_MS2} m/s²")
    print(f"  σ(21 Hz) = {s21:.3f} mg = "
          f"{s21 * 1e-3 * GRAVIDADE_PADRAO_MS2:.5f} m/s²")
    print(f"  ⇒ k implicado = {k:.1f} σ   (um limiar de ruído usaria k ≈ 3–5)")
    print(f"  em g: {LIMIAR_MOVIMENTO_MS2 / GRAVIDADE_PADRAO_MS2:.5f} g  "
          f"(= LIMIAR_P_FRAC_G de ml/src/features.py)")

    # ---------------- CALC-04 ----------------
    _t("CALC-04 · pull-down de 10 kΩ (só com o botão FECHADO)")
    print(f"  I = V/R = {V_LOGICA_V}/{R_PULLDOWN_OHM:.0f} = "
          f"{corrente_pulldown_a() * 1e3:.3f} mA")
    print(f"  P = V²/R = {potencia_pulldown_w() * 1e3:.3f} mW")
    print("  ⚠️ é PICO, não média: com o botão aberto o ramo não conduz.")

    _t("CALC-04 · pull-ups do I2C — a janela de R que funciona")
    r_min = pullup_minimo_ohm()
    print(f"  R_mín = (V_DD − V_OL)/I_OL = ({V_LOGICA_V} − {MPU_VOL_V})/"
          f"{MPU_IOL_A * 1e3:.0f} mA = {r_min:.0f} Ω")
    for cb_pf, modo, tr_ns in ((50, "100 kHz", 1000), (100, "100 kHz", 1000),
                               (50, "400 kHz", 300), (100, "400 kHz", 300),
                               (200, "400 kHz", 300)):
        r_max = pullup_maximo_ohm(tr_ns * 1e-9, cb_pf * 1e-12)
        print(f"  C_b = {cb_pf:3d} pF, {modo} (t_r ≤ {tr_ns:4d} ns) → "
              f"R_máx = {r_max / 1000:6.2f} kΩ")
    print("\n  corrente enquanto a linha está baixa:")
    for r in (2200.0, 4700.0, 10000.0):
        i = corrente_pullup_linha_baixa_a(r)
        print(f"    R = {r / 1000:4.1f} kΩ → {i * 1e3:5.3f} mA por linha, "
              f"{2 * i * 1e3:5.3f} mA nas duas")

    # ---------------- CALC-01 ----------------
    _t("CALC-01 · por que não dá para dormir entre amostras")
    f_s = nyquist_hz(BANDA_FILTRO_HZ)
    print(f"  período entre amostras a {f_s:.0f} Hz = {1000 / f_s:.2f} ms")
    print(f"  partida do MPU6050 (§6.4): {MPU_PARTIDA_S[0] * 1e3:.0f} ms típ., "
          f"{MPU_PARTIDA_S[1] * 1e3:.0f} ms máx.")
    print("  ⇒ o tempo de partida do sensor é da ordem do período de "
          "amostragem, ou maior:")
    print("    desligar o sensor entre amostras é aritmeticamente impossível.")

    _t("CALC-01 · a amostragem do ML proíbe o modo de baixo consumo do sensor")
    for hz, i in sorted(MPU_I_ACEL_BAIXO_CONSUMO_A.items()):
        marca = "  ← teto do modo" if hz == 40.0 else ""
        print(f"  baixo consumo a {hz:5.2f} Hz: {i * 1e6:6.1f} µA{marca}")
    print(f"  FW-05 exige f_s ≥ {f_s:.0f} Hz > 40 Hz ⇒ modo normal: "
          f"{MPU_I_ACEL_SO_A * 1e6:.0f} µA")
    print(f"  custo do Nyquist: {MPU_I_ACEL_SO_A / MPU_I_ACEL_BAIXO_CONSUMO_A[40.0]:.2f}× "
          f"na corrente do sensor")

    _t("CALC-01 · I_média e autonomia — CHIP sozinho (piso teórico)")
    posts_h = 3600.0 / EPOCA_S
    print(f"  {posts_h:.0f} POSTs/h (uma época por POST, sem API-03)  "
          f"[PARÂM] t_post ∈ [0,5; 2,0] s, I_rf ∈ "
          f"[{NAO_CONFERIDO_I_RF_A[0] * 1e3:.0f}; "
          f"{NAO_CONFERIDO_I_RF_A[1] * 1e3:.0f}] mA")
    for t_post in (0.5, 2.0):
        for i_rf in NAO_CONFERIDO_I_RF_A:
            for i_esp in ESP32_I_MODEM_SLEEP_80MHZ_A:
                im = cenario_continuo(i_esp, i_rf, t_post, posts_h,
                                      2 * corrente_pullup_linha_baixa_a(4700.0) * 0.5,
                                      0.0)
                print(f"    t_post={t_post:.1f}s I_rf={i_rf * 1e3:3.0f}mA "
                      f"I_esp={i_esp * 1e3:2.0f}mA → I_méd = {im * 1e3:6.2f} mA "
                      f"→ {autonomia_h(2000, im):5.1f} h com 2000 mAh")

    _t("CALC-01 · o que a placa faz com isso  [PARÂM: I_placa]")
    i_ref = cenario_continuo(ESP32_I_MODEM_SLEEP_80MHZ_A[0],
                             NAO_CONFERIDO_I_RF_A[0], 1.0, posts_h,
                             2 * corrente_pullup_linha_baixa_a(4700.0) * 0.5, 0.0)
    i_wom = cenario_wom(ESP32_I_MODEM_SLEEP_80MHZ_A[0],
                        NAO_CONFERIDO_I_RF_A[0], 1.0, 60.0, 0.5, 0.0)
    print(f"  contínuo (FW-07) sem placa : {i_ref * 1e3:7.3f} mA")
    print(f"  Wake-on-Motion   sem placa : {i_wom * 1e3:7.3f} mA  "
          f"→ {i_ref / i_wom:6.1f}× melhor")
    print("\n  com o consumo fixo da placa somado:")
    for i_placa in (0.0, 100e-6, 1e-3, 5e-3, 10e-3, 20e-3):
        a, b = i_ref + i_placa, i_wom + i_placa
        print(f"    I_placa = {i_placa * 1e3:6.2f} mA → contínuo "
              f"{a * 1e3:7.3f} mA | WOM {b * 1e3:7.3f} mA | ganho "
              f"{a / b:6.2f}×  | autonomia WOM (2000 mAh) "
              f"{autonomia_h(2000, b):6.1f} h")
    # Ganho(p) = (I_cont + p)/(I_wom + p). Resolvendo Ganho(p) = G:
    #     p = (I_cont − G·I_wom) / (G − 1)
    for g in (10.0, 5.0, 2.0):
        p = (i_ref - g * i_wom) / (g - 1.0)
        print(f"\n  para o ganho do Deep Sleep cair a {g:4.1f}×, basta "
              f"I_placa = {p * 1e3:6.2f} mA")
    print("\n  É I_placa que o HW-02 precisa MEDIR: ela não muda o SINAL do "
          "ganho,")
    print("  mas comprime a ordem de grandeza que a folha de dados do chip "
          "promete.")
    print(f"  Repartição do cenário WOM sem placa ({i_wom * 1e3:.3f} mA): o "
          "rádio responde por")
    i_wom_sem_radio = cenario_wom(ESP32_I_MODEM_SLEEP_80MHZ_A[0], 0.0, 1.0,
                                  60.0, 0.5, 0.0)
    print(f"  {(i_wom - i_wom_sem_radio) / i_wom * 100:.0f}% dela ⇒ o item que "
          "move a autonomia é o API-03 (lote), não o modo de sono.")

    _t("CALC-01 · buffer — recuperado de firmware/nucleo (MEDIDO, não estimado)")
    for bytes_, epocas, nome in ((4096, 128, "RTC (Deep Sleep)"),
                                 (6144, 192, "RTC folgado"),
                                 (32768, 1024, "heap (envio-continuo)"),
                                 (131072, 4096, "heap generoso")):
        assert bytes_ // BYTES_POR_EPOCA == epocas, (bytes_, epocas)
        print(f"  {nome:<22} {bytes_:>6} B / {BYTES_POR_EPOCA} B = "
              f"{epocas:>4} épocas → {epocas * EPOCA_S / 3600:6.2f} h em "
              f"resolução cheia")
    print("  (a coluna degradada sai de `make capacidade`, não daqui: ela é "
          "simulação do buffer real)")


# ══════════════════════════════════════════════════════════════════════════
# Asserções — travam os números já publicados em outros documentos
# ══════════════════════════════════════════════════════════════════════════

def conferir() -> int:
    falhas: list[str] = []

    def eq(rotulo: str, obtido: float, esperado: float, tol: float,
           fonte: str) -> None:
        if abs(obtido - esperado) > tol:
            falhas.append(f"{rotulo}: obtido {obtido!r}, documento diz "
                          f"{esperado!r} ({fonte})")

    # docs/ML-DATASETS-E-PLANO.md §2.1 e docs/SINTESE §116
    eq("resolução ±8 g", resolucao_mg_por_lsb(8), 0.244, 0.0005,
       "ML-DATASETS §2.1: 0,244 mg/LSB")
    eq("resolução ±2 g", resolucao_mg_por_lsb(2), 0.061, 0.0005,
       "folha §6.2: 16384 LSB/g")

    # docs/ML-DATASETS-E-PLANO.md §2.2 — a tabela do piso de ENMO
    eq("σ MPU 16 Hz", sigma_termico_mg(16.0), 1.6, 0.01, "§2.2: 1,6 mg")
    eq("piso ENMO MPU", piso_enmo_gaussiano_mg(sigma_termico_mg(16.0)), 0.64,
       0.005, "§2.2: ≈ 0,64 mg")
    eq("σ_q GENEActiv", sigma_quantizacao_mg(Q_GENEACTIV_MG), 1.13, 0.005,
       "§2.2: 1,13 mg")
    eq("piso ENMO GENEActiv", piso_enmo_uniforme_mg(Q_GENEACTIV_MG), 0.49,
       0.005, "§2.2: ≥ 0,49 mg")
    # §2.2 arredonda 4,5105… para "4,5"; a tolerância acomoda o arredondamento.
    eq("σ_q E4", sigma_quantizacao_mg(Q_EMPATICA_MG), 4.5, 0.02, "§2.2: 4,5 mg")
    eq("piso ENMO E4", piso_enmo_uniforme_mg(Q_EMPATICA_MG), 1.95, 0.005,
       "§2.2: ≥ 1,95 mg")
    eq("σ MPU 21 Hz", sigma_termico_mg(21.0), 1.8, 0.04,
       "§2.2: 400 µg/√Hz × √21 = 1,8 mg")
    eq("resolução E4", Q_EMPATICA_MG, 15.6, 0.03, "§2.1: 15,6 mg/LSB")

    # docs/BACKLOG-COMPLETO.md, CALC-04
    eq("pull-down I", corrente_pulldown_a() * 1e3, 0.33, 0.005,
       "BACKLOG CALC-04: ≈ 0,33 mA")
    eq("pull-down P", potencia_pulldown_w() * 1e3, 1.1, 0.02,
       "BACKLOG CALC-04: ≈ 1,1 mW")

    # ml/src/features.py — LIMIAR_P_FRAC_G
    eq("limiar em g", LIMIAR_MOVIMENTO_MS2 / GRAVIDADE_PADRAO_MS2, 0.1224,
       0.0002, "features.py: 1,2/9,80665 ≈ 0,1224 g")

    # firmware/nucleo/README.md — capacidade MEDIDA
    eq("buffer 1024 épocas", 1024 * EPOCA_S / 3600.0, 8.53, 0.01,
       "nucleo/README.md: 8,53 h")
    eq("buffer 128 épocas", 128 * EPOCA_S / 3600.0, 1.07, 0.01,
       "nucleo/README.md: 1,07 h")
    eq("buffer 192 épocas", 192 * EPOCA_S / 3600.0, 1.60, 0.01,
       "nucleo/README.md: 1,60 h")
    eq("POSTs em 8 h", 8 * 3600.0 / EPOCA_S, 960.0, 0.5,
       "nucleo/README.md: 960 POSTs")

    # ML-DATASETS §0.2 — a identidade da acurácia, nos dois estudos
    def p_implicado(acc: float, sens: float, esp: float) -> float:
        return (acc - esp) / (sens - esp)

    eq("p implicado Li 2025", p_implicado(0.873, 0.948, 0.331), 0.878, 0.0005,
       "§0.2 / RESULTADOS Y.1.3: 0,878")
    eq("p implicado Walch 2019", p_implicado(0.900, 0.930, 0.596), 0.910,
       0.0005, "§0.2 / RESULTADOS Y.1.3: 0,910")

    if falhas:
        print("DIVERGÊNCIAS (o documento manda até prova em contrário):")
        for f in falhas:
            print(f"  ✗ {f}")
        return 1
    print("✓ todas as asserções batem com o que já estava escrito nos documentos.")
    return 0


def main() -> int:
    # A saída usa ✓, ĝ, σ e outros fora do cp1252: no console do Windows o
    # `print` morria com UnicodeEncodeError — no `--conferir`, DEPOIS de as
    # asserções baterem, e o exit 1 parecia reprovação (DOCS-WIN-02).
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--conferir", action="store_true",
                    help="só as asserções contra os documentos")
    args = ap.parse_args()
    if args.conferir:
        return conferir()
    relatorio()
    print()
    return conferir()


if __name__ == "__main__":
    sys.exit(main())
