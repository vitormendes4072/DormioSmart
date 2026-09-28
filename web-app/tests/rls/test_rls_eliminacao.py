"""Direito de eliminação, e o que ele não pode abrir (SEC-07).

── O RISCO DE ACRESCENTAR DELETE ────────────────────────────────────────

Toda policy nova é superfície nova. As de `delete` são as mais perigosas do
conjunto, porque o estrago é irreversível: um vazamento de leitura é grave, um
delete indevido apaga a noite de sono de alguém para sempre, e não há backup de
dado que nunca foi para backup.

Então estes testes gastam mais linhas no adversarial do que no caminho feliz. A
pergunta não é "a Ana consegue apagar o dela?" — é "ao ganhar esse direito, a
Ana ganhou algum alcance sobre o do Bruno?".

── E O PIOR CASO DA FUNÇÃO DE CONTA ─────────────────────────────────────

`apagar_minha_conta()` é `security definer` e apaga de `auth.users`. É a função
mais poderosa do banco. Se ela aceitasse um parâmetro de usuário, um JWT válido
qualquer apagaria qualquer conta. Ela não aceita — e
`test_a_funcao_nao_tem_parametro_de_usuario` existe para que continue assim,
porque acrescentar `p_user_id` "para o admin poder usar" é o tipo de mudança
que parece inofensiva no diff.
"""
import pytest


# =====================================================================
# 1. sleep_data — o titular apaga o próprio, e só
# =====================================================================

def test_ana_apaga_a_propria_leitura(como, cenario):
    """Caminho feliz. Antes da 006 isto era impossível — nem para o dono."""
    with como(cenario["ana"]) as ana:
        afetadas = ana.contar_afetadas(
            "delete from public.sleep_data where id = %s", (cenario["leitura_ana"],)
        )
    assert afetadas == 1, (
        "o titular nao conseguiu apagar o proprio dado — a policy "
        "sleep_data_delete_own nao esta valendo (LGPD art. 18, V)"
    )


def test_ana_nao_apaga_leitura_do_bruno(como, cenario):
    with como(cenario["ana"]) as ana:
        afetadas = ana.contar_afetadas(
            "delete from public.sleep_data where id = %s", (cenario["leitura_bruno"],)
        )
    assert afetadas == 0


def test_o_delete_em_massa_da_ana_nao_alcanca_o_bruno(como, cenario):
    """`delete from sleep_data` sem WHERE.

    Antes da 006 este comando afetava zero linhas, porque não havia policy de
    delete. Agora ele apaga — e o que importa é EXATAMENTE QUANTO. O RLS
    restringe o conjunto de linhas visíveis para apagar, então o comando mais
    destrutivo possível continua limitado ao dono.
    """
    with como(cenario["ana"]) as ana:
        afetadas = ana.contar_afetadas("delete from public.sleep_data")

        # A linha do Bruno e a órfã seguem lá — conferido pelo dono do banco,
        # na mesma transação, antes do rollback.
        ana.cursor.execute("set local role postgres")
        restantes = {
            linha[0]
            for linha in ana.executar("select id from public.sleep_data")
        }

    assert afetadas == 1, f"o delete em massa da Ana afetou {afetadas} linhas"
    assert cenario["leitura_bruno"] in restantes, "a leitura do Bruno foi apagada"
    assert cenario["leitura_orfa"] in restantes


def test_ana_nao_apaga_leitura_sem_dono(como, cenario):
    """A linha órfã não é de ninguém, então não é dela para apagar.

    Importa porque `user_id = auth.uid()` com nulo dá NULL, e um erro de
    escrita da policy (`is not distinct from`, por exemplo) tornaria toda linha
    órfã apagável por qualquer usuário.
    """
    with como(cenario["ana"]) as ana:
        afetadas = ana.contar_afetadas(
            "delete from public.sleep_data where id = %s", (cenario["leitura_orfa"],)
        )
    assert afetadas == 0


def test_o_direito_de_apagar_nao_virou_direito_de_reescrever(como, cenario):
    """Eliminar e alterar são direitos diferentes.

    A 006 acrescentou delete e deliberadamente NÃO acrescentou update. Apagar é
    visível — a linha sai. Editar é invisível, e destruiria o valor probatório
    de todo o conjunto de medições. Se um dia aparecer policy de update em
    `sleep_data`, este teste cai.
    """
    with como(cenario["ana"]) as ana:
        afetadas = ana.contar_afetadas(
            "update public.sleep_data set movimento_total = 0 where id = %s",
            (cenario["leitura_ana"],),
        )
    assert afetadas == 0


# =====================================================================
# 2. profiles — idem
# =====================================================================

def test_ana_apaga_o_proprio_profile(como, cenario):
    with como(cenario["ana"]) as ana:
        afetadas = ana.contar_afetadas(
            "delete from public.profiles where id = %s", (cenario["ana"],)
        )
    assert afetadas == 1


def test_ana_nao_apaga_o_profile_do_bruno(como, cenario):
    with como(cenario["ana"]) as ana:
        afetadas = ana.contar_afetadas(
            "delete from public.profiles where id = %s", (cenario["bruno"],)
        )
    assert afetadas == 0


def test_o_delete_em_massa_de_profiles_nao_alcanca_o_bruno(como, cenario):
    with como(cenario["ana"]) as ana:
        afetadas = ana.contar_afetadas("delete from public.profiles")
        ana.cursor.execute("set local role postgres")
        restantes = {str(l[0]) for l in ana.executar("select id from public.profiles")}
    assert afetadas == 1
    assert cenario["bruno"] in restantes


# =====================================================================
# 3. devices — a policy já existia; confirmando que segue contida
# =====================================================================

def test_ana_apaga_o_proprio_dispositivo_mas_nao_o_do_bruno(como, cenario):
    with como(cenario["ana"]) as ana:
        proprio = ana.contar_afetadas(
            "delete from public.devices where id = %s", (cenario["device_ana"],)
        )
        alheio = ana.contar_afetadas(
            "delete from public.devices where id = %s", (cenario["device_bruno"],)
        )
    assert proprio == 1
    assert alheio == 0


def test_apagar_dispositivo_nao_apaga_a_leitura_dele(como, cenario):
    """`sleep_data.device_id` é `on delete set null`, e é o desejado.

    Apagar o instrumento não pode apagar a medição: a leitura continua sendo
    dado do titular, e ele não pediu para eliminá-la. O que se perde é a
    atribuição de qual aparelho a produziu — perda real, e o motivo de a
    revogação (soft delete) ser o caminho recomendado na interface.
    """
    with como(cenario["ana"]) as ana:
        ana.contar_afetadas(
            "delete from public.devices where id = %s", (cenario["device_ana"],)
        )
        ana.cursor.execute("set local role postgres")
        linha = ana.executar(
            "select user_id, device_id from public.sleep_data where id = %s",
            (cenario["leitura_ana"],),
        )
    assert linha, "a leitura foi apagada junto com o dispositivo"
    assert str(linha[0][0]) == cenario["ana"]
    assert linha[0][1] is None, "device_id deveria ter virado nulo"


# =====================================================================
# 4. apagar_minha_conta() — a eliminação completa
# =====================================================================

def test_a_funcao_nao_tem_parametro_de_usuario(catalogo):
    """A salvaguarda estrutural.

    Sem parâmetro, a função só sabe apagar quem a chamou. Com um `p_user_id`,
    ela se tornaria "apague a conta que eu indicar" — e um JWT de qualquer
    usuário apagaria a conta de qualquer outro, porque `security definer`
    ignora o RLS. É a diferença entre um direito e uma arma.
    """
    assinatura = catalogo(
        """
        select pg_get_function_identity_arguments(p.oid)
          from pg_proc p join pg_namespace n on n.oid = p.pronamespace
         where n.nspname = 'public' and p.proname = 'apagar_minha_conta'
        """
    )
    assert assinatura, "funcao apagar_minha_conta ausente — migration 006 aplicada?"
    assert assinatura[0][0] == "", (
        f"apagar_minha_conta ganhou parametro: {assinatura[0][0]!r}. "
        "Sem parametro ela apaga quem chamou; com parametro, quem for indicado."
    )


def test_ana_apaga_a_propria_conta_por_completo(como, cenario):
    """Caminho feliz, e o recibo.

    Confere que TODAS as três tabelas foram esvaziadas para a Ana. Um teste que
    só olhasse `sleep_data` não pegaria um `delete from profiles` esquecido — e
    perfil remanescente é dado pessoal remanescente.
    """
    with como(cenario["ana"]) as ana:
        recibo = ana.executar("select public.apagar_minha_conta()")[0][0]

        ana.cursor.execute("set local role postgres")
        leituras = ana.executar(
            "select count(*) from public.sleep_data where user_id = %s", (cenario["ana"],)
        )[0][0]
        devices = ana.executar(
            "select count(*) from public.devices where user_id = %s", (cenario["ana"],)
        )[0][0]
        perfis = ana.executar(
            "select count(*) from public.profiles where id = %s", (cenario["ana"],)
        )[0][0]

    assert recibo["leituras_apagadas"] == 1
    assert recibo["dispositivos_apagados"] == 1
    assert recibo["perfil_apagado"] is True
    assert leituras == 0 and devices == 0 and perfis == 0


def test_apagar_a_conta_da_ana_nao_toca_no_bruno(como, cenario):
    """O adversarial da função. `security definer` ignora RLS — o isolamento
    aqui vem do `where` dentro dela, e é isso que está sob teste."""
    with como(cenario["ana"]) as ana:
        ana.executar("select public.apagar_minha_conta()")

        ana.cursor.execute("set local role postgres")
        leituras = ana.executar(
            "select count(*) from public.sleep_data where user_id = %s",
            (cenario["bruno"],),
        )[0][0]
        devices = ana.executar(
            "select count(*) from public.devices where user_id = %s", (cenario["bruno"],)
        )[0][0]
        perfis = ana.executar(
            "select count(*) from public.profiles where id = %s", (cenario["bruno"],)
        )[0][0]
        orfa = ana.executar(
            "select count(*) from public.sleep_data where id = %s",
            (cenario["leitura_orfa"],),
        )[0][0]

    assert leituras == 1, "a exclusao da Ana apagou leitura do Bruno"
    assert devices == 1, "a exclusao da Ana apagou dispositivo do Bruno"
    assert perfis == 1, "a exclusao da Ana apagou o perfil do Bruno"
    assert orfa == 1, "a exclusao da Ana apagou a linha orfa"


def test_apagar_a_conta_remove_a_linha_de_auth_users(como, cenario, catalogo):
    """A eliminação só está completa com o e-mail fora.

    No harness de teste o dono do banco tem privilégio, então isto passa. Em
    produção pode não ter — e nesse caso a função devolve
    `conta_de_acesso_removida: false` e a rota avisa o titular, em vez de
    reportar sucesso completo. Ver o cabeçalho de migrations/006.
    """
    with como(cenario["ana"]) as ana:
        recibo = ana.executar("select public.apagar_minha_conta()")[0][0]
        ana.cursor.execute("set local role postgres")
        restou = ana.executar(
            "select count(*) from auth.users where id = %s", (cenario["ana"],)
        )[0][0]

    assert recibo["conta_de_acesso_removida"] is True
    assert restou == 0


def test_a_funcao_recusa_sem_sessao(como_anon):
    """Sem JWT, `auth.uid()` é nulo. Retorno nulo, não exceção e não estrago."""
    with como_anon() as visitante:
        # O `revoke ... from public` da 006 já barra antes de chegar ao corpo.
        visitante.negado("select public.apagar_minha_conta()")


def test_anon_nao_alcanca_a_funcao(catalogo):
    """A chave anon está no bundle do frontend.

    Função no Postgres nasce com EXECUTE para PUBLIC. Sem o `revoke` da 006,
    um visitante sem conta poderia chamar a função mais destrutiva do banco.
    """
    assert catalogo(
        "select has_function_privilege('anon', 'public.apagar_minha_conta()', 'execute')"
    )[0][0] is False


def test_o_papel_de_ingestao_nao_alcanca_a_funcao(catalogo):
    """A credencial que fica no servidor não apaga conta de ninguém.

    Se alcançasse, o pior caso de um vazamento daquela chave voltaria a incluir
    destruição de dado — e a SEC-06 existiu para que fosse só "insere lixo".
    """
    assert catalogo(
        "select has_function_privilege('dormio_ingestao', "
        "'public.apagar_minha_conta()', 'execute')"
    )[0][0] is False


def test_a_funcao_tem_search_path_fixo(catalogo):
    """`security definer` que apaga de `auth.users` sem `search_path` fixo é a
    pior combinação possível no banco."""
    config = catalogo(
        """
        select coalesce(array_to_string(p.proconfig, ','), '')
          from pg_proc p join pg_namespace n on n.oid = p.pronamespace
         where n.nspname = 'public' and p.proname = 'apagar_minha_conta'
        """
    )[0][0]
    assert "search_path=" in config.replace(" ", ""), config
