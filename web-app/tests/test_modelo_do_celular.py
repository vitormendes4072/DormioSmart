from unittest.mock import MagicMock, patch

import pytest

import dispositivos
from test_versao_do_app import _client, JWT


def post(modelo, existente=None, falha=False):
    criado = {"id": "novo", "nome": "novo"}
    with patch("database.db.validar_token_de_usuario", return_value="usuario-teste"), \
         patch("database.db.cliente_do_usuario", return_value=MagicMock()), \
         patch.object(dispositivos, "primeiro_do_tipo", return_value=existente), \
         patch.object(dispositivos, "criar", return_value=criado) as criar, \
         patch.object(dispositivos, "registrar_modelo", return_value=None if falha else {"id": "d", "nome": modelo}) as registrar:
        resposta = _client().post("/api/devices/celular", json={"modelo": modelo}, headers=JWT)
    return resposta, criar, registrar


def test_cria_com_modelo():
    resposta, criar, _ = post("  Marca Modelo  ")
    assert resposta.status_code == 201
    assert criar.call_args.args[1] == "Marca Modelo"


@pytest.mark.parametrize("modelo", [None, "", " " , "x" * 61, "x\ny", 23, ["x"]])
def test_cria_com_padrao_quando_modelo_invalido(modelo):
    resposta, criar, _ = post(modelo)
    assert resposta.status_code == 201
    assert criar.call_args.args[1] == "Meu celular"


def test_renomeia_padrao():
    resposta, _, registrar = post("Marca Modelo", {"id": "d", "nome": "Meu celular"})
    registrar.assert_called_once()
    assert resposta.get_json()["nome"] == "Marca Modelo"


def test_preserva_nome_alterado():
    resposta, _, registrar = post("Marca Modelo", {"id": "d", "nome": "Meu aparelho"})
    registrar.assert_not_called()
    assert resposta.get_json()["nome"] == "Meu aparelho"


def test_falha_na_troca_nao_derruba_rota():
    resposta, _, registrar = post("Marca Modelo", {"id": "d", "nome": "Meu celular"}, falha=True)
    assert resposta.status_code == 200
    registrar.assert_called_once()
    assert resposta.get_json()["nome"] == "Meu celular"


def test_atualizacao_exige_nome_padrao_e_dono():
    client = MagicMock()
    dispositivos.registrar_modelo(client, "u", "d", "Marca Modelo")
    consulta = client.table.return_value.update.return_value
    assert consulta.eq.call_args.args == ("id", "d")
    assert consulta.eq.return_value.eq.call_args.args == ("user_id", "u")
    assert consulta.eq.return_value.eq.return_value.eq.call_args.args == ("nome", "Meu celular")


def test_erro_do_banco_e_ignorado():
    client = MagicMock()
    client.table.side_effect = RuntimeError("falha")
    assert dispositivos.registrar_modelo(client, "u", "d", "Marca Modelo") is None
