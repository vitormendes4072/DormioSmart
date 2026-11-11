"""O consentimento específico e destacado para dado de saúde (LGPD-12, migração 017).

── O QUE ESTÁ SOB TESTE ─────────────────────────────────────────────────────

A política trata a série de movimento e a estimativa de sono como dado de saúde (art. 11, I):
sem consentimento específico e destacado, não há tratamento. A 017 faz o BANCO garantir isso, e
não só a tela:

  1. sem consentimento na versão vigente, a gravação pela sessão e o pareamento recusam;
  2. a data do consentimento é do relógio do banco, e o titular não a escreve direto;
  3. versão antiga do texto conta como sem consentimento;
  4. o caminho do token do dispositivo NÃO é travado — decisão do autor, para o firmware não
     descartar a noite; o teste fixa essa decisão, para que mudá-la seja visível.

A Ana do cenário consentiu (conftest). Cada teste retira o consentimento dela dentro da própria
transação, como dono do banco, e tudo volta no fim.
"""
import json

SEM_PRIVILEGIO = "42501"
CHECK = "23514"
HASH_ANA = "hash-ana-1"
LEITURA = json.dumps({"movimento_total": 9.8, "status": "Repouso"})


def _sem_consentimento(sessao, usuario, versao=None):
    """Como dono do banco, deixa o titular sem consentimento (ou com uma versão dada)."""
    sessao.cursor.execute("set local role postgres")
    sessao.cursor.execute(
        "update public.profiles set consentimento_saude_em = %s, consentimento_saude_versao = %s "
        "where id = %s",
        (None if versao is None else "2026-01-01", versao, usuario),
    )
    sessao._reaplicar()


def _versao(sessao):
    return sessao.executar("select public.versao_do_consentimento()")[0][0]


def test_sem_consentimento_a_gravacao_pela_sessao_e_recusada(como, cenario):
    with como(cenario["ana"]) as ana:
        _sem_consentimento(ana, cenario["ana"])
        erro = ana.negado("select public.registrar_leitura_da_sessao(%s, %s::jsonb)",
                          (cenario["device_ana"], LEITURA))
        assert erro.pgcode == SEM_PRIVILEGIO, erro


def test_sem_consentimento_o_pareamento_e_recusado(como, cenario):
    with como(cenario["ana"]) as ana:
        _sem_consentimento(ana, cenario["ana"])
        erro = ana.negado("select id from public.parear_dispositivo('x', 'celular', %s)", ("ab" * 32,))
        assert erro.pgcode == SEM_PRIVILEGIO, erro


def test_versao_antiga_conta_como_sem_consentimento(como, cenario):
    with como(cenario["ana"]) as ana:
        _sem_consentimento(ana, cenario["ana"], versao="2000-01-01")
        erro = ana.negado("select public.registrar_leitura_da_sessao(%s, %s::jsonb)",
                          (cenario["device_ana"], LEITURA))
        assert erro.pgcode == SEM_PRIVILEGIO, erro


def test_consentir_na_versao_vigente_grava_a_data_do_banco_e_libera(como, cenario):
    with como(cenario["ana"]) as ana:
        _sem_consentimento(ana, cenario["ana"])
        recibo = ana.executar("select public.consentir_dado_de_saude(%s)", (_versao(ana),))[0][0]
        assert recibo["consentimento_saude_versao"] == _versao(ana)
        agora = ana.executar("select now()")[0][0]
        ana.cursor.execute("set local role postgres")
        em, versao = ana.executar(
            "select consentimento_saude_em, consentimento_saude_versao from public.profiles where id = %s",
            (cenario["ana"],))[0]
        ana._reaplicar()
        assert em == agora, "a data do consentimento nao e a do relogio do banco"
        assert versao == _versao(ana)
        assert ana.executar("select public.registrar_leitura_da_sessao(%s, %s::jsonb)",
                            (cenario["device_ana"], LEITURA))[0][0] is not None


def test_consentir_com_versao_errada_e_recusado(como, cenario):
    with como(cenario["ana"]) as ana:
        erro = ana.negado("select public.consentir_dado_de_saude(%s)", ("2000-01-01",))
        assert erro.pgcode == CHECK, erro


def test_o_titular_nao_escreve_o_consentimento_direto(como, cenario):
    with como(cenario["ana"]) as ana:
        _sem_consentimento(ana, cenario["ana"])
        erro = ana.negado(
            "update public.profiles set consentimento_saude_em = now(), "
            "consentimento_saude_versao = public.versao_do_consentimento() where id = %s",
            (cenario["ana"],))
        assert erro.pgcode == SEM_PRIVILEGIO, erro


def test_o_titular_nao_forja_a_data(como, cenario):
    with como(cenario["ana"]) as ana:
        erro = ana.negado(
            "update public.profiles set consentimento_saude_em = '2020-01-01' where id = %s",
            (cenario["ana"],))
        assert erro.pgcode == SEM_PRIVILEGIO, erro


def test_quem_nao_tem_perfil_nao_cria_um_ja_consentido(como, cenario):
    with como(cenario["sem_perfil"]) as carol:
        erro = carol.negado(
            "insert into public.profiles (id, consentimento_saude_em, consentimento_saude_versao) "
            "values (%s, now(), public.versao_do_consentimento())",
            (cenario["sem_perfil"],))
        assert erro.pgcode == SEM_PRIVILEGIO, erro


def test_quem_nao_tem_perfil_consente_pela_funcao(como, cenario):
    with como(cenario["sem_perfil"]) as carol:
        carol.executar("select public.consentir_dado_de_saude(%s)", (_versao(carol),))
        carol.cursor.execute("set local role postgres")
        assert carol.executar(
            "select consentimento_saude_versao from public.profiles where id = %s",
            (cenario["sem_perfil"],))[0][0] is not None


def test_o_titular_ainda_corrige_o_proprio_nome(como, cenario):
    """O gatilho só olha as colunas do consentimento."""
    with como(cenario["ana"]) as ana:
        assert ana.contar_afetadas("update public.profiles set nome = 'Ana Maria' where id = %s",
                                   (cenario["ana"],)) == 1


def test_o_caminho_do_token_nao_e_travado(como, cenario):
    """Decisão do autor (10/11): o firmware descarta leitura recusada; o pareamento já exige o
    consentimento. Se esta decisão mudar, este teste cai, e a mudança fica visível."""
    with como(cenario["ana"], papel="dormio_ingestao") as ingestao:
        ingestao.cursor.execute("set local role postgres")
        ingestao.cursor.execute(
            "update public.profiles set consentimento_saude_em = null, "
            "consentimento_saude_versao = null where id = %s", (cenario["ana"],))
        ingestao._reaplicar()
        assert ingestao.executar("select public.registrar_leitura(%s, %s::jsonb)",
                                 (HASH_ANA, LEITURA))[0][0] is not None


def test_anon_nao_consente(como_anon, cenario):
    with como_anon() as anon:
        erro = anon.negado("select public.consentir_dado_de_saude('2026-11-10')")
        assert erro.pgcode == SEM_PRIVILEGIO, erro
