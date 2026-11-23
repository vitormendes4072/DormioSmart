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
        assert ana.executar("select bancada from sleep_data where id = %s", (cenario["leitura_ana"],)) == [(False,)]

@pytest.mark.parametrize("operacao", ["apagar", "marcar"])
def test_data17_outra_conta_nao_alcanca_nada(como, cenario, operacao):
    with como(cenario["ana"]) as ana:
        ids = _semear(ana, cenario)
        sql = ("select apagar_trecho(%s,%s,%s,%s,%s,%s)" if operacao == "apagar" else
               "select marcar_trecho(%s,%s,%s,true,%s,%s,%s)")
        assert ana.executar(sql, (cenario["device_bruno"], DESDE, ATE, 0, False, _hash_ids([]))) == [(0,)]
        assert _existe(ana, ids["bruno"]) is False

@pytest.mark.parametrize("operacao", ["apagar", "marcar"])
def test_data17_anon_nao_executa(como_anon, cenario, operacao):
    with como_anon() as anon:
        sql = ("select apagar_trecho(%s,%s,%s,%s,%s,%s)" if operacao == "apagar" else
               "select marcar_trecho(%s,%s,%s,true,%s,%s,%s)")
        erro = anon.negado(sql, (cenario["device_ana"], DESDE, ATE, 0, False, _hash_ids([])))
        assert erro.pgcode == "42501"

@pytest.mark.parametrize("operacao", ["apagar", "marcar"])
@pytest.mark.parametrize("janela,mensagem", [((ATE, DESDE), "trecho_invertido"),
    (("2026-11-15 00:00:00+00", "2026-11-17 00:00:01+00"), "trecho_acima_de_48h"),
    ((None, ATE), "trecho_incompleto")])
def test_data17_janela_invalida(como, cenario, operacao, janela, mensagem):
    with como(cenario["ana"]) as ana:
        sql = ("select apagar_trecho(%s,%s,%s,%s,%s,%s)" if operacao == "apagar" else
               "select marcar_trecho(%s,%s,%s,true,%s,%s,%s)")
        ana.executar("savepoint janela")
        with pytest.raises(psycopg2.Error, match=mensagem):
            ana.executar(sql, (cenario["device_ana"], *janela, 0, False, _hash_ids([])))
        ana.executar("rollback to savepoint janela")

def test_a_conferencia_da_janela_nao_e_chamavel_pelo_cliente(como, cenario):
    with como(cenario["ana"]) as ana:
        erro = ana.negado("select _conferir_trecho(%s, %s, %s)", (cenario["device_ana"], DESDE, ATE))
        assert erro.pgcode == "42501"


def test_data17_assinaturas_antigas_foram_removidas(como, cenario):
    with como(cenario["ana"]) as ana:
        assert ana.executar("select to_regprocedure('public.apagar_trecho(uuid,timestamptz,timestamptz)')") == [(None,)]
        assert ana.executar("select to_regprocedure('public.marcar_trecho(uuid,timestamptz,timestamptz,boolean)')") == [(None,)]


def _hash_ids(ids):
    import hashlib
    return hashlib.sha256(",".join(sorted(str(i).lower() for i in ids)).encode("utf-8")).hexdigest()

@pytest.mark.parametrize("operacao", ["apagar", "marcar"])
@pytest.mark.parametrize("alteracao", ["extra", "menos", "marca", "troca", "nenhuma"])
def test_data17_confere_identidade_e_marca(como, cenario, operacao, alteracao):
    with como(cenario["ana"]) as ana:
        ids = _semear(ana, cenario)
        esperados = ids["dentro"] + [ids["chegada"]]
        impressao = _hash_ids(esperados)
        ana.executar("reset role")
        if alteracao in ("menos", "troca"):
            ana.executar("delete from sleep_data where id = %s", (esperados[0],))
        if alteracao in ("extra", "troca"):
            ana.executar("insert into sleep_data (user_id, device_id, movimento_total, status, captured_at) values (%s, %s, 9.8, 'Repouso', %s)",
                         (cenario["ana"], cenario["device_ana"], "2026-11-17 03:00:15+00"))
        if alteracao == "marca":
            ana.executar("update sleep_data set bancada = true where id = %s", (esperados[0],))
        antes = ana.executar("select id, bancada from sleep_data where user_id = %s and device_id = %s order by id", (cenario["ana"], cenario["device_ana"]))
        ana.executar("set local role authenticated")
        sql = ("select apagar_trecho(%s,%s,%s,%s,%s,%s)" if operacao == "apagar"
               else "select marcar_trecho(%s,%s,%s,true,%s,%s,%s)")
        args = (cenario["device_ana"], DESDE, ATE, len(esperados), False, impressao)
        ana.executar("savepoint teste_data17")
        if alteracao == "nenhuma":
            assert ana.executar(sql, args) == [(4,)]
        else:
            with pytest.raises(psycopg2.Error, match="trecho_divergente"):
                ana.executar(sql, args)
            ana.executar("rollback to savepoint teste_data17")
            ana.executar("reset role")
            depois = ana.executar("select id, bancada from sleep_data where user_id = %s and device_id = %s order by id", (cenario["ana"], cenario["device_ana"]))
            assert depois == antes

def test_data17_hash_vetor_fixo(como, cenario):
    ids = ["ffffffff-ffff-ffff-ffff-ffffffffffff", "00000000-0000-0000-0000-000000000001"]
    with como(cenario["ana"]) as ana:
        assert ana.executar("select encode(sha256(convert_to(string_agg(id::text, ',' order by id), 'UTF8')), 'hex') from unnest(%s::uuid[]) id", (ids,))[0][0] == _hash_ids(ids)


@pytest.mark.parametrize("operacao", ["apagar", "marcar"])
def test_data17_chegada_depois_da_conferencia_nao_e_atingida(como, cenario, operacao):
    with como(cenario["ana"]) as ana:
        ids = _semear(ana, cenario)
        esperados = ids["dentro"] + [ids["chegada"]]
        ana.executar("reset role")
        ana.executar("""create function pg_temp.data17_inserir() returns trigger language plpgsql as $$
        begin
          insert into public.sleep_data(user_id, device_id, movimento_total, status, captured_at)
          select OLD.user_id, OLD.device_id, 9.8, 'Repouso', '2026-11-17 03:00:15+00'
          where not exists (select 1 from public.sleep_data where device_id=OLD.device_id and captured_at='2026-11-17 03:00:15+00');
          if TG_OP = 'UPDATE' then return NEW; end if;
          return OLD;
        end $$""")
        evento = "delete" if operacao == "apagar" else "update"
        ana.executar(f"create trigger data17_inserir before {evento} on public.sleep_data for each row execute function pg_temp.data17_inserir()")
        ana.executar("set local role authenticated")
        sql = ("select apagar_trecho(%s,%s,%s,%s,%s,%s)" if operacao == "apagar" else
               "select marcar_trecho(%s,%s,%s,true,%s,%s,%s)")
        assert ana.executar(sql, (cenario["device_ana"], DESDE, ATE, 4, False, _hash_ids(esperados))) == [(4,)]
        ana.executar("reset role")
        assert ana.executar("select bancada from public.sleep_data where device_id=%s and captured_at='2026-11-17 03:00:15+00'", (cenario["device_ana"],)) == [(False,)]


def test_data17_recusa_contagem_errada(como, cenario):
    with como(cenario["ana"]) as ana:
        ids = _semear(ana, cenario)
        esperados = ids["dentro"] + [ids["chegada"]]
        with pytest.raises(psycopg2.Error, match="trecho_divergente"):
            ana.executar("select apagar_trecho(%s,%s,%s,%s,%s,%s)",
                         (cenario["device_ana"], DESDE, ATE, 5, False, _hash_ids(esperados)))


def test_data17_sem_titular_nao_faz_nada(como, cenario):
    with como(None) as sessao:
        assert sessao.executar("select apagar_trecho(%s,%s,%s,%s,%s,%s)",
            (cenario["device_ana"], DESDE, ATE, 0, False, _hash_ids([]))) == [(None,)]

def test_data17_limite_exato_de_48_horas(como, cenario):
    with como(cenario["ana"]) as ana:
        ids = _semear(ana, cenario)
        esperados = ids["dentro"] + [ids["chegada"], ids["fora"]]
        assert ana.executar("select apagar_trecho(%s,%s,%s,%s,%s,%s)",
            (cenario["device_ana"], "2026-11-16 03:00:00+00", "2026-11-18 03:00:00+00",
             5, False, _hash_ids(esperados))) == [(5,)]


def test_data17_conferencia_dos_ids_nao_e_chamavel(como, cenario):
    with como(cenario["ana"]) as ana:
        erro = ana.negado("select _ids_trecho(%s,%s,%s,%s,%s,%s)",
            (cenario["device_ana"], DESDE, ATE, 0, False, _hash_ids([])))
        assert erro.pgcode == "42501"
