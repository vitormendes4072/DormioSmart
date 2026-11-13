"""Como o cliente de ingestão monta os cabeçalhos (SEC-14).

O defeito que estes testes travam: com `SUPABASE_INGESTAO_KEY` configurada,
`create_client(url, chave_de_ingestao)` punha o JWT do papel `dormio_ingestao`
no `apikey` E no `Authorization`. O gateway do Supabase só aceita no `apikey`
as chaves que ele emitiu (anon, service_role) e responde
`401 Invalid API key` antes de o pedido chegar ao banco. Medido contra a
produção em 31/10: apikey = ingestão -> 401; apikey = anon e Bearer =
ingestão -> 200 com o papel `dormio_ingestao`. Em produção o `/health` foi a
503 enquanto a chave esteve configurada.

Nenhum teste pegava porque nenhum chegava ao gateway: estes também não
chegam -- conferem o arranjo dos cabeçalhos, que é o que a medição mostrou
que decide. A confirmação contra o serviço é o `/health` depois do deploy.
"""
from unittest.mock import Mock, patch

from flask import Flask
from routes import init_routes

import pytest

import database

URL = "https://projeto.supabase.co"
ANON = "chave-anon-publica"
SERVICO = "chave-service-role"
INGESTAO = "jwt-do-papel-dormio-ingestao"


class ClienteFalso:
    def __init__(self, url, chave):
        self.url = url
        self.apikey = chave
        self.bearer_do_postgrest = chave  # o padrão do supabase-py: a mesma chave
        self.postgrest = self

    def auth(self, token):
        self.bearer_do_postgrest = token


def montar(monkeypatch, ingestao=None, anon=ANON, servico=SERVICO):
    monkeypatch.setenv("SUPABASE_URL", URL)
    for nome, valor in (("SUPABASE_INGESTAO_KEY", ingestao),
                        ("SUPABASE_ANON_KEY", anon),
                        ("SUPABASE_SERVICE_ROLE_KEY", servico)):
        if valor is None:
            monkeypatch.delenv(nome, raising=False)
        else:
            monkeypatch.setenv(nome, valor)
    monkeypatch.delenv("SUPABASE_KEY", raising=False)
    db = database.Database()
    with patch.object(database, "create_client", side_effect=ClienteFalso):
        return db.cliente_de_ingestao()


def test_chave_de_ingestao_vai_so_no_authorization(monkeypatch):
    cliente = montar(monkeypatch, ingestao=INGESTAO)
    assert cliente is not None
    assert cliente.apikey == ANON, "o gateway só aceita anon/service_role no apikey"
    assert cliente.bearer_do_postgrest == INGESTAO, "o papel vem do JWT do Authorization"


def test_chave_de_ingestao_nunca_vai_no_apikey(monkeypatch):
    cliente = montar(monkeypatch, ingestao=INGESTAO)
    assert cliente.apikey != INGESTAO


@pytest.mark.parametrize("legada", ["SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_KEY"])
def test_chave_legada_nao_substitui_ingestao(monkeypatch, legada):
    monkeypatch.setenv("SUPABASE_URL", URL)
    monkeypatch.setenv("SUPABASE_ANON_KEY", ANON)
    for nome in ("SUPABASE_INGESTAO_KEY", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_KEY"):
        monkeypatch.delenv(nome, raising=False)
    monkeypatch.setenv(legada, SERVICO)
    db = database.Database()
    app = Flask(__name__)
    init_routes(app)
    falso = Mock()
    falso.rpc.side_effect = lambda nome, *args, **kwargs: Mock(
        execute=Mock(return_value=Mock(data="ok" if nome == "sanidade" else []))
    )
    with patch("routes.db", db), patch.object(database, "create_client", return_value=falso) as criar:
        cliente = app.test_client()
        saude = cliente.get("/health")
        ingestao = cliente.post("/api/data", headers={"X-Device-Token": "token-teste"}, json={})
    assert (saude.status_code, ingestao.status_code) == (503, 503)
    criar.assert_not_called()


def test_chave_de_ingestao_sem_anon_recusa_em_vez_de_cair_para_a_service_role(monkeypatch):
    cliente = montar(monkeypatch, ingestao=INGESTAO, anon=None)
    assert cliente is None, "pedir privilégio mínimo e receber privilégio total em silêncio não"


@pytest.mark.parametrize("ingestao", [INGESTAO, None])
def test_nunca_levanta(monkeypatch, ingestao):
    monkeypatch.setenv("SUPABASE_URL", URL)
    monkeypatch.setenv("SUPABASE_ANON_KEY", ANON)
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", SERVICO)
    if ingestao:
        monkeypatch.setenv("SUPABASE_INGESTAO_KEY", ingestao)
    else:
        monkeypatch.delenv("SUPABASE_INGESTAO_KEY", raising=False)
    db = database.Database()
    with patch.object(database, "create_client", side_effect=RuntimeError("rede")):
        assert db.cliente_de_ingestao() is None
