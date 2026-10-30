"""Ingestão em lote — `POST /api/data/lote` (API-03, contrato v2.6.0).

O que se trava aqui é a PROMESSA da resposta, porque é dela que o firmware
decide o que apagar da fila e o que reenviar:

  - toda leitura cai em exatamente uma lista (aceitas, rejeitadas, pendentes);
  - "aceita" só com gravação confirmada (FIX-02, item a item);
  - nada gravado e algo pendente → 503, não 200;
  - autenticação antes do envelope, e o dono nunca vem do corpo (SEC-06).

O Supabase é sempre mockado.
"""
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

import database
import dispositivos
import lote
from device_auth import TOKEN_HEADER
from routes import init_routes

_DEVICE = {"id": "dev-uuid-1", "user_id": "user-uuid-1", "revoked_at": None}
_AUTH = {TOKEN_HEADER: "token-de-teste"}
_LEITURA = {"ax": 0.10, "ay": 0.20, "az": 9.80, "gx": 0.0, "gy": 0.0, "gz": 0.0,
            "t": 32.0, "total": 9.80, "status": "Repouso"}
# Incoerente: total muito longe de √(ax²+ay²+az²). A validação recusa.
_INVALIDA = dict(_LEITURA, total=3.0)


def _client():
    app = Flask(__name__)
    init_routes(app)
    app.testing = True
    return app.test_client()


def _post(corpo, headers=_AUTH):
    return _client().post("/api/data/lote", json=corpo, headers=headers)


def _com_device():
    return patch.object(database.db, "get_device_by_token_hash", return_value=_DEVICE)


def _particao_completa(resposta, n):
    """Cada índice 0..n-1 aparece em exatamente uma lista."""
    rej = [r["indice"] for r in resposta["rejeitadas"]]
    todos = resposta["aceitas"] + rej + resposta["pendentes"]
    return sorted(todos) == list(range(n))


# --- autenticação vem antes do envelope ------------------------------------

def test_sem_credencial_responde_401_e_nao_grava():
    with patch.object(database.db, "registrar_leitura") as gravar:
        resp = _client().post("/api/data/lote", json={"leituras": [_LEITURA]})
    assert resp.status_code == 401
    gravar.assert_not_called()


def test_envelope_invalido_sem_token_ainda_e_401():
    # Quem não se identifica não recebe diagnóstico do corpo, como no /api/data.
    resp = _client().post("/api/data/lote", json={"leituras": "nao-e-lista"})
    assert resp.status_code == 401


def test_token_desconhecido_responde_401():
    with patch.object(database.db, "get_device_by_token_hash", return_value=None), \
         patch.object(database.db, "registrar_leitura") as gravar:
        resp = _post({"leituras": [_LEITURA]})
    assert resp.status_code == 401
    gravar.assert_not_called()


# --- envelope ----------------------------------------------------------------

@pytest.mark.parametrize("corpo", [
    {},
    {"leituras": None},
    {"leituras": "x"},
    {"leituras": {"0": _LEITURA}},
    {"leituras": []},
])
def test_envelope_malformado_e_400(corpo):
    with _com_device(), patch.object(database.db, "registrar_leitura") as gravar:
        resp = _post(corpo)
    assert resp.status_code == 400
    gravar.assert_not_called()


def test_corpo_que_nao_e_json_e_400():
    with _com_device():
        resp = _client().post("/api/data/lote", data="nao-e-json",
                              content_type="application/json", headers=_AUTH)
    assert resp.status_code == 400


def test_lote_acima_do_teto_e_413_e_nada_e_gravado():
    corpo = {"leituras": [_LEITURA] * (lote.MAX_LEITURAS_POR_LOTE + 1)}
    with _com_device(), patch.object(database.db, "registrar_leitura") as gravar:
        resp = _post(corpo)
    assert resp.status_code == 413
    gravar.assert_not_called()


def test_lote_no_teto_e_aceito():
    n = lote.MAX_LEITURAS_POR_LOTE
    with _com_device(), patch.object(database.db, "registrar_leitura", return_value=1):
        resp = _post({"leituras": [_LEITURA] * n})
    assert resp.status_code == 200
    assert resp.get_json()["aceitas"] == list(range(n))


# --- a promessa da resposta -------------------------------------------------

def test_tudo_valido_tudo_aceito_e_uma_gravacao_por_leitura():
    with _com_device(), \
         patch.object(database.db, "registrar_leitura", return_value=1) as gravar:
        resp = _post({"leituras": [_LEITURA] * 3})
    assert resp.status_code == 200
    assert resp.get_json() == {"aceitas": [0, 1, 2], "rejeitadas": [], "pendentes": []}
    assert gravar.call_count == 3


def test_invalida_e_rejeitada_com_indice_e_motivo_e_as_outras_entram():
    with _com_device(), \
         patch.object(database.db, "registrar_leitura", return_value=1) as gravar:
        resp = _post({"leituras": [_LEITURA, _INVALIDA, "nem-objeto", _LEITURA]})
    corpo = resp.get_json()
    assert resp.status_code == 200
    assert corpo["aceitas"] == [0, 3]
    assert [r["indice"] for r in corpo["rejeitadas"]] == [1, 2]
    assert all(r["erro"] for r in corpo["rejeitadas"])
    assert "incoerente" in corpo["rejeitadas"][0]["erro"]
    assert corpo["pendentes"] == []
    assert gravar.call_count == 2          # a inválida nunca chega ao banco
    assert _particao_completa(corpo, 4)


def test_tudo_rejeitado_e_200_porque_reenviar_nao_adianta():
    with _com_device(), patch.object(database.db, "registrar_leitura") as gravar:
        resp = _post({"leituras": [_INVALIDA, _INVALIDA]})
    assert resp.status_code == 200
    assert resp.get_json()["aceitas"] == []
    assert len(resp.get_json()["rejeitadas"]) == 2
    gravar.assert_not_called()


def test_banco_falha_no_meio_o_resto_fica_pendente_e_ele_para_de_tentar():
    # Grava as duas primeiras, falha na terceira: 2..4 pendentes, e a 4ª e a 5ª
    # nem são tentadas.
    with _com_device(), \
         patch.object(database.db, "registrar_leitura",
                      side_effect=[1, 1, None, 1, 1]) as gravar:
        resp = _post({"leituras": [_LEITURA] * 5})
    corpo = resp.get_json()
    assert resp.status_code == 200
    assert corpo["aceitas"] == [0, 1]
    assert corpo["pendentes"] == [2, 3, 4]
    assert gravar.call_count == 3
    assert _particao_completa(corpo, 5)


def test_banco_fora_desde_a_primeira_e_503_nao_200():
    # FIX-02 no lote inteiro: um 200 com tudo pendente pareceria sucesso.
    with _com_device(), patch.object(database.db, "registrar_leitura", return_value=None):
        resp = _post({"leituras": [_LEITURA] * 3})
    assert resp.status_code == 503
    assert resp.get_json()["pendentes"] == [0, 1, 2]
    assert resp.get_json()["aceitas"] == []


def test_estouro_do_orcamento_de_tempo_devolve_o_resto_como_pendente():
    # O relógio pula além do orçamento depois da segunda leitura.
    instantes = iter([0.0, 0.0, 1.0, lote.ORCAMENTO_DE_TEMPO_S + 1.0])
    with _com_device(), \
         patch.object(database.db, "registrar_leitura", return_value=1) as gravar, \
         patch("routes.time.monotonic", side_effect=lambda: next(instantes)):
        resp = _post({"leituras": [_LEITURA] * 5})
    corpo = resp.get_json()
    assert resp.status_code == 200
    assert corpo["aceitas"] == [0, 1]
    assert corpo["pendentes"] == [2, 3, 4]
    assert gravar.call_count == 2


def test_excecao_numa_leitura_rejeita_so_ela():
    # Uma exceção inesperada não pode derrubar o lote: as já gravadas sumiriam
    # da resposta e o dispositivo as reenviaria em duplicata.
    with _com_device(), \
         patch.object(database.db, "registrar_leitura",
                      side_effect=[1, RuntimeError("boom"), 1]):
        resp = _post({"leituras": [_LEITURA] * 3})
    corpo = resp.get_json()
    assert resp.status_code == 200
    assert corpo["aceitas"] == [0, 2]
    assert corpo["rejeitadas"] == [{"indice": 1, "erro": "boom"}]


def test_a_mesma_regra_do_api_data_vale_no_lote():
    # Uma leitura não pode ser válida num caminho e inválida no outro: as duas
    # rotas usam o mesmo `_gravar_leitura`.
    with _com_device(), patch.object(database.db, "registrar_leitura", return_value=1):
        unica = _client().post("/api/data", json=_INVALIDA, headers=_AUTH)
        emlote = _post({"leituras": [_INVALIDA]})
    assert unica.status_code == 400
    assert emlote.get_json()["rejeitadas"][0]["erro"] == unica.get_json()["error"]


def test_o_token_vai_ao_banco_e_nenhum_user_id_no_payload():
    with _com_device(), \
         patch.object(database.db, "registrar_leitura", return_value=1) as gravar:
        _post({"leituras": [dict(_LEITURA, user_id="de-outra-pessoa")]})
    token_hash, payload = gravar.call_args[0]
    assert token_hash
    assert "user_id" not in payload


# --- caminho por sessão (celular) ------------------------------------------

def _com_sessao(device):
    return (
        patch.object(database.db, "validar_token_de_usuario", return_value="user-ana"),
        patch.object(database.db, "cliente_do_usuario", return_value=MagicMock()),
        patch.object(dispositivos, "buscar_do_dono", return_value=device),
    )


_SESSAO = {"Authorization": "Bearer jwt-da-ana"}


def test_sessao_com_dispositivo_proprio_grava_o_lote():
    a, b, c = _com_sessao({"id": "dev-ana"})
    with a, b, c, patch.object(database.db, "registrar_leitura_da_sessao",
                               return_value=7) as gravar:
        resp = _post({"device_id": "dev-ana", "leituras": [_LEITURA] * 2},
                     headers=_SESSAO)
    assert resp.status_code == 200
    assert resp.get_json()["aceitas"] == [0, 1]
    jwt, device_id, _ = gravar.call_args[0]
    assert (jwt, device_id) == ("jwt-da-ana", "dev-ana")


def test_sessao_nao_grava_no_dispositivo_de_outro():
    a, b, c = _com_sessao(None)
    with a, b, c, patch.object(database.db, "registrar_leitura_da_sessao") as gravar:
        resp = _post({"device_id": "dev-bruno", "leituras": [_LEITURA]},
                     headers=_SESSAO)
    assert resp.status_code == 404
    gravar.assert_not_called()


# --- o módulo puro -----------------------------------------------------------

def test_status_da_resposta():
    assert lote.status_da_resposta({"aceitas": [], "rejeitadas": [], "pendentes": [0]}) == 503
    assert lote.status_da_resposta({"aceitas": [0], "rejeitadas": [], "pendentes": [1]}) == 200
    assert lote.status_da_resposta({"aceitas": [], "rejeitadas": [{"indice": 0}],
                                    "pendentes": []}) == 200
