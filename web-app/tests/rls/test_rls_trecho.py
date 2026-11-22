"""DATA-16: excluir e marcar um trecho, no PostgreSQL real (migração 023).

As épocas de cada teste são semeadas dentro da própria transação, pelo dono do
banco (como a ingestão grava), e somem no rollback do fim. O trecho é o
`coalesce(captured_at, created_at)` do cliente: uma época sem `captured_at`
entra pelo instante de chegada.
"""
import psycopg2
import pytest

DENTRO = ("2026-11-17 03:00:00+00", "2026-11-17 03:00:30+00", "2026-11-17 03:01:00+00")
FORA = "2026-11-17 05:00:00+00"
DESDE, ATE = "2026-11-17 02:59:00+00", "2026-11-17 03:02:00+00"


def _semear(sessao, cenario):
    """Três épocas da Ana dentro do trecho, uma fora, uma sem `captured_at`
    chegada dentro do trecho, e uma do Bruno com o mesmo instante."""
    sessao.executar("reset role")
    ids = {"dentro": [], "fora": None, "chegada": None, "bruno": None}
    for instante in DENTRO:
        ids["dentro"].append(sessao.executar(
            "insert into public.sleep_data (user_id, device_id, movimento_total, status, captured_at) "
            "values (%s, %s, 9.8, 'Repouso', %s) returning id",
            (cenario["ana"], cenario["device_ana"], instante))[0][0])
    ids["fora"] = sessao.executar(
        "insert into public.sleep_data (user_id, device_id, movimento_total, status, captured_at) "
        "values (%s, %s, 9.8, 'Repouso', %s) returning id",
        (cenario["ana"], cenario["device_ana"], FORA))[0][0]
    ids["chegada"] = sessao.executar(
        "insert into public.sleep_data (user_id, device_id, movimento_total, status, created_at) "
        "values (%s, %s, 9.8, 'Repouso', %s) returning id",
        (cenario["ana"], cenario["device_ana"], DENTRO[1]))[0][0]
    ids["bruno"] = sessao.executar(
        "insert into public.sleep_data (user_id, device_id, movimento_total, status, captured_at) "
        "values (%s, %s, 9.8, 'Repouso', %s) returning id",
        (cenario["bruno"], cenario["device_bruno"], DENTRO[0]))[0][0]
    sessao.executar("set local role authenticated")
    return ids


def _existe(sessao, linha):
    sessao.executar("reset role")
    achou = sessao.executar("select bancada from public.sleep_data where id = %s", (linha,))
    sessao.executar("set local role authenticated")
    return achou[0][0] if achou else None


def test_a_epoca_nasce_fora_da_bancada(como, cenario):
    with como(cenario["ana"]) as ana:
        assert ana.executar("select bancada from sleep_data where id = %s",
                            (cenario["leitura_ana"],)) == [(False,)]


def test_titular_apaga_o_proprio_trecho_e_so_ele(como, cenario):
    with como(cenario["ana"]) as ana:
        ids = _semear(ana, cenario)
        assert ana.executar("select apagar_trecho(%s, %s, %s)",
                            (cenario["device_ana"], DESDE, ATE)) == [(4,)]
        for linha in ids["dentro"] + [ids["chegada"]]:
            assert _existe(ana, linha) is None
        assert _existe(ana, ids["fora"]) is False
        assert _existe(ana, ids["bruno"]) is False


def test_titular_marca_e_desmarca_o_proprio_trecho(como, cenario):
    with como(cenario["ana"]) as ana:
        ids = _semear(ana, cenario)
        assert ana.executar("select marcar_trecho(%s, %s, %s, true)",
                            (cenario["device_ana"], DESDE, ATE)) == [(4,)]
        for linha in ids["dentro"] + [ids["chegada"]]:
            assert _existe(ana, linha) is True
        assert _existe(ana, ids["fora"]) is False
        assert _existe(ana, ids["bruno"]) is False
        assert ana.executar("select marcar_trecho(%s, %s, %s, false)",
                            (cenario["device_ana"], DESDE, ATE)) == [(4,)]
        for linha in ids["dentro"]:
            assert _existe(ana, linha) is False


@pytest.mark.parametrize("funcao", ["apagar", "marcar"])
def test_aparelho_de_outra_conta_nao_e_alcancado(como, cenario, funcao):
    """O dono vem de `auth.uid()`: a Ana passando o aparelho do Bruno, na
    janela da época dele, não apaga nem marca nada."""
    with como(cenario["ana"]) as ana:
        ids = _semear(ana, cenario)
        sql = ("select apagar_trecho(%s, %s, %s)" if funcao == "apagar"
               else "select marcar_trecho(%s, %s, %s, true)")
        assert ana.executar(sql, (cenario["device_bruno"], DESDE, ATE)) == [(0,)]
        assert _existe(ana, ids["bruno"]) is False


@pytest.mark.parametrize("janela,mensagem", [
    (("2026-11-17 03:00:00+00", "2026-11-17 02:00:00+00"), "trecho_invertido"),
    (("2026-11-15 00:00:00+00", "2026-11-17 00:00:01+00"), "trecho_acima_de_48h"),
    ((None, "2026-11-17 00:00:00+00"), "trecho_incompleto"),
])
@pytest.mark.parametrize("funcao", ["apagar", "marcar"])
def test_janela_fora_do_aceito_e_recusada_sem_tocar_em_nada(como, cenario, janela, mensagem, funcao):
    with como(cenario["ana"]) as ana:
        ids = _semear(ana, cenario)
        sql = ("select apagar_trecho(%s, %s, %s)" if funcao == "apagar"
               else "select marcar_trecho(%s, %s, %s, true)")
        ana.executar("savepoint antes")
        with pytest.raises(psycopg2.Error) as erro:
            ana.executar(sql, (cenario["device_ana"], *janela))
        assert erro.value.pgcode == "22023"
        assert erro.value.diag.message_primary == mensagem
        ana.executar("rollback to savepoint antes")
        assert all(_existe(ana, linha) is False for linha in ids["dentro"])


def test_janela_de_48h_exatas_e_aceita(como, cenario):
    with como(cenario["ana"]) as ana:
        _semear(ana, cenario)
        assert ana.executar("select apagar_trecho(%s, %s, %s)",
                            (cenario["device_ana"], "2026-11-16 03:00:00+00",
                             "2026-11-18 03:00:00+00")) == [(5,)]


def test_sem_titular_nao_faz_nada(como, cenario):
    """Papel autenticado sem `sub`: a função devolve nulo, como a
    `apagar_minha_conta()`, e não apaga nada."""
    with como(None) as sem_dono:
        assert sem_dono.executar("select apagar_trecho(%s, %s, %s)",
                                 (cenario["device_ana"], DESDE, ATE)) == [(None,)]


@pytest.mark.parametrize("assinatura", [
    "apagar_trecho(%s, %s, %s)",
    "marcar_trecho(%s, %s, %s, true)",
])
def test_anon_nao_executa(como_anon, cenario, assinatura):
    with como_anon() as anon:
        erro = anon.negado("select " + assinatura, (cenario["device_ana"], DESDE, ATE))
        assert erro.pgcode == "42501"


def test_a_conferencia_da_janela_nao_e_chamavel_pelo_cliente(como, cenario):
    with como(cenario["ana"]) as ana:
        erro = ana.negado("select _conferir_trecho(%s, %s, %s)", (cenario["device_ana"], DESDE, ATE))
        assert erro.pgcode == "42501"
