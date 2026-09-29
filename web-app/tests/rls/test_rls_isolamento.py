"""Isolamento entre usuários, verificado no banco (SEC-05).

── O QUE ESTES TESTES AFIRMAM ───────────────────────────────────────────

Que o usuário A não alcança o dado do usuário B por nenhum comando SQL, em
nenhuma das três tabelas que carregam dado pessoal (`profiles`, `devices`,
`sleep_data`), e que isso é garantido pelo BANCO — não por um filtro em Python
que uma rota futura pode esquecer.

── POR QUE O TESTE É SQL, E NÃO CHAMADA DE ROTA ─────────────────────────

Porque a superfície exposta é maior que as rotas do Flask. O frontend fala
direto com o Supabase usando a chave `anon`, que é **pública por design**
(`frontend/src/lib/supabase.ts` diz isso explicitamente). Qualquer pessoa com
uma conta no app tem a chave e um JWT válido, e com os dois pode chamar o
PostgREST com o filtro que quiser — sem passar por rota nenhuma.

Testar só pelas rotas provaria que as rotas filtram. Não é essa a pergunta. A
pergunta é se o BANCO recusa, e é ela que estes testes fazem: `SET ROLE
authenticated` com a claim `sub` no GUC é exatamente o que o PostgREST monta
por requisição. O que a Ana consegue aqui é o que a Ana conseguiria com um
`curl`.

── O CAMINHO FELIZ ESTÁ AQUI DE PROPÓSITO ───────────────────────────────

Toda negativa deste arquivo vem acompanhada da afirmativa correspondente: a
Ana lê o próprio dado. Sem isso, um erro de setup (schema vazio, GRANT
faltando, claim mal montada) faria a suíte inteira passar por tudo estar
quebrado — o modo de falha mais perigoso que um teste de segurança tem, porque
ele produz exatamente o relatório verde que se quer ver.
"""
import pytest


# =====================================================================
# 1. sleep_data — as leituras de sono. O dado pessoal propriamente dito.
# =====================================================================

def test_ana_le_apenas_o_proprio_dado_de_sono(como, cenario):
    """Caminho feliz + negativa na mesma asserção: o SELECT amplo."""
    with como(cenario["ana"]) as ana:
        linhas = ana.executar("select id, user_id from public.sleep_data")

    ids = {linha[0] for linha in linhas}
    donos = {str(linha[1]) for linha in linhas}

    assert cenario["leitura_ana"] in ids, (
        "a Ana nao viu o PROPRIO dado. Sem isto, todas as negativas deste "
        "arquivo passariam por estar tudo quebrado."
    )
    assert cenario["leitura_bruno"] not in ids
    assert donos == {cenario["ana"]}


def test_ana_nao_alcanca_a_linha_do_bruno_nem_pedindo_pelo_id(como, cenario):
    """O filtro explícito é o ataque real: quem sonda não pede "tudo"."""
    with como(cenario["ana"]) as ana:
        linhas = ana.executar(
            "select * from public.sleep_data where id = %s",
            (cenario["leitura_bruno"],),
        )
    assert linhas == []


def test_ana_nao_alcanca_dado_do_bruno_filtrando_pelo_user_id_dele(como, cenario):
    """Reproduz a consulta do `database.py` trocando o dono.

    `get_leituras_do_usuario` faz `.eq("user_id", usuario_id)` — proteção em
    profundidade, por cima do RLS. Este teste subverte exatamente esse filtro,
    pedindo o `user_id` do Bruno, para provar que o RLS segura sozinho. É a
    afirmação que o docstring daquele método faz e que nunca tinha sido
    verificada.
    """
    with como(cenario["ana"]) as ana:
        linhas = ana.executar(
            """
            select created_at, movimento_total, temp, status, device_id,
                   epoca_segundos, captured_at
              from public.sleep_data
             where user_id = %s
             order by created_at desc
             limit 100
            """,
            (cenario["bruno"],),
        )
    assert linhas == []


def test_ana_nao_alcanca_dado_do_bruno_pelo_device_id_dele(como, cenario):
    """O recorte por dispositivo (DASH-05) não é uma porta lateral."""
    with como(cenario["ana"]) as ana:
        linhas = ana.executar(
            "select id from public.sleep_data where device_id = %s",
            (cenario["device_bruno"],),
        )
    assert linhas == []


def test_ninguem_enxerga_leitura_sem_dono(como, cenario):
    """Linha órfã (pré-001) é invisível para todo mundo.

    `user_id = auth.uid()` com `user_id` nulo dá NULL, não verdadeiro — então
    a policy nega. É o comportamento que o README das migrações descreve e a
    razão de existir do backfill (DATA-03). Verificado, não suposto.
    """
    for quem in ("ana", "bruno"):
        with como(cenario[quem]) as sessao:
            linhas = sessao.executar(
                "select id from public.sleep_data where id = %s",
                (cenario["leitura_orfa"],),
            )
        assert linhas == [], f"{quem} enxergou a linha orfa"


def test_ana_nao_fabrica_leitura_no_nome_do_bruno(como, cenario):
    """Escrever leitura no nome de outro é o ataque mais grave possível aqui.

    Não é só vazamento: é contaminar o dado de sono de outra pessoa, que é
    exatamente o que um TCC de medição não pode admitir.
    """
    with como(cenario["ana"]) as ana:
        ana.negado(
            """
            insert into public.sleep_data (user_id, movimento_total, status)
            values (%s, 99.0, 'Injetado')
            """,
            (cenario["bruno"],),
        )


def test_ana_nao_fabrica_leitura_nem_no_proprio_nome(como, cenario):
    """Cliente não inventa leitura de sensor — nem a própria.

    A 001 deixa `sleep_data` SEM policy de insert para `authenticated` de
    propósito: a escrita é exclusiva do dispositivo, via service_role. Se um
    dia alguém acrescentar `sleep_data_insert_own` "para facilitar", este teste
    cai — e deve cair, porque a integridade da medição depende de o dado não
    poder ser digitado.
    """
    with como(cenario["ana"]) as ana:
        ana.negado(
            """
            insert into public.sleep_data (user_id, movimento_total, status)
            values (%s, 1.0, 'Digitado')
            """,
            (cenario["ana"],),
        )


def test_ana_nao_altera_leitura_do_bruno(como, cenario):
    with como(cenario["ana"]) as ana:
        afetadas = ana.contar_afetadas(
            "update public.sleep_data set movimento_total = 0 where id = %s",
            (cenario["leitura_bruno"],),
        )
    assert afetadas == 0


def test_ana_nao_altera_leitura_alguma_nem_a_propria(como, cenario):
    """Sem policy de update, nem o dono reescreve a medição. Histórico é imutável."""
    with como(cenario["ana"]) as ana:
        afetadas = ana.contar_afetadas(
            "update public.sleep_data set status = 'Mexido' where id = %s",
            (cenario["leitura_ana"],),
        )
    assert afetadas == 0


def test_ana_nao_apaga_leitura_do_bruno(como, cenario):
    with como(cenario["ana"]) as ana:
        afetadas = ana.contar_afetadas(
            "delete from public.sleep_data where id = %s",
            (cenario["leitura_bruno"],),
        )
    assert afetadas == 0


# A LACUNA QUE ESTAVA AQUI FOI FECHADA PELA 006.
#
# Este arquivo tinha dois testes afirmando que o titular NAO conseguia apagar o
# proprio dado — travando o comportamento de entao e apontando que era um
# problema de direito do titular (LGPD art. 18, VI), nao uma virtude.
#
# A 006 acrescentou as policies de delete. Os testes do direito de eliminacao,
# e o adversarial correspondente (a Ana ganhou alcance sobre o dado do Bruno?),
# estao em `test_rls_eliminacao.py` — inclusive a versao nova do DELETE sem
# WHERE, que agora apaga, e cuja pergunta passou a ser QUANTO.


# =====================================================================
# 2. devices — os dispositivos pareados. Carregam a credencial de ingestão.
# =====================================================================

def test_ana_lista_apenas_os_proprios_dispositivos(como, cenario):
    with como(cenario["ana"]) as ana:
        linhas = ana.executar("select id, user_id, nome from public.devices")

    ids = {str(linha[0]) for linha in linhas}
    assert cenario["device_ana"] in ids, "a Ana nao viu o proprio dispositivo"
    assert cenario["device_bruno"] not in ids


def test_ana_nao_alcanca_dispositivo_do_bruno_pelo_id(como, cenario):
    with como(cenario["ana"]) as ana:
        linhas = ana.executar(
            "select nome from public.devices where id = %s",
            (cenario["device_bruno"],),
        )
    assert linhas == []


# O TESTE DO `token_hash` MUDOU DE LUGAR.
#
# Aqui havia um teste conferindo que a Ana nao lia `devices.token_hash` do
# Bruno. Ele passava — o RLS nunca deixou ler linha alheia. O que ele NAO
# cobria, e a analise que o acompanhava dizia o contrario, e que a Ana lia o
# hash do PROPRIO dispositivo: `dispositivos.CAMPOS` omitia a coluna, mas
# omissao em Python nao e permissao no banco.
#
# A 007 tirou a coluna de `devices` e a pos em `device_tokens`, sem GRANT para
# o cliente. O regime todo da credencial esta em `test_rls_credencial.py`.


def test_ana_nao_renomeia_dispositivo_do_bruno(como, cenario):
    """O caminho do PATCH /api/devices/<id>, sem passar pela rota."""
    with como(cenario["ana"]) as ana:
        afetadas = ana.contar_afetadas(
            "update public.devices set nome = 'Meu agora' where id = %s",
            (cenario["device_bruno"],),
        )
    assert afetadas == 0


def test_ana_nao_revoga_dispositivo_do_bruno(como, cenario):
    """Revogar o dispositivo alheio derruba a coleta da noite dele."""
    with como(cenario["ana"]) as ana:
        afetadas = ana.contar_afetadas(
            "update public.devices set revoked_at = now() where id = %s",
            (cenario["device_bruno"],),
        )
    assert afetadas == 0


def test_ana_nao_sequestra_o_dispositivo_do_bruno(como, cenario):
    """Sequestro de dispositivo: apontar a ingestão do Bruno para um token
    escolhido pela Ana.

    Desde a 007 a credencial nao esta em `devices`, entao o UPDATE daquela
    coluna nem existe mais. A tentativa equivalente — escrever em
    `device_tokens` — esta em
    `test_rls_credencial.py::test_ana_nao_escreve_na_tabela_de_credenciais`.
    O que sobra aqui e a outra metade do sequestro: renomear ou desrevogar
    o dispositivo alheio.
    """
    with como(cenario["ana"]) as ana:
        afetadas = ana.contar_afetadas(
            "update public.devices set revoked_at = null, nome = %s where id = %s",
            ("Meu agora", cenario["device_bruno"]),
        )
    assert afetadas == 0


def test_ana_nao_apaga_dispositivo_do_bruno(como, cenario):
    with como(cenario["ana"]) as ana:
        afetadas = ana.contar_afetadas(
            "delete from public.devices where id = %s",
            (cenario["device_bruno"],),
        )
    assert afetadas == 0


def test_ana_nao_cria_dispositivo_no_nome_do_bruno(como, cenario):
    """Plantar um dispositivo na conta de outro daria à Ana um token válido
    que escreve leitura carimbada como sendo do Bruno.

    Desde a 007 nem no proprio nome da para inserir direto — a policy de insert
    saiu. A versao pela funcao esta em
    `test_rls_credencial.py::test_o_pareamento_nao_aceita_escolher_o_dono`.
    """
    with como(cenario["ana"]) as ana:
        ana.negado(
            """
            insert into public.devices (user_id, nome)
            values (%s, 'Presente de grego')
            """,
            (cenario["bruno"],),
        )


def test_ana_nao_transfere_o_proprio_dispositivo_para_o_bruno(como, cenario):
    """Escalada pelo `with check`: alterar a própria linha para apontar para
    outro dono. Sem `with check`, o `using` sozinho permitiria."""
    with como(cenario["ana"]) as ana:
        ana.negado(
            "update public.devices set user_id = %s where id = %s",
            (cenario["bruno"], cenario["device_ana"]),
        )


# O CAMINHO FELIZ DO PAREAMENTO MUDOU DE LUGAR.
#
# Era um INSERT direto em `devices`, permitido pela policy `devices_insert_own`.
# A 007 removeu aquela policy: o unico caminho de criacao passou a ser
# `parear_dispositivo()`, que cria o dispositivo E a credencial na mesma
# transacao. Ver `test_rls_credencial.py::test_ana_pareia_um_dispositivo_novo`.


def test_ana_renomeia_o_proprio_dispositivo(como, cenario):
    """Caminho feliz do PATCH."""
    with como(cenario["ana"]) as ana:
        afetadas = ana.contar_afetadas(
            "update public.devices set nome = 'Travesseiro novo' where id = %s",
            (cenario["device_ana"],),
        )
    assert afetadas == 1


# =====================================================================
# 3. profiles — nome e idade. Dado pessoal identificável.
# =====================================================================

def test_o_trigger_criou_os_profiles(catalogo, cenario):
    """Pré-condição dos testes abaixo, e teste da 001 em si.

    `handle_new_user` é `security definer` com `search_path = ''`. Se o trigger
    não disparar, os testes de profile passariam por a tabela estar vazia.
    """
    linhas = catalogo("select id, nome from public.profiles order by nome")
    assert [linha[1] for linha in linhas] == ["Ana", "Bruno"]


def test_ana_le_apenas_o_proprio_profile(como, cenario):
    with como(cenario["ana"]) as ana:
        linhas = ana.executar("select id, nome from public.profiles")

    assert len(linhas) == 1, "a Ana enxergou profile que nao e dela"
    assert str(linhas[0][0]) == cenario["ana"]
    assert linhas[0][1] == "Ana"


def test_ana_nao_le_o_profile_do_bruno(como, cenario):
    """Nome e idade de outra pessoa. É o vazamento mais direto de PII aqui."""
    with como(cenario["ana"]) as ana:
        linhas = ana.executar(
            "select nome, idade from public.profiles where id = %s",
            (cenario["bruno"],),
        )
    assert linhas == []


def test_ana_nao_altera_o_profile_do_bruno(como, cenario):
    with como(cenario["ana"]) as ana:
        afetadas = ana.contar_afetadas(
            "update public.profiles set nome = 'Invadido', idade = 1 where id = %s",
            (cenario["bruno"],),
        )
    assert afetadas == 0


def test_ana_nao_cria_profile_para_o_bruno(como, cenario):
    """Se o Bruno ainda não tivesse profile, criá-lo seria plantar dado na
    conta dele antes do primeiro login."""
    with como(cenario["ana"]) as ana:
        ana.negado(
            "insert into public.profiles (id, nome) values (%s, 'Plantado')",
            ("cccccccc-0000-4000-8000-cccccccccccc",),
        )


def test_ana_nao_apaga_o_profile_do_bruno(como, cenario):
    """Desde a 006 existe `profiles_delete_own`, e o alcance dela e o que
    importa: o titular apaga o proprio perfil, nunca o alheio. O caminho feliz
    e os demais casos de eliminacao estao em `test_rls_eliminacao.py`."""
    with como(cenario["ana"]) as ana:
        afetadas = ana.contar_afetadas(
            "delete from public.profiles where id = %s", (cenario["bruno"],)
        )
    assert afetadas == 0


def test_ana_atualiza_o_proprio_profile(como, cenario):
    """Caminho feliz."""
    with como(cenario["ana"]) as ana:
        afetadas = ana.contar_afetadas(
            "update public.profiles set nome = 'Ana Maria', idade = 22 where id = %s",
            (cenario["ana"],),
        )
    assert afetadas == 1


# =====================================================================
# 4. anon — o visitante com a chave pública e nada mais
# =====================================================================

@pytest.mark.parametrize("tabela", ["profiles", "devices", "sleep_data"])
def test_anon_nao_le_nada(como_anon, tabela):
    """A chave anon está no bundle do frontend, legível por qualquer um.

    Todas as policies da 001 são `to authenticated`. Sem JWT não há policy
    aplicável, e o RLS nega por padrão. Este é o teste que impede que a chave
    pública vire uma chave de leitura.
    """
    with como_anon() as visitante:
        assert visitante.executar("select * from public.%s" % tabela) == []


@pytest.mark.parametrize("tabela", ["profiles", "devices", "sleep_data"])
def test_anon_nao_escreve_nada(como_anon, tabela):
    """Importa mais desde a 006: agora EXISTE policy de delete nas tres tabelas.

    Antes, um delete de `anon` afetava zero linhas porque nao havia policy de
    delete para ninguem. Agora ha — para `authenticated`. Este teste e o que
    garante que a chave publica do bundle nao entrou nessa carona.
    """
    with como_anon() as visitante:
        assert visitante.contar_afetadas("delete from public.%s" % tabela) == 0


def test_anon_nao_cria_dispositivo(como_anon, cenario):
    with como_anon() as visitante:
        visitante.negado(
            """
            insert into public.devices (user_id, nome, token_hash)
            values (%s, 'Do visitante', 'hash-anon')
            """,
            (cenario["ana"],),
        )


def test_anon_nao_enxerga_auth_uid(como_anon):
    """Sem claim, `auth.uid()` é nulo — a premissa de todas as policies."""
    with como_anon() as visitante:
        assert visitante.executar("select auth.uid()")[0][0] is None


# =====================================================================
# 5. service_role — o caminho de ingestão, que ignora RLS de propósito
# =====================================================================

def test_service_role_ignora_o_rls(como, cenario):
    """Documenta a assimetria, em vez de deixá-la implícita.

    O backend usa `service_role` na ingestão (`database.py`), e esse papel tem
    BYPASSRLS. É o que faz `POST /api/data` funcionar sem policy de insert em
    `sleep_data`. A consequência é direta e vale estar escrita num teste: **o
    RLS não protege nada do backend**. Se a service_role vazar, ou se uma rota
    montar a consulta com ela em vez do JWT do usuário, o isolamento
    desaparece por completo — e nenhum dos testes acima cairia.

    É por isso que `_cliente_do_usuario()` em `routes.py` é o ponto mais
    sensível do arquivo, e por que o `.eq("user_id", ...)` do `database.py`
    é defesa em profundidade e não redundância decorativa.
    """
    with como(cenario["ana"], papel="service_role") as backend:
        linhas = backend.executar("select user_id from public.sleep_data")
    donos = {str(linha[0]) for linha in linhas if linha[0] is not None}
    assert donos == {cenario["ana"], cenario["bruno"]}, (
        "a service_role deveria ver tudo; se nao ve, a ingestao esta quebrada"
    )
