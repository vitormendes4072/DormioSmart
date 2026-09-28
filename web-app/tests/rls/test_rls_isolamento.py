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


def test_ana_nao_apaga_a_propria_leitura(como, cenario):
    """Documenta uma LACUNA, não uma virtude.

    Não há policy de delete em `sleep_data`, então o usuário não consegue
    apagar o próprio dado de sono por caminho nenhum do app. Isso protege o
    histórico, mas é um problema de direito do titular (LGPD art. 18, V:
    eliminação do dado pessoal). O teste trava o comportamento ATUAL para que
    a mudança, quando vier, seja deliberada — e aponta o item no lugar certo.
    """
    with como(cenario["ana"]) as ana:
        afetadas = ana.contar_afetadas(
            "delete from public.sleep_data where user_id = %s",
            (cenario["ana"],),
        )
    assert afetadas == 0


def test_ana_nao_apaga_leitura_em_massa(como, cenario):
    """O DELETE sem WHERE. Se o RLS falhar, aqui é onde a base inteira vai."""
    with como(cenario["ana"]) as ana:
        afetadas = ana.contar_afetadas("delete from public.sleep_data")
    assert afetadas == 0


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


def test_ana_nao_le_o_token_hash_do_bruno(como, cenario):
    """`token_hash` é a credencial de ingestão do dispositivo (SEC-02).

    A camada Python nunca devolve essa coluna (`dispositivos.CAMPOS` a omite),
    mas o PostgREST devolve qualquer coluna que o SELECT peça — a lista de
    campos do Python não protege nada aqui. Quem protege é o RLS.
    """
    with como(cenario["ana"]) as ana:
        linhas = ana.executar(
            "select token_hash from public.devices where user_id = %s",
            (cenario["bruno"],),
        )
        todos = ana.executar("select token_hash from public.devices")

    assert linhas == []
    assert {linha[0] for linha in todos} == {"hash-ana-1"}, (
        "a Ana alcancou token_hash que nao e dela"
    )


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


def test_ana_nao_troca_o_token_hash_do_bruno(como, cenario):
    """Sequestro de dispositivo: reescrever o hash apontaria a ingestão do
    Bruno para um token escolhido pela Ana."""
    with como(cenario["ana"]) as ana:
        afetadas = ana.contar_afetadas(
            "update public.devices set token_hash = %s where id = %s",
            ("hash-escolhido-pela-ana", cenario["device_bruno"]),
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
    que escreve leitura carimbada como sendo do Bruno."""
    with como(cenario["ana"]) as ana:
        ana.negado(
            """
            insert into public.devices (user_id, nome, token_hash)
            values (%s, 'Presente de grego', 'hash-plantado')
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


def test_ana_cria_o_proprio_dispositivo(como, cenario):
    """Caminho feliz do pareamento (AUTH-05). Prova que a policy de insert
    existe e funciona — as negativas acima não são "tudo bloqueado"."""
    with como(cenario["ana"]) as ana:
        linhas = ana.executar(
            """
            insert into public.devices (user_id, nome, token_hash, tipo)
            values (%s, 'Meu celular', 'hash-ana-celular', 'celular')
            returning id, nome, tipo
            """,
            (cenario["ana"],),
        )
    assert len(linhas) == 1
    assert linhas[0][1] == "Meu celular"
    assert linhas[0][2] == "celular"


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


def test_ana_nao_apaga_profile_algum(como, cenario):
    """Não há policy de delete em `profiles` — nem para o próprio.

    Igual ao caso de `sleep_data`: protege contra apagar a conta alheia, mas
    deixa o titular sem caminho de eliminação. Travado aqui para que a decisão
    seja explícita.
    """
    with como(cenario["ana"]) as ana:
        for alvo in (cenario["bruno"], cenario["ana"]):
            afetadas = ana.contar_afetadas(
                "delete from public.profiles where id = %s", (alvo,)
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
