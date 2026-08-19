"""Testes do critério de movimento (DATA-02).

O limiar antigo do firmware era assimétrico (`total > 11.0 || total < 8.0`):
+1,19 m/s² para cima e -1,81 m/s² para baixo em torno da gravidade. O dashboard,
por outro lado, sempre exibiu |total - 9,81| — desvio absoluto, simétrico. Um
mesmo afastamento do repouso era "movimento" para cima e "repouso" para baixo.

Estes testes fixam o critério simétrico do contrato v1.1.0 e travam justamente
a faixa em que os dois discordavam.
"""
import pytest

from fake_sensor import (
    GRAVIDADE,
    LIMIAR_MOVIMENTO,
    STATUS_MOVIMENTO,
    STATUS_REPOUSO,
    classificar,
)


def test_repouso_exato_na_gravidade():
    assert classificar(GRAVIDADE) == STATUS_REPOUSO


@pytest.mark.parametrize("sinal", [1, -1])
def test_simetria_do_limiar(sinal):
    """Mesmo afastamento do repouso -> mesma classificação, para os dois lados."""
    logo_abaixo = GRAVIDADE + sinal * (LIMIAR_MOVIMENTO - 0.05)
    logo_acima = GRAVIDADE + sinal * (LIMIAR_MOVIMENTO + 0.05)

    assert classificar(logo_abaixo) == STATUS_REPOUSO
    assert classificar(logo_acima) == STATUS_MOVIMENTO


def test_regressao_do_limiar_assimetrico():
    """8,5 m/s² é o caso que o limiar antigo classificava errado.

    Desvio de 1,31 m/s² para baixo: acima do limiar, logo é movimento. A regra
    antiga (`< 8.0`) chamava de "Dormindo", enquanto o mesmo desvio para cima
    (11,12) era chamado de movimento.
    """
    abaixo = 8.5
    acima = GRAVIDADE + (GRAVIDADE - abaixo)  # espelho exato

    assert abs(abaixo - GRAVIDADE) > LIMIAR_MOVIMENTO
    assert classificar(abaixo) == STATUS_MOVIMENTO
    assert classificar(abaixo) == classificar(acima)


def test_rotulos_nao_afirmam_sono():
    """O dispositivo registra movimento, não sono (Escopo do ROADMAP.md)."""
    for rotulo in (STATUS_REPOUSO, STATUS_MOVIMENTO):
        assert "dorm" not in rotulo.lower()
        assert "sono" not in rotulo.lower()
