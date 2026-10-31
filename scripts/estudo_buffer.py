#!/usr/bin/env python3
"""Reproduz os números de `docs/DECISAO-BUFFER-E-FEATURES.md`.

    python3 scripts/estudo_buffer.py            # imprime o estudo inteiro
    python3 scripts/estudo_buffer.py --conferir # só as asserções; sai != 0 se divergir

Mesma convenção de `scripts/calculos_tcc.py`: só biblioteca padrão, e cada
constante traz fonte e condição. Onde o valor não pôde ser conferido na folha
de dados, está marcado `NAO_CONFERIDO` e entra como **parâmetro em faixa**, com
análise de sensibilidade — nunca como número citado.

O custo em kappa da quantização NÃO é calculado aqui: ele é **medido** sobre as
bases reais por `ml/experimentos/quantizacao_features.py`, e os valores que este
script confere são os que aquele produziu.
"""

from __future__ import annotations

import argparse
import sys

# ══════════════════════════════════════════════════════════════════════════
# CONSTANTES — cada uma com fonte
# ══════════════════════════════════════════════════════════════════════════

# --- Época ----------------------------------------------------------------
# `ml/config.yaml` e `firmware/nucleo/epoca.h` (DURACAO_EPOCA_BASE_S).
EPOCA_S = 30.0
REGISTROS_POR_MINUTO = 60.0 / EPOCA_S          # = 2, como o enunciado supunha

# Horas de operação por dia. O aparelho é de uso noturno: não grava 24 h.
# Todo número de desgaste abaixo é dado nas duas bases — 24 h/dia (o pior caso
# possível, que é contínuo) e 8 h/noite (o uso real) — porque a diferença é de
# um fator 3 e ela aparece justamente no cenário mais apertado.
HORAS_POR_DIA_CONTINUO = 24.0
HORAS_POR_NOITE_REAL = 8.0

# --- Microcontrolador e memória -------------------------------------------
# Espressif, *ESP32-WROOM-32 Datasheet* v2.4, §1 (Mouser 891/esp-wroom-32).
# O módulo do DevKit V1 e o do `board-esp32-devkit-c-v4` do Wokwi são ambos
# WROOM-32: 4 MiB de flash SPI, 520 KiB de SRAM interna, **sem PSRAM**.
FLASH_TOTAL_B = 4 * 1024 * 1024
TEM_PSRAM = False

# Arduino-ESP32, `tools/partitions/default.csv`: esquema padrão de 4 MB =
# duas fatias de OTA de 1,25 MiB + a área de dados (`spiffs`) + coredump.
# ✏️ 31/10 (FW-08): conferido no arquivo do `arduino-esp32` (ramo master), a
# área de dados é **0x160000 = 1 408 KiB**. Este script usava 1 536 KiB
# (1,5 MiB), número nunca conferido, que superestimava a partição em 9 %.
PARTICAO_DADOS_PADRAO_B = 0x160000
# A tabela que o projeto adotou e versiona desde 31/10: `firmware/partitions.csv`,
# sem OTA, com a partição `dormio` de 2 MiB. Até então este número era uma
# hipótese de ~2,8 MB; `make capacidade` mede a cobertura sobre a tabela real.
PARTICAO_DADOS_SOB_MEDIDA_B = 0x200000

# Orçamentos de RAM, de `firmware/nucleo/capacidade.cpp`.
RTC_SLOW_B = 4096
HEAP_CONSERVADOR_B = 32768

# --- Flash: geometria e desgaste -------------------------------------------
# Winbond, *W25Q32JV Datasheet* Rev. G: 256 B por página programável,
# 4 KiB por setor de apagamento.
PAGINA_B = 256
SETOR_B = 4096
# Endurance: Espressif e a literatura de flash NOR dão 10 000 a 100 000 ciclos
# de programa/apagamento por setor. Usamos 100 000 (valor nominal do W25Q32JV)
# e mostramos que a conclusão não muda com 10 000.
CICLOS_PE = 100_000
CICLOS_PE_PESSIMISTA = 10_000

# Tempo de apagamento de setor: 400 ms (W25Q32JV, tempo máximo de 4 KiB).
T_APAGAR_SETOR_MS = 400.0
# Tempo de programação de página: 0,7 ms típico.
T_PROGRAMAR_PAGINA_MS = 0.7

# ⚠️ NAO_CONFERIDO — a corrente durante programação/apagamento não aparece de
# forma inequívoca na folha que foi possível consultar (a folha dá 4 mA de
# corrente ativa de leitura e 1 µA em repouso). Entra como PARÂMETRO EM FAIXA,
# exatamente como a corrente de rádio no CALC-01 (ver nota 🔧 3 daquele texto).
FAIXA_I_ESCRITA_FLASH_MA = (4.0, 10.0, 20.0)

# --- Energia de referência -------------------------------------------------
# `docs/CALCULOS-TCC.md` Z.4.4: arquitetura de amostragem contínua por época,
# só circuitos integrados, rádio arbitrado em 100 mA e 1 s por época.
I_MEDIA_CONTINUA_MA = 23.9
# A mesma seção: uma transmissão de 1 s a 100 mA, uma vez por época de 30 s.
I_RADIO_MA = 100.0
T_RADIO_S = 1.0

# --- Piso de ruído ---------------------------------------------------------
# `docs/ML-DATASETS-E-PLANO.md` §2.2, tabela de pisos do ENMO.
PISO_ENMO_MPU6050_G = 0.00064          # 0,64 mg
SIGMA_POR_AMOSTRA_MPU6050_G = 0.0016   # 1,6 mg

# --- Layouts de registro ---------------------------------------------------
LAYOUTS: dict[str, list[tuple[str, int]]] = {
    "A. hoje, sem features": [
        ("índice u32", 4), ("pico total+ax/ay/az+temp, 5×f32", 20),
        ("amostras/esperadas/duração, 3×u16", 6), ("nível+flags", 2),
    ],
    "B. ingênuo: 8 features f32": [
        ("layout A", 32), ("8 features float32", 32),
    ],
    "C. ĝ em float: 6 features + ĝ": [
        ("layout A", 32), ("6 features float32", 24), ("ĝ, 3×float32", 12),
    ],
    "D. quantizado (proposto)": [
        ("índice u32", 4), ("6 features u16", 12), ("ĝ, 3×i16", 6),
        ("pico total u16", 2), ("pico ax/ay/az, 3×i16", 6), ("temp i16", 2),
        ("amostras/esperadas, 2×u16", 4), ("duração u16", 2), ("nível+flags", 2),
    ],
}

# --- Escalas do ponto fixo -------------------------------------------------
# Fundo de escala por feature. Os máximos observados saem das três bases
# (Wearanize+ cabeça/pulso e Newcastle) — ver o experimento de quantização.
ESCALAS_U16 = {
    # feature:         (fundo de escala, unidade, máximo observado nas bases)
    "enmo_media":      (1.0,   "g",     0.2394),
    "enmo_desvio":     (1.0,   "g",     0.5467),
    "enmo_max":        (16.0,  "g",     6.4434),
    "mag_din_media":   (2.0,   "g",     0.8596),
    "inclinacao_rel":  (180.0, "graus", 179.3015),
    "d_angulo":        (180.0, "graus", 175.6912),
}

# --- Resultados MEDIDOS pelo experimento de quantização --------------------
# `ml/experimentos/quantizacao_features.py`, 10 dobras agrupadas por sujeito,
# normalização por sujeito + contexto ±2 + regressão logística balanceada.
# Diferença PAREADA por dobra contra float64.
DKAPPA_U16 = {           # (Δκ médio, max |Δκ|)
    "wearanize/pulso":  (-0.00008, 0.00081),
    "wearanize/cabeça": (-0.00003, 0.00204),
    "newcastle":        (+0.00005, 0.00160),
}
DKAPPA_U8 = {
    "wearanize/pulso":  (+0.00027, 0.01837),
    "wearanize/cabeça": (-0.03802, 0.07469),
    "newcastle":        (-0.01068, 0.10817),
}
# Referências de escala para ler os Δκ acima.
KAPPA_TETO_INTERAVALIADOR = 0.612   # ML-05, os 90 sujeitos comuns
GANHO_HMM = 0.123                   # ML-03b item 8b


def tamanho(nome: str) -> int:
    return sum(b for _, b in LAYOUTS[nome])


# ══════════════════════════════════════════════════════════════════════════
# SEÇÕES
# ══════════════════════════════════════════════════════════════════════════

def secao_layouts() -> None:
    print("=" * 78)
    print("1. LAYOUTS DE REGISTRO DE ÉPOCA")
    print("=" * 78)
    for nome in LAYOUTS:
        t = tamanho(nome)
        campos = ", ".join(f"{n} {b} B" for n, b in LAYOUTS[nome])
        print(f"  {nome:32s} {t:3d} B")
        print(f"  {'':32s}     ({campos})")
    print()
    print("  Autonomia em RAM, resolução PLENA de 30 s (sem degradar uma vez):")
    print(f"  {'layout':32s} {'4 KiB RTC':>20s} {'32 KiB heap':>22s}")
    for nome in LAYOUTS:
        t = tamanho(nome)
        n_rtc, n_heap = RTC_SLOW_B // t, HEAP_CONSERVADOR_B // t
        print(f"  {nome:32s} {n_rtc:5d} ép = {n_rtc*EPOCA_S/3600:5.2f} h"
              f" {n_heap:7d} ép = {n_heap*EPOCA_S/3600:6.2f} h")
    print()


def secao_flash() -> None:
    print("=" * 78)
    print("2. FLASH — QUANTO CABE")
    print("=" * 78)
    print(f"  ESP32-WROOM-32: {FLASH_TOTAL_B//1024//1024} MiB de flash SPI, "
          f"{'sem' if not TEM_PSRAM else 'com'} PSRAM.")
    print(f"  Partição de dados no esquema PADRÃO do Arduino-ESP32 (4 MB): "
          f"{PARTICAO_DADOS_PADRAO_B/1024/1024:.1f} MiB.")
    print(f"  Tabela sob medida, sem OTA: {PARTICAO_DADOS_SOB_MEDIDA_B/1024/1024:.1f} MiB.")
    print("  Desde 31/10 o repositório versiona firmware/partitions.csv (FW-08), a sob medida.")
    print()
    for rotulo, area in [("partição padrão", PARTICAO_DADOS_PADRAO_B),
                         ("tabela sob medida, sem OTA", PARTICAO_DADOS_SOB_MEDIDA_B)]:
        print(f"  {rotulo} ({area/1024/1024:.1f} MiB):")
        for nome in LAYOUTS:
            t = tamanho(nome)
            n = area // t
            h = n * EPOCA_S / 3600
            print(f"     {nome:32s} {n:7d} ép = {h:8.1f} h = {h/24:5.1f} dias")
        print()


def secao_desgaste() -> None:
    print("=" * 78)
    print("3. DESGASTE DA FLASH")
    print("=" * 78)
    print(f"  Taxa de escrita: {REGISTROS_POR_MINUTO:.0f} registros por minuto.")
    print()
    for nome in ("D. quantizado (proposto)", "B. ingênuo: 8 features f32"):
        t = tamanho(nome)
        b_dia = t * REGISTROS_POR_MINUTO * 60 * 24
        reg_por_setor = SETOR_B // t
        apagamentos_dia = REGISTROS_POR_MINUTO * 60 * 24 / reg_por_setor
        print(f"  {nome} — {t} B por época")
        print(f"     escrita: {b_dia/1024:.0f} KiB/dia = {b_dia*365/1024/1024:.1f} MiB/ano")
        for rotulo, area in [("padrão 1,4 MiB", PARTICAO_DADOS_PADRAO_B),
                             ("sob medida 2,0 MiB", PARTICAO_DADOS_SOB_MEDIDA_B)]:
            for ciclos, tag in [(CICLOS_PE, "100k ciclos"), (CICLOS_PE_PESSIMISTA, " 10k ciclos")]:
                anos = area * ciclos / b_dia / 365
                print(f"     {rotulo:20s} {tag}: orçamento {area*ciclos/1024**3:6.1f} GiB "
                      f"-> {anos:10,.0f} anos com nivelamento")
        print(f"     append SEM nivelamento nenhum: {reg_por_setor} registros por setor"
              f" -> {apagamentos_dia:.1f} apagamentos/dia em operação contínua")
        for ciclos, tag in [(CICLOS_PE, "100k ciclos"), (CICLOS_PE_PESSIMISTA, " 10k ciclos")]:
            anos_24 = ciclos / apagamentos_dia / 365
            anos_8 = anos_24 * HORAS_POR_DIA_CONTINUO / HORAS_POR_NOITE_REAL
            print(f"       {tag}: {anos_24:6.1f} anos a 24 h/dia"
                  f"  |  {anos_8:6.1f} anos a {HORAS_POR_NOITE_REAL:.0f} h/noite (uso real)")
        print()
    print("  Leitura: a taxa de 2 registros/min é irrisória para endurance, como o")
    print("  enunciado supunha. A ÚNICA célula apertada do quadro é o cruzamento de")
    print("  três pessimismos simultâneos — 10 000 ciclos, zero nivelamento e operação")
    print("  24 h/dia — e ela dá ~1 ano. Basta desfazer QUALQUER um dos três para a")
    print("  vida útil passar de uma década; e LittleFS e NVS fazem nivelamento por")
    print("  padrão, então o cenário sem nivelamento não é o que se vai construir.")
    print()


def secao_energia() -> None:
    print("=" * 78)
    print("4. ENERGIA DA ESCRITA EM FLASH")
    print("=" * 78)
    print(f"  Referência (CALC-01, Z.4.4): amostragem contínua = {I_MEDIA_CONTINUA_MA} mA médios.")
    print("  A extração das 8 features OBRIGA essa arquitetura (Z.4.3): o vetor de")
    print("  características exige a época inteira amostrada, o que é incompatível")
    print("  com o despertar por movimento e com o modo de baixo consumo do sensor.")
    print()
    t = tamanho("D. quantizado (proposto)")
    reg_por_setor = SETOR_B // t
    for i_ma in FAIXA_I_ESCRITA_FLASH_MA:
        q_prog = i_ma * T_PROGRAMAR_PAGINA_MS / 1000.0
        q_apagar = i_ma * T_APAGAR_SETOR_MS / 1000.0 / reg_por_setor
        i_med = (q_prog + q_apagar) / EPOCA_S
        print(f"  I_escrita = {i_ma:4.1f} mA (parâmetro declarado): "
              f"programa {q_prog*1000:5.1f} µA·s + apagamento amortizado {q_apagar*1000:5.1f} µA·s"
              f"  ->  {i_med*1000:5.2f} µA médios = {i_med/I_MEDIA_CONTINUA_MA*100:.4f} %")
    i_radio_media = I_RADIO_MA * T_RADIO_S / EPOCA_S
    print()
    print(f"  Comparação: UMA transmissão por época ({I_RADIO_MA:.0f} mA por {T_RADIO_S:.0f} s)")
    print(f"  custa {i_radio_media:.2f} mA médios — mais de mil vezes a persistência.")
    print("  A conclusão do Z.4.4 (o rádio domina, agregar entregas é o que importa)")
    print("  não é alterada em nada por gravar em flash.")
    print()


def secao_quantizacao() -> None:
    print("=" * 78)
    print("5. QUANTIZAÇÃO — PASSO CONTRA O QUE O SENSOR DISTINGUE")
    print("=" * 78)
    print(f"  Piso do ENMO_media no MPU6050: {PISO_ENMO_MPU6050_G*1000:.2f} mg "
          f"(σ por amostra {SIGMA_POR_AMOSTRA_MPU6050_G*1000:.1f} mg) — ML-DATASETS §2.2.")
    print()
    for nome, (fundo, unidade, obs) in ESCALAS_U16.items():
        passo = fundo / 65535
        if unidade == "g":
            razao = PISO_ENMO_MPU6050_G / passo
            print(f"  {nome:16s} fundo {fundo:5.1f} g    passo {passo*1e6:7.1f} µg"
                  f"   = {razao:6.1f}× mais fino que o piso   (máx. observado {obs:.3f})")
        else:
            print(f"  {nome:16s} fundo {fundo:5.1f} graus passo {passo:9.5f} graus"
                  f"                            (máx. observado {obs:.3f})")
    print(f"  {'zcr, p_frac':16s} guardados como CONTAGEM inteira de amostras (0..959 em")
    print(f"  {'':16s} 960): cabem em u16 SEM PERDA NENHUMA, por construção.")
    print(f"  {'ĝ (3×i16)':16s} componente unitária em [-1,1], passo 3,05e-5")
    print(f"  {'':16s} -> resolução angular ~0,002 graus.")
    print()
    print("  ⚠️ `enmo_max` é o único com folga pequena (2,6× o piso), porque seu fundo")
    print("  de escala precisa cobrir 16 g. Mas ele é um MÁXIMO: o ruído relevante é o")
    print(f"  σ por amostra ({SIGMA_POR_AMOSTRA_MPU6050_G*1000:.1f} mg), e aí a folga é "
          f"{SIGMA_POR_AMOSTRA_MPU6050_G/(16.0/65535):.1f}×.")
    print()
    print("  CUSTO MEDIDO EM KAPPA (pareado por dobra, contra float64):")
    print(f"  {'base':20s} {'Δκ com u16':>22s} {'Δκ com u8':>22s}")
    for base in DKAPPA_U16:
        m16, x16 = DKAPPA_U16[base]
        m8, x8 = DKAPPA_U8[base]
        print(f"  {base:20s} {m16:+9.5f} (máx {x16:.5f}) {m8:+9.5f} (máx {x8:.5f})")
    print()
    print(f"  Escala de leitura: o teto entre pontuadores humanos é κ = {KAPPA_TETO_INTERAVALIADOR}")
    print(f"  (ML-05) e o ganho do HMM foi Δκ = +{GANHO_HMM} (ML-03b item 8b). O custo do")
    print(f"  u16 é ~{GANHO_HMM/max(abs(v[0]) for v in DKAPPA_U16.values()):,.0f}× menor que o "
          f"ganho do HMM. O do u8 já NÃO é desprezível na cabeça.")
    print()


def secao_redundancia() -> None:
    print("=" * 78)
    print("6. REDUNDÂNCIA ENTRE FEATURES")
    print("=" * 78)
    print("  `d_angulo` NÃO é a diferença de `inclinacao_rel` entre épocas vizinhas.")
    print("  Os dois são ângulos numa ESFERA, e o que vale é a desigualdade triangular")
    print("  esférica, não uma igualdade:")
    print()
    print("      | θ_t − θ_{t−1} |  ≤  d_angulo  ≤  θ_t + θ_{t−1}")
    print()
    print("  Medido nos 87 795 épocas do Wearanize+ (pulso): a aproximação")
    print("  d_angulo ≈ |Δinclinacao_rel| erra 0,010 grau na mediana — e até 149,4 graus")
    print("  no pior caso. O erro cresce monotonicamente com o tamanho da virada:")
    print("     d_angulo em [ 0,  1) graus — n=73 386 — erro médio  0,03 grau")
    print("     d_angulo em [ 5, 20) graus — n= 4 719 — erro médio  3,70 graus")
    print("     d_angulo em [60,180) graus — n= 1 252 — erro médio 31,10 graus")
    print()
    print("  Ou seja: a aproximação é ótima onde não há virada e falha exatamente")
    print("  nas 5,16 % de épocas que são viradas — que é tudo o que `d_angulo` existe")
    print("  para capturar. Ela não serve.")
    print()
    print("  O QUE SERVE: guardar ĝ (o vetor gravidade unitário da época) em vez dos")
    print("  dois ângulos. Ambos são funções de ĝ, e a reconstrução é EXATA")
    print("  (erro máximo medido: 0,000e+00 grau nas duas features).")
    print()
    print("  Efeito colateral que vale mais que os bytes: ĝ_ref é a mediana geométrica")
    print("  da gravação INTEIRA. Guardando ĝ, ela é calculável na drenagem, com o")
    print("  MESMO Weiszfeld do Python — em vez de um acumulador incremental que seria")
    print("  um estimador diferente e divergiria em silêncio.")
    print()


# ══════════════════════════════════════════════════════════════════════════
# CONFERÊNCIA
# ══════════════════════════════════════════════════════════════════════════

def conferir() -> int:
    falhas = []

    def checar(cond: bool, msg: str) -> None:
        if not cond:
            falhas.append(msg)

    checar(tamanho("A. hoje, sem features") == 32,
           "layout A deixou de ter 32 B — confira o static_assert de epoca.cpp")
    checar(tamanho("B. ingênuo: 8 features f32") == 64, "layout B != 64 B")
    checar(tamanho("D. quantizado (proposto)") == 40, "layout D != 40 B")

    # O layout D cabe em mais épocas de RTC do que o ingênuo, e em mais da
    # metade do que o layout de hoje.
    checar(RTC_SLOW_B // tamanho("D. quantizado (proposto)") == 102, "D no RTC != 102 épocas")
    checar(RTC_SLOW_B // tamanho("B. ingênuo: 8 features f32") == 64, "B no RTC != 64 épocas")

    # Flash: o layout proposto cobre mais de uma semana na partição padrão.
    horas = (PARTICAO_DADOS_PADRAO_B // tamanho("D. quantizado (proposto)")) * EPOCA_S / 3600
    checar(horas > 7 * 24, f"flash padrão cobre {horas:.0f} h, esperado > 168 h")

    # Desgaste. A célula mais apertada do quadro é o cruzamento dos três
    # pessimismos (10k ciclos + zero nivelamento + 24 h/dia). Ela fica em torno
    # de 1 ano; a asserção trava que ela NÃO caia abaixo de meio ano, e que o
    # cenário de uso real (8 h/noite) fique acima de dois anos mesmo assim.
    t = tamanho("D. quantizado (proposto)")
    apag_dia = REGISTROS_POR_MINUTO * 60 * 24 / (SETOR_B // t)
    anos_pior = CICLOS_PE_PESSIMISTA / apag_dia / 365
    checar(anos_pior > 0.5,
           f"pior caso triplo caiu para {anos_pior:.2f} anos, esperado > 0,5")
    anos_real = anos_pior * HORAS_POR_DIA_CONTINUO / HORAS_POR_NOITE_REAL
    checar(anos_real > 2.0,
           f"pior caso em uso real caiu para {anos_real:.2f} anos, esperado > 2")
    # E com nivelamento — que é o que LittleFS e NVS fazem — a folga é de ordens
    # de magnitude, em qualquer das duas hipóteses de endurance.
    b_dia = t * REGISTROS_POR_MINUTO * 60 * 24
    checar(PARTICAO_DADOS_PADRAO_B * CICLOS_PE_PESSIMISTA / b_dia / 365 > 100,
           "desgaste com nivelamento caiu abaixo de 100 anos")

    # Energia: a escrita em flash fica abaixo de 0,1 % do consumo de referência.
    i_max = max(FAIXA_I_ESCRITA_FLASH_MA)
    q = (i_max * T_PROGRAMAR_PAGINA_MS / 1000.0
         + i_max * T_APAGAR_SETOR_MS / 1000.0 / (SETOR_B // t)) / EPOCA_S
    checar(q / I_MEDIA_CONTINUA_MA < 0.001,
           f"escrita em flash subiu para {q/I_MEDIA_CONTINUA_MA*100:.3f} % do consumo")

    # Quantização: o passo do u16 é mais fino que o piso de ruído em todas as
    # features do domínio de g.
    for nome, (fundo, unidade, _) in ESCALAS_U16.items():
        if unidade != "g":
            continue
        passo = fundo / 65535
        ref = (SIGMA_POR_AMOSTRA_MPU6050_G if nome == "enmo_max" else PISO_ENMO_MPU6050_G)
        checar(passo < ref, f"passo de {nome} ({passo*1e6:.1f} µg) não é mais fino que {ref*1000:.2f} mg")

    # O custo medido do u16 é menor que 1 % do ganho do HMM em toda base.
    for base, (media, maximo) in DKAPPA_U16.items():
        checar(abs(media) < 0.01 * GANHO_HMM,
               f"Δκ do u16 em {base} ({media:+.5f}) passou de 1 % do ganho do HMM")
        checar(maximo < 0.01, f"máx |Δκ| do u16 em {base} = {maximo:.5f}, esperado < 0,01")

    # E o do u8 NÃO é desprezível em pelo menos uma base — é o que justifica
    # ficar em 16 bits em vez de 8.
    checar(any(abs(m) > 0.01 for m, _ in DKAPPA_U8.values()),
           "u8 deixou de custar nada — a escolha de 16 bits perdeu a justificativa")

    if falhas:
        print("CONFERÊNCIA FALHOU:")
        for f in falhas:
            print("  ✗", f)
        return 1
    print(f"conferência: {15 + len(DKAPPA_U16)*2} asserções, todas passaram.")
    return 0


def main() -> int:
    # A saída usa ✓, ĝ, σ e outros fora do cp1252: no console do Windows o
    # `print` morria com UnicodeEncodeError — no `--conferir`, DEPOIS de as
    # asserções baterem, e o exit 1 parecia reprovação (DOCS-WIN-02).
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--conferir", action="store_true", help="só as asserções")
    args = p.parse_args()

    if args.conferir:
        return conferir()

    print()
    print("ESTUDO DO BUFFER DE ÉPOCAS COM VETOR DE FEATURES")
    print("reproduz docs/DECISAO-BUFFER-E-FEATURES.md")
    print()
    secao_layouts()
    secao_flash()
    secao_desgaste()
    secao_energia()
    secao_quantizacao()
    secao_redundancia()
    return conferir()


if __name__ == "__main__":
    sys.exit(main())
