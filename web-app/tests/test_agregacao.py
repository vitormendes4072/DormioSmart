"""Época de agregação e carimbo de captação (contrato v2.0.0, DATA-04).

O ESP32 manda **uma linha por evento**: acorda, mede, dorme. Um celular
amostrando a 50 Hz geraria ~180 mil linhas por hora — precisa agregar por
época antes de enviar. A época e o método viajam com o dado para que uma
mudança de método depois não torne o histórico ambíguo.
"""
import pytest

from validacao import EPOCA_MAXIMA, EPOCA_MINIMA, METODOS_DE_AGREGACAO, validar_leitura

METODO = METODOS_DE_AGREGACAO[0]

BASE = {"ax": 0.10, "ay": 0.20, "az": 9.80, "total": 9.80, "status": "Repouso"}


def test_sem_epoca_nem_metodo_e_amostra_instantanea():
    """O comportamento do ESP32 continua valendo sem nenhum campo novo."""
    dados, erro = validar_leitura(dict(BASE))
    assert erro is None
    assert dados is not None


def test_epoca_com_metodo_e_aceita():
    dados, erro = validar_leitura(dict(BASE, epoca_s=60, metodo=METODO, amostras=3000))
    assert erro is None
    assert dados is not None


def test_epoca_sem_metodo_e_recusada():
    """Uma leitura que resume 60 s sem dizer COMO resumiu não é interpretável."""
    _, erro = validar_leitura(dict(BASE, epoca_s=60))
    assert erro is not None
    assert "metodo" in erro


def test_metodo_sem_epoca_e_recusado():
    _, erro = validar_leitura(dict(BASE, metodo=METODO))
    assert erro is not None
    assert "epoca_s" in erro


def test_metodo_desconhecido_e_recusado():
    # Aceitar string livre faria o identificador não valer nada na análise.
    _, erro = validar_leitura(dict(BASE, epoca_s=60, metodo="chute"))
    assert erro is not None
    assert "metodo" in erro


@pytest.mark.parametrize("valor", [0, -1, EPOCA_MAXIMA + 1, 60.5, "60", True])
def test_epoca_invalida_e_recusada(valor):
    _, erro = validar_leitura(dict(BASE, epoca_s=valor, metodo=METODO))
    assert erro is not None
    assert "epoca_s" in erro


@pytest.mark.parametrize("valor", [EPOCA_MINIMA, 30, 60, EPOCA_MAXIMA])
def test_epocas_usuais_sao_aceitas(valor):
    _, erro = validar_leitura(dict(BASE, epoca_s=valor, metodo=METODO))
    assert erro is None


@pytest.mark.parametrize("valor", [0, -3, "muitas", 10.5, True])
def test_amostras_invalidas_sao_recusadas(valor):
    _, erro = validar_leitura(dict(BASE, epoca_s=60, metodo=METODO, amostras=valor))
    assert erro is not None
    assert "amostras" in erro


def test_amostras_e_opcional():
    _, erro = validar_leitura(dict(BASE, epoca_s=60, metodo=METODO))
    assert erro is None


def test_a_coerencia_continua_valendo_com_epoca():
    """Agregar não dispensa `total` bater com (ax, ay, az).

    O método `pico-da-magnitude` envia os eixos DA AMOSTRA DE PICO, então a
    coerência continua verificável — foi por isso que ele foi escolhido.
    """
    _, erro = validar_leitura(dict(BASE, total=50.0, epoca_s=60, metodo=METODO))
    assert erro is not None
    assert "incoerente" in erro
