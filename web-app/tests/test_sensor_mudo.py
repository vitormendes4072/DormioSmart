"""Recusa de leitura de sensor que responde mas nao mede (SEC-06).

Caso real de bancada em 25/08/2026: o MPU6050 passou a devolver todos os
registradores zerados. O delator foi a temperatura — 36,5 C e exatamente o
que a biblioteca produz com o registrador em zero (`raw / 340 + 36,53`).

Com os eixos zerados o dispositivo calcula |0 - 9,81| = 9,81, classifica como
MOVIMENTO e envia. O payload passava em tudo: zero esta na faixa fisica e a
coerencia fecha. Um fio solto encheria a base de eventos FABRICADOS.
"""
import pytest

from validacao import validar_leitura

# O payload exato que o firmware antigo mandaria com o sensor mudo.
SENSOR_MUDO = {
    "ax": 0.0, "ay": 0.0, "az": 0.0,
    "gx": 0.0, "gy": 0.0, "gz": 0.0,
    "t": 36.5, "total": 0.0, "status": "Movimento",
}

VIVA = {"ax": 0.10, "ay": 0.20, "az": 9.80, "total": 9.80, "status": "Repouso"}


def test_os_tres_eixos_zerados_sao_recusados():
    _, erro = validar_leitura(dict(SENSOR_MUDO))
    assert erro is not None
    assert "zero" in erro


def test_a_mensagem_aponta_para_a_alimentacao():
    """Quem le o 400 no monitor serial precisa saber o que conferir."""
    _, erro = validar_leitura(dict(SENSOR_MUDO))
    assert "alimenta" in erro.lower()


def test_o_payload_mudo_passaria_em_todo_o_resto():
    """Mostra por que esta regra precisou existir.

    Sem ela, nada mais barra: zero esta dentro da faixa fisica declarada, a
    coerencia fecha (0 = raiz de 0+0+0) e o status e um dos validos.
    """
    from validacao import CAMPOS_NUMERICOS, STATUS_VALIDOS, TOLERANCIA_COERENCIA
    import math

    for campo, (minimo, maximo) in CAMPOS_NUMERICOS.items():
        assert minimo <= SENSOR_MUDO[campo] <= maximo, f"{campo} sairia da faixa"
    assert SENSOR_MUDO["status"] in STATUS_VALIDOS
    magnitude = math.sqrt(sum(SENSOR_MUDO[c] ** 2 for c in ("ax", "ay", "az")))
    assert abs(SENSOR_MUDO["total"] - magnitude) <= TOLERANCIA_COERENCIA


def test_leitura_viva_continua_passando():
    dados, erro = validar_leitura(dict(VIVA))
    assert erro is None
    assert dados is not None


@pytest.mark.parametrize("eixo", ["ax", "ay", "az"])
def test_um_unico_eixo_em_zero_e_legitimo(eixo):
    """Deitado, dois eixos ficam perto de zero. So os TRES juntos e defeito."""
    leitura = dict(VIVA, **{eixo: 0.0})
    # recalcula o total para a coerencia continuar valendo
    import math
    leitura["total"] = round(
        math.sqrt(sum(leitura[c] ** 2 for c in ("ax", "ay", "az"))), 2
    )
    _, erro = validar_leitura(leitura)
    assert erro is None, f"{eixo}=0 sozinho nao deveria ser recusado: {erro}"


def test_dois_eixos_em_zero_e_legitimo():
    """Sensor perfeitamente nivelado: ax e ay em zero, az na gravidade."""
    _, erro = validar_leitura(
        {"ax": 0.0, "ay": 0.0, "az": 9.81, "total": 9.81, "status": "Repouso"}
    )
    assert erro is None


def test_a_regra_nao_e_um_piso_de_magnitude():
    """Em queda livre |a| tende a zero de verdade, e isso e fisica, nao defeito.

    A regra olha os TRES eixos exatamente zero — assinatura de registrador
    morto — e nao a magnitude pequena.
    """
    quase_queda = {"ax": 0.02, "ay": -0.01, "az": 0.03, "total": 0.04,
                   "status": "Movimento"}
    _, erro = validar_leitura(quase_queda)
    assert erro is None
