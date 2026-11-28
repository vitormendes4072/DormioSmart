"""Chip associado à época, na migração 028."""
import json

import pytest

from test_rls_validacao_no_banco import CHECK, _base, _unica


_SQL_TOKEN = "select public.registrar_leitura(%s, %s::jsonb)"


def _token(leitura):
    return "hash-ana-1", json.dumps(leitura)


def _ler(sessao, leitura_id):
    return sessao.executar(
        "select sensor from public.sleep_data where id = %s", (leitura_id,)
    )[0][0]


@pytest.mark.parametrize("sensor", ["MPU6050", "MPU6500", "desconhecido", None])
def test_token_guarda_o_sensor_da_leitura(como, cenario, sensor):
    leitura = _unica(_base(**({"sensor": sensor} if sensor is not None else {})))
    with como(cenario["ana"], papel="dormio_ingestao") as sessao:
        leitura_id = sessao.executar(_SQL_TOKEN, _token(leitura))[0][0]
        sessao.cursor.execute("set local role postgres")
        assert _ler(sessao, leitura_id) == sensor


def test_sensor_fora_da_lista_e_recusado_no_banco(como, cenario):
    with como(cenario["ana"], papel="dormio_ingestao") as sessao:
        erro = sessao.negado(_SQL_TOKEN, _token(_unica(_base(sensor="outro"))))
        assert erro.pgcode == CHECK
        assert erro.diag.constraint_name == "sleep_data_sensor_valido"


def test_sessao_grava_sem_sensor_mesmo_se_receber_o_campo(como, cenario):
    with como(cenario["ana"]) as sessao:
        leitura_id = sessao.executar(
            "select public.registrar_leitura_da_sessao(%s, %s::jsonb)",
            (cenario["device_ana"], json.dumps(_unica(_base(sensor="MPU6500")))),
        )[0][0]
        assert _ler(sessao, leitura_id) is None


def test_troca_de_chip_e_reenvio_preservam_o_chip_da_epoca_antiga(como, cenario):
    antiga = _unica(_base(sensor="MPU6050"))
    with como(cenario["ana"], papel="dormio_ingestao") as sessao:
        id_antigo = sessao.executar(_SQL_TOKEN, _token(antiga))[0][0]
        id_novo = sessao.executar(_SQL_TOKEN, _token(_unica(_base(sensor="MPU6500"))))[0][0]
        id_repetido = sessao.executar(_SQL_TOKEN, _token(dict(antiga, sensor="MPU6500")))[0][0]
        assert id_repetido == id_antigo
        assert id_novo != id_antigo
        sessao.cursor.execute("set local role postgres")
        assert (_ler(sessao, id_antigo), _ler(sessao, id_novo)) == ("MPU6050", "MPU6500")
