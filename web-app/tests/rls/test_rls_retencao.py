"""Retenção por inatividade (LGPD-02, migração 013).

── O QUE ESTÁ SOB TESTE ─────────────────────────────────────────────────

`expurgar_contas_inativas()` apaga por inteiro a conta sem nenhum sinal de uso
há 12 meses: criação, último login, última renovação de sessão (✏️ 10/11, LGPD-09)
ou última leitura. É a segunda função do
banco que apaga conta — e, ao contrário da `apagar_minha_conta()`, apaga a de
OUTRA pessoa. Então o teste mais importante não é "a conta velha saiu"; é "a
conta que ainda tem UM sinal recente ficou".

Cada teste semeia as próprias contas numa transação, como dono do banco, com
as datas recuadas, e tudo é revertido no fim (fixture `como`).
"""
import uuid

import pytest


def _conta(sessao, *, criada_ha, login_ha=None, leitura_ha=None, sessao_ha=None,
           com_dispositivo=True):
    """Cria uma conta com as datas recuadas. Devolve o id.

    `*_ha` são intervalos do Postgres ('13 months', '2 days'); `None` = nunca.
    """
    titular = str(uuid.uuid4())
    sessao.cursor.execute(
        f"""
        insert into auth.users (id, email, created_at, last_sign_in_at)
        values (%s, %s, now() - interval '{criada_ha}',
                {"now() - interval '%s'" % login_ha if login_ha else "null"})
        """,
        (titular, f"{titular}@exemplo.test"),
    )
    if sessao_ha:
        # Uma sessão aberta e renovada (LGPD-09): `updated_at` muda a cada
        # renovação, e o `last_sign_in_at` não.
        sessao.cursor.execute(
            f"insert into auth.sessions (user_id, created_at, updated_at) "
            f"values (%s, now() - interval '{criada_ha}', now() - interval '{sessao_ha}')",
            (titular,),
        )
    device = None
    if com_dispositivo:
        device = str(uuid.uuid4())
        sessao.cursor.execute(
            "insert into public.devices (id, user_id, nome, tipo) values (%s, %s, 'T', 'travesseiro')",
            (device, titular),
        )
        sessao.cursor.execute(
            "insert into public.device_tokens (device_id, token_hash) values (%s, %s)",
            (device, f"hash-{titular}"),
        )
    if leitura_ha:
        sessao.cursor.execute(
            f"""
            insert into public.sleep_data
                (user_id, device_id, movimento_total, temp, status, created_at)
            values (%s, %s, 1.0, 30.0, 'Repouso', now() - interval '{leitura_ha}')
            """,
            (titular, device),
        )
    return titular


def _restos(sessao, titular):
    """Quanto dado pessoal do titular sobrou, tabela a tabela."""
    consultas = {
        "auth.users": "select count(*) from auth.users where id = %s",
        "auth.sessions": "select count(*) from auth.sessions where user_id = %s",
        "profiles": "select count(*) from public.profiles where id = %s",
        "devices": "select count(*) from public.devices where user_id = %s",
        "device_tokens": (
            "select count(*) from public.device_tokens t "
            "join public.devices d on d.id = t.device_id where d.user_id = %s"
        ),
        "sleep_data": "select count(*) from public.sleep_data where user_id = %s",
    }
    return {
        nome: sessao.executar(sql, (titular,))[0][0] for nome, sql in consultas.items()
    }


@pytest.fixture
def dono(como, cenario):
    """Uma transação como dono do banco — é como o agendamento roda."""
    import contextlib

    @contextlib.contextmanager
    def abrir():
        with como(cenario["ana"]) as sessao:
            sessao.cursor.execute("set local role postgres")
            yield sessao

    return abrir


# =====================================================================
# 1. Quem sai
# =====================================================================

def test_conta_sem_nenhum_sinal_ha_13_meses_sai_por_inteiro(dono):
    with dono() as s:
        velha = _conta(s, criada_ha="3 years", login_ha="13 months", leitura_ha="14 months",
                       sessao_ha="13 months")
        recibo = s.executar("select public.expurgar_contas_inativas()")[0][0]
        restos = _restos(s, velha)

    assert restos == {
        "auth.users": 0, "auth.sessions": 0, "profiles": 0, "devices": 0, "device_tokens": 0,
        "sleep_data": 0,
    }, f"sobrou dado pessoal da conta inativa: {restos}"
    assert recibo["contas_expurgadas"] == 1
    assert recibo["leituras_apagadas"] == 1
    assert recibo["dispositivos_apagados"] == 1
    assert recibo["contas_de_acesso_removidas"] == 1


def test_sessao_velha_nao_salva_a_conta(dono):
    """LGPD-09: a sessão conta como uso, mas só se for recente. Login e sessão há 13 meses saem."""
    with dono() as s:
        velha = _conta(s, criada_ha="3 years", login_ha="13 months", sessao_ha="13 months",
                       com_dispositivo=False)
        s.executar("select public.expurgar_contas_inativas()")
        restos = _restos(s, velha)
    assert restos["auth.users"] == 0 and restos["auth.sessions"] == 0


def test_conta_que_nunca_fez_login_nem_enviou_sai(dono):
    """Cadastro abandonado: só a data de criação, e ela é antiga."""
    with dono() as s:
        abandonada = _conta(s, criada_ha="13 months", com_dispositivo=False)
        s.executar("select public.expurgar_contas_inativas()")
        restos = _restos(s, abandonada)
    assert restos["auth.users"] == 0 and restos["profiles"] == 0


# =====================================================================
# 2. Quem fica — o adversarial: UM sinal recente basta
# =====================================================================

@pytest.mark.parametrize(
    "rotulo, datas",
    [
        ("login recente", dict(criada_ha="3 years", login_ha="11 months", leitura_ha="2 years")),
        ("leitura recente", dict(criada_ha="3 years", login_ha="2 years", leitura_ha="2 days")),
        ("conta nova", dict(criada_ha="1 month")),
        # LGPD-09 (10/11): quem usa o app com a sessão aberta e sem dispositivo
        # enviando. O login é velho; a renovação da sessão, não.
        ("sessão renovada recente", dict(criada_ha="3 years", login_ha="13 months",
                                         sessao_ha="1 month", com_dispositivo=False)),
    ],
)
def test_um_sinal_dentro_de_12_meses_mantem_a_conta(dono, rotulo, datas):
    with dono() as s:
        ativa = _conta(s, **datas)
        recibo = s.executar("select public.expurgar_contas_inativas()")[0][0]
        restos = _restos(s, ativa)
    assert recibo["contas_expurgadas"] == 0, f"{rotulo}: a conta ativa foi expurgada"
    assert restos["auth.users"] == 1 and restos["profiles"] == 1, rotulo


def test_o_expurgo_nao_toca_na_conta_ativa_ao_lado_da_inativa(dono):
    """O `where` é por titular: apagar a conta velha não alcança a nova."""
    with dono() as s:
        velha = _conta(s, criada_ha="3 years", leitura_ha="2 years")
        ativa = _conta(s, criada_ha="3 years", leitura_ha="1 day")
        s.executar("select public.expurgar_contas_inativas()")
        restos_velha = _restos(s, velha)
        restos_ativa = _restos(s, ativa)
    assert restos_velha["sleep_data"] == 0
    assert restos_ativa == {
        "auth.users": 1, "auth.sessions": 0, "profiles": 1, "devices": 1, "device_tokens": 1,
        "sleep_data": 1,
    }


def test_o_cenario_comum_e_a_linha_orfa_sobrevivem(dono, cenario):
    """Contas criadas agora (Ana, Bruno) e a leitura sem dono não são alvo."""
    with dono() as s:
        s.executar("select public.expurgar_contas_inativas()")
        usuarios = s.executar(
            "select count(*) from auth.users where id in (%s, %s)",
            (cenario["ana"], cenario["bruno"]),
        )[0][0]
        orfa = s.executar(
            "select count(*) from public.sleep_data where id = %s", (cenario["leitura_orfa"],)
        )[0][0]
    assert usuarios == 2
    assert orfa == 1


# =====================================================================
# 3. Quem não executa
# =====================================================================

@pytest.mark.parametrize("papel", ["anon", "authenticated", "service_role", "dormio_ingestao"])
@pytest.mark.parametrize("funcao", ["public.expurgar_contas_inativas()", "public._eliminar_titular(uuid)"])
def test_nenhum_papel_de_fora_executa_as_funcoes_novas(catalogo, papel, funcao):
    """A chave anon está no bundle; a `authenticated` é qualquer conta. Nenhuma
    das duas pode apagar conta alheia — nem a credencial do servidor."""
    assert catalogo(
        "select has_function_privilege(%s, %s, 'execute')", (papel, funcao)
    )[0][0] is False, f"{papel} executa {funcao}"


def test_usuario_logado_nao_consegue_chamar_o_expurgo(como, cenario):
    with como(cenario["ana"]) as ana:
        ana.negado("select public.expurgar_contas_inativas()")


def test_usuario_logado_nao_consegue_eliminar_outro_titular(como, cenario):
    """`_eliminar_titular` recebe o id: é exatamente a função que a
    `apagar_minha_conta()` se recusa a ser. Fora do banco, ninguém a alcança."""
    with como(cenario["ana"]) as ana:
        ana.negado("select public._eliminar_titular(%s)", (cenario["bruno"],))


def test_as_funcoes_novas_nao_elevam_privilegio(catalogo):
    """`security invoker`: rodam com o privilégio de quem chama."""
    linhas = catalogo(
        """
        select p.proname, p.prosecdef, coalesce(array_to_string(p.proconfig, ','), '')
          from pg_proc p join pg_namespace n on n.oid = p.pronamespace
         where n.nspname = 'public'
           and p.proname in ('expurgar_contas_inativas', '_eliminar_titular')
        """
    )
    assert len(linhas) == 2
    for nome, definer, config in linhas:
        assert definer is False, f"{nome} virou security definer"
        assert "search_path=" in config, f"{nome} sem search_path fixo"


def test_o_expurgo_nao_tem_parametro(catalogo):
    """O prazo é o da política; um parâmetro permitiria `(1)` por engano."""
    args = catalogo(
        """
        select pg_get_function_identity_arguments(p.oid)
          from pg_proc p join pg_namespace n on n.oid = p.pronamespace
         where n.nspname = 'public' and p.proname = 'expurgar_contas_inativas'
        """
    )
    assert args == [("",)]
