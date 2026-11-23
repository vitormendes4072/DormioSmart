"""A versão do app informada pelo celular (APP-19).

O app manda `versao_app` no `POST /api/devices/celular`, que já é chamado a cada
envio de noite; o servidor grava no aparelho do titular. O que importa travar: a
versão válida é gravada no aparelho certo, existente ou recém-criado; o site
(sem versão) e a versão fora do formato não gravam nada e não mudam a resposta;
e a régua do Flask é a mesma da restrição do banco.
"""
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

import database
import dispositivos
from routes import init_routes

JWT = {"Authorization": "Bearer jwt-de-teste"}
MIGRACAO = Path(__file__).resolve().parents[1] / "migrations" / "026_versao_do_app.sql"
APARELHO = {"id": "dev-celular", "nome": "Celular", "tipo": "celular"}


def _client():
    app = Flask(__name__)
    init_routes(app)
    app.testing = True
    return app.test_client()


def _post(corpo, existente=APARELHO, criado=None, gravou=True):
    with patch.object(database.db, "validar_token_de_usuario", return_value="user-ana"), \
         patch.object(database.db, "cliente_do_usuario", return_value=MagicMock()), \
         patch.object(dispositivos, "primeiro_do_tipo", return_value=existente), \
         patch.object(dispositivos, "criar", return_value=criado) as criar, \
         patch.object(dispositivos, "registrar_versao", return_value=gravou) as registrar:
        kwargs = {"headers": JWT}
        if corpo is not None:
            kwargs["json"] = corpo
        resp = _client().post("/api/devices/celular", **kwargs)
    return resp, registrar, criar


def test_a_versao_do_app_e_gravada_no_aparelho_existente():
    resp, registrar, criar = _post({"versao_app": "1.1.4"})
    assert resp.status_code == 200 and resp.get_json()["id"] == "dev-celular"
    criar.assert_not_called()
    _, usuario, device, versao, quando = registrar.call_args[0]
    assert (usuario, device, versao) == ("user-ana", "dev-celular", "1.1.4")
    assert quando.endswith("+00:00"), "o instante vai com fuso, em UTC"


def test_no_primeiro_envio_a_versao_vai_para_o_aparelho_criado():
    resp, registrar, _ = _post({"versao_app": "1.1.4"}, existente=None, criado={"id": "dev-novo"})
    assert resp.status_code == 201
    assert registrar.call_args[0][2] == "dev-novo"


@pytest.mark.parametrize("corpo", [None, {}, {"versao_app": None}])
def test_o_site_nao_manda_versao_e_nada_e_gravado(corpo):
    resp, registrar, _ = _post(corpo)
    assert resp.status_code == 200
    registrar.assert_not_called()


@pytest.mark.parametrize("versao", ["1.1", "1.1.4-beta", "v1.1.4", 114, ["1.1.4"], "1.1.4 "])
def test_versao_fora_do_formato_e_ignorada_sem_travar(versao):
    resp, registrar, _ = _post({"versao_app": versao})
    assert resp.status_code == 200
    registrar.assert_not_called()


def test_falha_ao_gravar_a_versao_nao_muda_a_resposta():
    resp, registrar, _ = _post({"versao_app": "1.1.4"}, gravou=False)
    assert resp.status_code == 200 and resp.get_json()["id"] == "dev-celular"
    registrar.assert_called_once()


def test_registrar_versao_filtra_pelo_dono_e_pelo_aparelho():
    client = MagicMock()
    tabela = client.table.return_value
    tabela.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [{"id": "d"}]
    assert dispositivos.registrar_versao(client, "user-ana", "d", "1.1.4", "2026-11-23T12:00:00+00:00")
    client.table.assert_called_with("devices")
    tabela.update.assert_called_once_with(
        {"versao_app": "1.1.4", "versao_vista_em": "2026-11-23T12:00:00+00:00"})
    filtros = [c.args for c in (tabela.update.return_value.eq.call_args,
                                tabela.update.return_value.eq.return_value.eq.call_args)]
    assert filtros == [("id", "d"), ("user_id", "user-ana")]


def test_registrar_versao_engole_a_falha():
    client = MagicMock()
    client.table.side_effect = RuntimeError("banco fora")
    assert dispositivos.registrar_versao(client, "u", "d", "1.1.4", "agora") is False


def test_a_regua_do_flask_e_a_da_restricao_do_banco():
    sql = MIGRACAO.read_text(encoding="utf-8")
    no_banco = re.search(r"versao_app ~ '\^(.+?)\$'", sql).group(1)
    assert no_banco == dispositivos._VERSAO_APP.pattern
