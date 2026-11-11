"""A autocalibração pela gravidade (CAL-03), e o dourado que o núcleo C++ confere.

Os erros sintéticos são os do Moto E7 medidos na bancada da etapa 0 (diário,
10/11 iv), com um coeficiente de temperatura da ordem do que a noite de 10/11
sugeriu (8 mg de resíduo entre 26 e 18 °C). O sensor simulado lê:

    bruto = escala_sensor · verdade + desvio_sensor + coef_sensor · (T − 22)

e a calibração certa é o inverso disso.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

import numpy as np
import pytest

from src.calibracao import (
    COMPLETO, DESVIO, ERRO_MAXIMO_ACEITO_G, FIXO, PONTOS_MINIMOS, Calibracao,
    aplicar, desfazer, estimar,
)

RAIZ = Path(__file__).resolve().parents[1]
CAMINHO = RAIZ / "testes" / "dourado_calibracao.json"
REGRAVAR = os.environ.get("DORMIO_REGRAVAR_DOURADO", "").strip() == "1"

DESVIO_SENSOR = np.array([-0.0097, 0.0015, -0.0076])
ESCALA_SENSOR = np.array([1.0076, 0.9913, 1.0117])
COEF_SENSOR = np.array([0.0006, -0.0003, 0.0008])
T_SENSOR = 22.0


def _ler(verdade: np.ndarray, temp: np.ndarray, rng, ruido=0.0005) -> np.ndarray:
    v = verdade / np.linalg.norm(verdade, axis=1, keepdims=True)
    return (ESCALA_SENSOR * v + DESVIO_SENSOR + np.outer(temp - T_SENSOR, COEF_SENSOR)
            + rng.normal(0, ruido, v.shape))


def _norma_parada(c: Calibracao, bruto: np.ndarray, temp: np.ndarray) -> np.ndarray:
    return np.linalg.norm(aplicar(c, bruto, temp), axis=1)


# --- os casos (os mesmos vão para o dourado) ---------------------------------

def caso_esfera(rng):
    """Posições espalhadas e 10 °C de faixa: tudo identificável."""
    d = rng.normal(size=(120, 3))
    t = rng.uniform(17, 27, 120)
    return _ler(d, t, rng), t


def caso_deitado(rng):
    """O celular no colchão: tela para cima e para baixo, 1 °C de faixa."""
    d = np.vstack([np.tile([0.02, 0.01, 1.0], (60, 1)), np.tile([0.01, -0.02, -1.0], (60, 1))])
    d = d + rng.normal(0, 0.03, d.shape)
    t = rng.uniform(18, 19, 120)
    return _ler(d, t, rng), t


def caso_so_para_cima(rng):
    """Uma noite inteira de tela para cima."""
    d = np.tile([0.02, 0.01, 1.0], (80, 1)) + rng.normal(0, 0.03, (80, 3))
    t = rng.uniform(18, 19, 80)
    return _ler(d, t, rng), t


def caso_ruidoso(rng):
    """Pontos que não são épocas paradas de verdade: 30 mg de ruído."""
    d = rng.normal(size=(120, 3))
    t = rng.uniform(17, 27, 120)
    return _ler(d, t, rng, ruido=0.03), t


def caso_poucos(rng):
    d = rng.normal(size=(PONTOS_MINIMOS - 1, 3))
    t = rng.uniform(17, 27, PONTOS_MINIMOS - 1)
    return _ler(d, t, rng), t


CASOS = {
    "esfera": caso_esfera,
    "deitado": caso_deitado,
    "so_para_cima": caso_so_para_cima,
    "ruidoso": caso_ruidoso,
    "poucos": caso_poucos,
}


def _gerar(nome):
    return CASOS[nome](np.random.default_rng(sorted(CASOS).index(nome) + 11))


# --- o comportamento ---------------------------------------------------------

def test_na_esfera_recupera_o_erro_do_sensor():
    bruto, t = _gerar("esfera")
    c = estimar(bruto, t)
    assert c.aceita and c.modos == [COMPLETO] * 3 and c.usou_temperatura
    # A calibração certa é o inverso do sensor. A tolerância é a do ruído: com
    # 0,5 mg por ponto e 120 pontos, a escala sai a ~2e-4 da verdade (medido
    # 2,07e-4 no eixo x); 5e-4 é 0,05 % de escala, dez vezes abaixo do erro
    # que se corrige.
    np.testing.assert_allclose(c.escala, 1 / ESCALA_SENSOR, atol=5e-4)
    desvio_esperado = -(DESVIO_SENSOR + COEF_SENSOR * (c.temp_ref_c - T_SENSOR)) / ESCALA_SENSOR
    np.testing.assert_allclose(c.desvio, desvio_esperado, atol=3e-4)
    np.testing.assert_allclose(c.coef_temp, -COEF_SENSOR / ESCALA_SENSOR, atol=5e-5)
    assert c.erro_antes_g > 0.005 and c.erro_depois_g < 0.001


def test_deitado_so_calibra_o_eixo_que_virou_e_tira_o_movimento_fantasma():
    bruto, t = _gerar("deitado")
    c = estimar(bruto, t)
    assert c.aceita and c.modos == [FIXO, FIXO, COMPLETO]
    assert not c.usou_temperatura, "1 °C de faixa não basta para o coeficiente"
    assert c.desvio[:2] == [0.0, 0.0] and c.escala[:2] == [1.0, 1.0]
    # O ENMO parado: antes, a tela para baixo lia mais de 1 g; depois, as duas
    # posições ficam a menos de 2 mg de 1 g.
    antes = np.linalg.norm(bruto, axis=1)
    depois = _norma_parada(c, bruto, t)
    assert abs(antes[60:].mean() - antes[:60].mean()) > 0.01
    assert np.abs(depois - 1).max() < 0.002


def test_um_lado_so_corrige_o_desvio():
    bruto, t = _gerar("so_para_cima")
    c = estimar(bruto, t)
    assert c.aceita and c.modos == [FIXO, FIXO, DESVIO] and c.escala == [1.0, 1.0, 1.0]
    assert abs(_norma_parada(c, bruto, t).mean() - 1) < 0.0005


def test_pontos_que_nao_sao_parados_sao_recusados():
    bruto, t = _gerar("ruidoso")
    c = estimar(bruto, t)
    assert not c.aceita and c.erro_depois_g > ERRO_MAXIMO_ACEITO_G
    assert (c.desvio, c.escala, c.coef_temp) == ([0.0] * 3, [1.0] * 3, [0.0] * 3)


def test_poucos_pontos_sao_recusados():
    bruto, t = _gerar("poucos")
    c = estimar(bruto, t)
    assert not c.aceita and "poucos" in c.motivo


def test_nenhum_eixo_identificavel_e_recusado():
    rng = np.random.default_rng(3)
    pontos = np.tile([0.2, 0.2, 0.2], (60, 1)) + rng.normal(0, 0.01, (60, 3))
    c = estimar(pontos, np.full(60, 20.0))
    assert not c.aceita and c.modos == [FIXO] * 3


def test_recusada_nao_mexe_no_dado():
    bruto, t = _gerar("ruidoso")
    c = estimar(bruto, t)
    np.testing.assert_array_equal(aplicar(c, bruto, t), bruto)


def test_desfazer_e_o_inverso_de_aplicar():
    bruto, t = _gerar("esfera")
    c = estimar(bruto, t)
    np.testing.assert_allclose(desfazer(c, aplicar(c, bruto, t), t), bruto, atol=1e-12)


def test_entrada_malformada():
    with pytest.raises(ValueError):
        estimar(np.zeros((50, 2)), np.zeros(50))


# --- o dourado ---------------------------------------------------------------

def _monta_dourado() -> dict:
    casos = []
    for nome in sorted(CASOS):
        bruto, t = _gerar(nome)
        c = estimar(bruto, t)
        # Três amostras de conferência de `aplicar`, fora dos pontos: o C++
        # tem de calibrar uma amostra qualquer igual.
        conferir = np.array([[0.1, -0.2, 0.97], [-0.7, 0.7, 0.1], [0.0, 0.0, -1.02]])
        t_conferir = np.array([16.0, 22.5, 29.0])
        casos.append({
            "nome": nome,
            "pontos": [[float(v) for v in linha] for linha in bruto],
            "temp_c": [float(v) for v in t],
            "esperado": {
                "aceita": c.aceita,
                "modos": c.modos,
                "usou_temperatura": c.usou_temperatura,
                "desvio": c.desvio,
                "escala": c.escala,
                "coef_temp": c.coef_temp,
                "temp_ref_c": c.temp_ref_c,
                "erro_antes_g": c.erro_antes_g,
                "erro_depois_g": c.erro_depois_g,
            },
            "conferir": [[float(v) for v in linha] for linha in conferir],
            "conferir_temp_c": [float(v) for v in t_conferir],
            "conferir_calibrado": [[float(v) for v in linha]
                                   for linha in aplicar(c, conferir, t_conferir)],
        })
    return {
        "descricao": "CAL-03: autocalibração pela gravidade. Gravado por ml/testes/test_calibracao.py; "
                     "conferido por firmware/nucleo (make calibracao).",
        "casos": casos,
    }


def _iguais(a, b, caminho="") -> list[str]:
    if isinstance(a, dict):
        return [d for k in a for d in _iguais(a[k], b.get(k), f"{caminho}.{k}")]
    if isinstance(a, list):
        if not isinstance(b, list) or len(a) != len(b):
            return [caminho]
        return [d for i, (x, y) in enumerate(zip(a, b)) for d in _iguais(x, y, f"{caminho}[{i}]")]
    if isinstance(a, float) and isinstance(b, float):
        return [] if math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12) else [caminho]
    return [] if a == b else [caminho]


def test_dourado_da_calibracao_confere_com_o_arquivo():
    """Referência fixa: regravar exige `DORMIO_REGRAVAR_DOURADO=1`."""
    dourado = _monta_dourado()
    if REGRAVAR or not CAMINHO.exists():
        CAMINHO.write_text(json.dumps(dourado, indent=1) + "\n", encoding="utf-8")
        if REGRAVAR:
            pytest.skip("dourado da calibração regravado (DORMIO_REGRAVAR_DOURADO=1)")
        return
    divergencias = _iguais(json.loads(CAMINHO.read_text(encoding="utf-8")), dourado)
    assert not divergencias, (
        f"o dourado da calibração no disco não bate com o código ({len(divergencias)}; "
        f"o primeiro: {divergencias[0]}). Se foi intencional, regrave com "
        f"DORMIO_REGRAVAR_DOURADO=1 e diga no commit o que mudou."
    )


def test_o_dourado_cobre_aceita_e_recusa():
    casos = {c["nome"]: c["esperado"] for c in _monta_dourado()["casos"]}
    assert {n for n, e in casos.items() if e["aceita"]} == {"esfera", "deitado", "so_para_cima"}
    assert {n for n, e in casos.items() if not e["aceita"]} == {"ruidoso", "poucos"}
