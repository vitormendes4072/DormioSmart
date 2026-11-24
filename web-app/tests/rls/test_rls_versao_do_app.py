"""A versão do app informada pelo celular no banco (APP-19, migração 026).

O servidor grava `versao_app` e `versao_vista_em` pelo cliente do titular, sob o
RLS de `devices`. A restrição `devices_versao_app_formato` tem a mesma régua do
Flask (`dispositivos.validar_versao_app`): mais estreita que ele, uma versão
aceita pelo backend falharia na gravação.
"""
import psycopg2
import pytest

import dispositivos

CHECK = "23514"
GRAVAR = "update devices set versao_app = %s, versao_vista_em = now() where id = %s"


def _versao(sessao, device):
    return sessao.executar("select versao_app, versao_vista_em is not null from devices where id = %s", (device,))[0]


def test_aparelhos_comecam_sem_versao(como, cenario):
    with como(cenario["ana"]) as ana:
        assert _versao(ana, cenario["device_ana"]) == (None, False)


def test_o_titular_grava_e_atualiza_a_propria_versao(como, cenario):
    with como(cenario["ana"]) as ana:
        for versao in ("1.1.4", "1.2.0"):
            assert ana.contar_afetadas(GRAVAR, (versao, cenario["device_ana"])) == 1
            assert _versao(ana, cenario["device_ana"]) == (versao, True)


def test_ninguem_grava_a_versao_do_aparelho_alheio(como, cenario):
    with como(cenario["ana"]) as ana:
        assert ana.contar_afetadas(GRAVAR, ("9.9.9", cenario["device_bruno"])) == 0
    with como(cenario["bruno"]) as bruno:
        assert _versao(bruno, cenario["device_bruno"]) == (None, False)


def test_o_visitante_nao_grava(como_anon, cenario):
    with como_anon() as anon:
        try:
            afetadas = anon.contar_afetadas(GRAVAR, ("1.1.4", cenario["device_ana"]))
        except psycopg2.Error as erro:
            assert erro.pgcode == "42501"  # sem privilégio
        else:
            assert afetadas == 0


@pytest.mark.parametrize("versao", ["1.1.4", "0.0.0", "999.999.999"])
def test_a_regua_do_flask_passa(como, cenario, versao):
    assert dispositivos.validar_versao_app(versao) == versao
    with como(cenario["ana"]) as ana:
        assert ana.contar_afetadas(GRAVAR, (versao, cenario["device_ana"])) == 1


@pytest.mark.parametrize("versao", ["1.1", "1.1.4-beta", "1000.0.0", " 1.1.4", "", "v1.1.4"])
def test_fora_da_regua_e_recusado(como, cenario, versao):
    assert dispositivos.validar_versao_app(versao) is None
    with como(cenario["ana"]) as ana:
        with pytest.raises(psycopg2.Error) as erro:
            ana.executar(GRAVAR, (versao, cenario["device_ana"]))
        assert erro.value.pgcode == CHECK


def test_versao_sem_a_data_e_recusada(como, cenario):
    with como(cenario["ana"]) as ana:
        with pytest.raises(psycopg2.Error) as erro:
            ana.executar("update devices set versao_app = '1.1.4' where id = %s", (cenario["device_ana"],))
        assert erro.value.pgcode == CHECK
