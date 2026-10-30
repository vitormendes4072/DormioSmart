"""Dourado da cadeia C2 (`FW-07`): da FIFO do MPU6050 à grade de 32 Hz.

É a terceira fronteira de paridade, e a que faltava para a arquitetura C2
(`ARQ-01`). As duas existentes (`test_vetor_dourado.py`) partem de 960 amostras
já na grade de 32 Hz. Esta parte de onde o sensor de fato entrega: inteiros de
16 bits saindo da FIFO a uma taxa que ninguém conhece de antemão.

=============================================================================
Por que este dourado confere contra DUAS referências
=============================================================================
Medido em 30/10 (50 sementes × 4 taxas × 2 épocas, `dourado_cadeia_c2.py`): o
que separa a cadeia do firmware do pipeline do `ml/` é **o instante de cada
amostra**. O pipeline conhece o tempo verdadeiro; o firmware o estima por
regressão sobre as drenagens, e erra até ~5 ms. Esse erro move `enmo_max` em
até 2,2e-3 g e `zcr` em até 8 cruzamentos — mais do que **cinco das seis
sabotagens** plausíveis movem as features. Uma tolerância larga o bastante para
o firmware correto passar deixaria todas elas passarem também.

Então são duas réguas, para duas perguntas:

  VALIDADE  — as features do firmware estão perto das do pipeline?
              Contra `esperado_pelo_pipeline`, tolerâncias derivadas entre o
              piso medido e o que mudaria uma decisão. Pega a ausência de
              anti-aliasing, e pouca coisa além.
  EXATIDÃO  — o firmware faz a conta que diz fazer?
              Contra `cadeia_estilo_firmware`, mesma aritmética em double:
              a linha do tempo bate em 1e-9 e a grade em 1e-4 g (o float32
              do ESP32). Pega as seis sabotagens com folga de 50× ou mais.

A régua de exatidão só faz sentido porque a de validade existe: ela prova que
o firmware implementa `cadeia_estilo_firmware`, e a de validade prova que
`cadeia_estilo_firmware` serve ao modelo.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

import numpy as np
import pytest

from dourado_cadeia_c2 import (
    AMOSTRAS_NA_GRADE, CORTE_ANTIALIASING_HZ, DURACAO_EPOCA_S, FOLGA_DO_AJUSTE_S,
    INTERVALO_DE_DRENAGEM_S, LSB_POR_G, MARGEM_S, MINIMO_DE_DRENAGENS,
    TAXA_DA_GRADE_HZ, TAXA_MAXIMA_FRAC, TAXA_MINIMA_FRAC, TAXA_NOMINAL_HZ,
    VARIACAO_DA_DRENAGEM_S, cadeia_estilo_firmware, esperado_pelo_pipeline,
    gerar_caso,
)
from src.configuracao import carregar_config
from src.features import FEATURES_DO_DISPOSITIVO
from test_vetor_dourado import REGRAVAR, _divergencias, features_estilo_firmware

RAIZ = Path(__file__).resolve().parents[1]
CAMINHO = RAIZ / "testes" / "vetor_dourado_cadeia_c2.json"

#: Um caso por taxa: os dois extremos do oscilador (−15 %, +10 %), o nominal
#: e um intermediário. Uma semente por taxa mantém o arquivo em ~300 KB.
CASOS = ((11, 42.5), (12, 47.0), (13, 50.0), (14, 55.0))

#: A grade é conferida de 8 em 8 amostras: 120 pontos × 3 eixos por época. Toda
#: sabotagem medida desloca a grade inteira, não pontos isolados.
PASSO_DA_GRADE_AMOSTRADA = 8


# =========================================================================
# TOLERÂNCIAS DE VALIDADE (firmware contra o pipeline do ml/)
# =========================================================================
# Piso medido em 30/10: 50 sementes × {42,5; 47; 50; 55} Hz × 2 épocas = 400
# épocas, firmware estilo Python contra `reamostrar` + `features_de_epoca` com
# o tempo verdadeiro. Inclui o resíduo de borda do filtro de gravidade, que já
# existia (`test_vetor_dourado.py`).
#
#   enmo_media, enmo_desvio  piso 2,2e-5 g   → 5e-5 g. Teto: o piso de ruído
#       do ENMO no MPU6050, 6,4e-4 g, fica 13× acima.
#   enmo_max                 piso 2,2e-3 g   → 5e-3 g. ⚠️ A maior das seis
#       contra o seu teto: é o máximo de 960 amostras, e o máximo é o que mais
#       sente o instante da amostra. Declarada, não escondida. O `ML-11` mediu
#       que `enmo_max` não está entre as três features que bastam ao kappa.
#   mag_din_media            piso 1,12 %     → 4 %, a mesma régua da fronteira A
#       (cujo piso, só do filtro de gravidade, é 1,43 %).
#   zcr                      piso 8 cruzamentos de 959 → 16. Também sente o
#       instante (a contagem é contra a média da janela). `ML-11`: dispensável.
#   p_frac                   piso 11 amostras de 960 → 24.
#   ĝ                        piso 0,079 grau → 0,25 grau, a régua da fronteira
#       A, 4× abaixo da menor decisão a jusante (1 grau).
TOL_ENMO_ABS_G = 5e-5
TOL_ENMO_MAX_ABS_G = 5e-3
TOL_MAG_DIN_REL = 0.04
TOL_ZCR_CRUZAMENTOS = 16
TOL_P_FRAC_AMOSTRAS = 24
TOL_ANGULO_GRAUS = 0.25

# =========================================================================
# TOLERÂNCIAS DE EXATIDÃO (C++ contra `cadeia_estilo_firmware`)
# =========================================================================
# A linha do tempo é a mesma regressão em double dos dois lados: a diferença
# legítima é de arredondamento, ~1e-15 s. 1e-9 s está seis ordens acima disso
# e seis abaixo do menor efeito de sabotagem (o meio passo, 1e-2 s).
TOL_LINHA_DO_TEMPO_S = 1e-9
#
# A grade passa por float32 no ESP32 (entrada e saída de cada seção do
# filtro). Piso medido em 30/10 no `make cadeia` (g++ 13, `gcc:13`): o C++
# difere desta referência em 9,2e-8 g na grade e em 0 s na linha do tempo.
# Teto: a menor sabotagem medida desloca a grade em 6,8e-3 g (`ordem_2`).
# 1e-4 g fica ~1 000× acima do piso e 68× abaixo do teto.
TOL_GRADE_G = 1e-4


def _dif_de_validade(ref: dict, fw: dict) -> dict[str, float]:
    u, v = np.asarray(ref["g"]), np.asarray(fw["g"])
    return {
        "enmo_media": abs(ref["enmo_media"] - fw["enmo_media"]),
        "enmo_desvio": abs(ref["enmo_desvio"] - fw["enmo_desvio"]),
        "enmo_max": abs(ref["enmo_max"] - fw["enmo_max"]),
        "mag_din_rel": abs(ref["mag_din_media"] - fw["mag_din_media"]) / ref["mag_din_media"],
        "zcr_cruzamentos": abs(ref["zcr"] - fw["zcr"]) * (AMOSTRAS_NA_GRADE - 1),
        "p_frac_amostras": abs(ref["p_frac"] - fw["p_frac"]) * AMOSTRAS_NA_GRADE,
        "angulo_graus": math.degrees(math.acos(min(1.0, float(u @ v)))),
    }


_LIMITES = {
    "enmo_media": TOL_ENMO_ABS_G,
    "enmo_desvio": TOL_ENMO_ABS_G,
    "enmo_max": TOL_ENMO_MAX_ABS_G,
    "mag_din_rel": TOL_MAG_DIN_REL,
    "zcr_cruzamentos": TOL_ZCR_CRUZAMENTOS,
    "p_frac_amostras": TOL_P_FRAC_AMOSTRAS,
    "angulo_graus": TOL_ANGULO_GRAUS,
}


def _estoura(ref: dict, fw: dict) -> list[str]:
    return [f"{k} = {v:.3g} > {_LIMITES[k]:.3g}"
            for k, v in _dif_de_validade(ref, fw).items() if v > _LIMITES[k]]


# =========================================================================
# As constantes são do pipeline, não deste arquivo
# =========================================================================
def test_constantes_batem_com_a_configuracao_do_ml():
    """A grade e o corte saem do `config.yaml`. Copiar errado daria uma
    terceira definição do mesmo número — exatamente o que o dourado evita."""
    cfg = carregar_config()
    assert TAXA_DA_GRADE_HZ == cfg.taxa_comum_hz
    assert CORTE_ANTIALIASING_HZ == pytest.approx(
        cfg.corte_antialiasing_frac_nyquist * cfg.taxa_comum_hz / 2, abs=1e-12)
    assert DURACAO_EPOCA_S == cfg.epoca_s


def test_a_c2_amostra_a_50_hz_pelo_divisor_19():
    """`ARQ-01` §5: 1 kHz / (1 + 19). A FIFO de 1024 B com 6 B por amostra
    guarda 170 amostras = 3,4 s; drenar na metade dá 1,7 s."""
    assert TAXA_NOMINAL_HZ == 1000.0 / (1 + 19)
    assert (1024 // 6) == 170
    assert INTERVALO_DE_DRENAGEM_S == pytest.approx(85 / TAXA_NOMINAL_HZ)
    # A variação do despertar não pode encostar no limite da FIFO: com o
    # oscilador a +10 % e o intervalo no máximo, a drenagem tem de chegar antes
    # de 170 amostras.
    pior = (INTERVALO_DE_DRENAGEM_S + VARIACAO_DA_DRENAGEM_S + 0.003) * TAXA_NOMINAL_HZ * 1.10
    assert pior < 170, f"a FIFO transbordaria: {pior:.0f} amostras por drenagem"


# =========================================================================
# Validade: a cadeia do firmware serve ao modelo
# =========================================================================
@pytest.mark.parametrize("seed,fs", CASOS)
def test_cadeia_do_firmware_bate_com_o_pipeline(seed, fs):
    caso = gerar_caso(seed, fs)
    for k, (ref, fw) in enumerate(zip(esperado_pelo_pipeline(caso), cadeia_estilo_firmware(caso))):
        assert fw is not None, f"época {k} recusada a {fs} Hz, dentro da faixa do oscilador"
        assert 1.0 / fw["b_s"] == pytest.approx(fs, rel=1e-3), "a taxa estimada não é a real"
        feats = features_estilo_firmware(fw["grade"], TAXA_DA_GRADE_HZ)
        estouros = _estoura(ref["esperado"], feats)
        assert not estouros, f"[{fs} Hz, época {k}] " + "; ".join(estouros)


def test_com_o_tempo_verdadeiro_a_margem_resolve_as_bordas():
    """A afirmação que sustenta `MARGEM_S`: se o firmware soubesse o instante
    de cada amostra, filtrar por época com 0,5 s de margem daria a mesma grade
    que filtrar a noite inteira. Logo, o que sobra de divergência é relógio."""
    caso = gerar_caso(21, 47.0)
    ref = esperado_pelo_pipeline(caso)
    t = caso["t_verdadeiro_s"]
    oraculo = dict(caso)
    # Drenagens "perfeitas": uma por amostra, no instante exato dela. A
    # regressão então recupera a linha do tempo verdadeira (meio passo depois).
    passo = t[1] - t[0]
    oraculo["drenagens"] = [[caso["origem_us"] + int(round((ti + 0.5 * passo) * 1e6)), 1]
                            for ti in t]
    fw = cadeia_estilo_firmware(oraculo)
    for k in range(caso["n_epocas"]):
        assert float(np.abs(fw[k]["grade"] - ref[k]["grade"]).max()) < 1e-4


def test_sem_antialiasing_a_validade_acusa():
    """O único erro que a régua de validade pega sozinha — e o mais grave:
    o que está entre 12,8 e ~25 Hz dobra para dentro da banda."""
    caso = gerar_caso(CASOS[1][0], CASOS[1][1])
    ref = esperado_pelo_pipeline(caso)
    fw = cadeia_estilo_firmware(caso, "sem_antialiasing")
    feats = features_estilo_firmware(fw[0]["grade"], TAXA_DA_GRADE_HZ)
    assert _estoura(ref[0]["esperado"], feats)


def test_taxa_fora_da_faixa_e_recusada():
    """A 35 Hz (−30 %) a estimativa está medindo outra coisa que não o
    oscilador. A época sai recusada em vez de reamostrada para a grade."""
    caso = gerar_caso(31, 35.0)
    assert all(e is None for e in cadeia_estilo_firmware(caso))


def test_poucas_drenagens_recusam_a_epoca():
    """Uma drenagem em cada três (o despertar falhando): nenhuma amostra se
    perde, porque cada drenagem lê tudo o que acumulou, mas a regressão fica
    com menos pontos que o mínimo e a época é recusada."""
    caso = gerar_caso(32, 50.0)
    novas = [[t_us, 0] for t_us, _ in caso["drenagens"][::3]]
    t = caso["t_verdadeiro_s"]
    acumulado = 0
    for par in novas:
        alvo = (par[0] - caso["origem_us"]) / 1e6
        total = int(np.searchsorted(t, alvo, side="right"))
        par[1] = total - acumulado
        acumulado = total
    caso["drenagens"] = novas
    n_janela = sum(1 for t_us, _ in novas
                   if -MARGEM_S - FOLGA_DO_AJUSTE_S
                   <= (t_us - caso["origem_us"]) / 1e6
                   <= DURACAO_EPOCA_S + MARGEM_S + FOLGA_DO_AJUSTE_S)
    assert n_janela < MINIMO_DE_DRENAGENS
    assert cadeia_estilo_firmware(caso)[0] is None


def test_a_faixa_de_taxa_cobre_o_oscilador():
    """Folha de produto: −15/+10 % na faixa de temperatura. A faixa aceita
    tem de conter isso, senão o firmware recusa noite fria inteira."""
    assert TAXA_MINIMA_FRAC <= 0.85 and TAXA_MAXIMA_FRAC >= 1.10


# =========================================================================
# As tolerâncias são uma afirmação sobre o mundo: re-medidas aqui
# =========================================================================
def test_as_tolerancias_de_validade_cercam_o_piso():
    """Re-mede o piso (20 sementes × 4 taxas × 2 épocas) e exige folga.

    Se cair, a resposta não é afrouxar: é entender por que o firmware se
    afastou do pipeline."""
    piso: dict[str, float] = {}
    for seed in range(1, 21):
        for _, fs in CASOS:
            caso = gerar_caso(seed, fs)
            for ref, fw in zip(esperado_pelo_pipeline(caso), cadeia_estilo_firmware(caso)):
                feats = features_estilo_firmware(fw["grade"], TAXA_DA_GRADE_HZ)
                for k, v in _dif_de_validade(ref["esperado"], feats).items():
                    piso[k] = max(piso.get(k, 0.0), v)
    apertadas = [f"{k}: piso {piso[k]:.3g} contra {_LIMITES[k]:.3g}"
                 for k in _LIMITES if piso[k] > _LIMITES[k] / 1.5]
    assert not apertadas, "tolerância sem folga de 1,5× sobre o piso: " + "; ".join(apertadas)


@pytest.mark.parametrize("sabotagem", ["taxa_nominal", "sem_antialiasing", "ordem_2",
                                       "sem_meio_passo", "sem_margem", "grade_deslocada"])
def test_cada_sabotagem_estoura_a_regua_de_exatidao(sabotagem):
    """O teto da régua de exatidão: cada erro plausível tem de mover a grade
    (ou a linha do tempo) muito além dela. É o que garante que a mutação do
    C++ (`make mutacao-cadeia`) tem o que pegar."""
    maior_grade = 0.0
    maior_tempo = 0.0
    recusas = 0
    for seed, fs in CASOS:
        caso = gerar_caso(seed, fs)
        base = cadeia_estilo_firmware(caso)
        sab = cadeia_estilo_firmware(caso, sabotagem)
        for b, s in zip(base, sab):
            if s is None:
                recusas += 1
                continue
            maior_grade = max(maior_grade, float(np.abs(s["grade"] - b["grade"]).max()))
            maior_tempo = max(maior_tempo, abs(s["b_s"] - b["b_s"]) * 1500)
    assert recusas or maior_grade > 10 * TOL_GRADE_G or maior_tempo > 1e3 * TOL_LINHA_DO_TEMPO_S, (
        f"{sabotagem} quase não muda nada: grade {maior_grade:.2e} g"
    )


# =========================================================================
# O arquivo que o C++ lê
# =========================================================================
def _monta_dourado() -> dict:
    casos = []
    for seed, fs in CASOS:
        caso = gerar_caso(seed, fs)
        ref = esperado_pelo_pipeline(caso)
        fw = cadeia_estilo_firmware(caso)
        epocas = []
        for k, (r, f) in enumerate(zip(ref, fw)):
            amostrada = f["grade"][::PASSO_DA_GRADE_AMOSTRADA]
            epocas.append({
                "inicio_us": caso["origem_us"] + int(k * DURACAO_EPOCA_S * 1e6),
                "estilo_firmware": {
                    "a_s": f["a_s"],
                    "b_s": f["b_s"],
                    "n_drenagens": f["n_drenagens"],
                    "k_ini": f["k_ini"],
                    "k_fim": f["k_fim"],
                    "grade_amostrada": [[float(c) for c in linha] for linha in amostrada],
                },
                "esperado": r["esperado"],
            })
        casos.append({
            "seed": seed,
            "fs_real_hz": fs,
            "origem_us": caso["origem_us"],
            "n_amostras": int(caso["amostras_lsb"].shape[0]),
            "drenagens": caso["drenagens"],
            "amostras_lsb": caso["amostras_lsb"].tolist(),
            "epocas": epocas,
        })
    return {
        "descricao": ("Cadeia C2 (FW-07): bytes da FIFO -> taxa medida -> anti-aliasing -> "
                      "grade de 32 Hz -> features. O C++ le `drenagens` e `amostras_lsb`, "
                      "reproduz `estilo_firmware` com as tolerancias de exatidao e "
                      "`esperado` com as de validade. Ver test_dourado_cadeia_c2.py."),
        "lsb_por_g": LSB_POR_G,
        "taxa_nominal_hz": TAXA_NOMINAL_HZ,
        "taxa_da_grade_hz": TAXA_DA_GRADE_HZ,
        "corte_antialiasing_hz": CORTE_ANTIALIASING_HZ,
        "duracao_epoca_s": DURACAO_EPOCA_S,
        "margem_s": MARGEM_S,
        "folga_do_ajuste_s": FOLGA_DO_AJUSTE_S,
        "minimo_de_drenagens": MINIMO_DE_DRENAGENS,
        "passo_da_grade_amostrada": PASSO_DA_GRADE_AMOSTRADA,
        "features_do_dispositivo": list(FEATURES_DO_DISPOSITIVO),
        "tolerancias": {
            "linha_do_tempo_s": TOL_LINHA_DO_TEMPO_S,
            "grade_g": TOL_GRADE_G,
            "enmo_abs_g": TOL_ENMO_ABS_G,
            "enmo_max_abs_g": TOL_ENMO_MAX_ABS_G,
            "mag_din_rel": TOL_MAG_DIN_REL,
            "zcr_cruzamentos": TOL_ZCR_CRUZAMENTOS,
            "p_frac_amostras": TOL_P_FRAC_AMOSTRAS,
            "g_angulo_graus": TOL_ANGULO_GRAUS,
            "nota": ("Exatidao (linha do tempo, grade) contra estilo_firmware; validade "
                     "(features) contra esperado. Derivacao no cabecalho de "
                     "test_dourado_cadeia_c2.py; o piso de validade e re-medido por "
                     "test_as_tolerancias_de_validade_cercam_o_piso."),
        },
        "casos": casos,
    }


def _serializar(dourado: dict) -> str:
    """JSON indentado, mas com cada lista de números numa linha só.

    Com `indent=2` puro, cada inteiro da FIFO ia para uma linha e o arquivo
    passava de 1,1 MB. Juntando as listas internas (`[x, y, z]`, `[t_us, n]`),
    fica uma amostra por linha: o diff continua legível e o arquivo cai a um
    terço."""
    texto = json.dumps(dourado, indent=2)
    return re.sub(r"\[\s+([-0-9.eE+,\s]+?)\s+\]",
                  lambda m: "[" + ", ".join(v.strip() for v in m.group(1).split(",")) + "]",
                  texto)


def test_dourado_da_cadeia_confere_com_o_arquivo():
    """Referência fixa, não retrato do código: regravar exige pedir
    (`DORMIO_REGRAVAR_DOURADO=1`), como nos outros dois dourados."""
    texto = _serializar(_monta_dourado())
    if REGRAVAR or not CAMINHO.exists():
        CAMINHO.write_text(texto, encoding="utf-8")
        if REGRAVAR:
            pytest.skip("vetor dourado da cadeia C2 regravado (DORMIO_REGRAVAR_DOURADO=1)")
        return
    divergencias = _divergencias(json.loads(CAMINHO.read_text(encoding="utf-8")),
                                 json.loads(texto))
    assert not divergencias, (
        f"o dourado da cadeia C2 no disco NÃO bate com o que o código produz agora "
        f"({len(divergencias)} valor(es); o primeiro: {divergencias[0]}). Se a "
        f"mudança foi intencional, regrave com DORMIO_REGRAVAR_DOURADO=1 e diga "
        f"no commit o que mudou de definição."
    )
