"""`profiles` como fonte de verdade — o caminho de escrita novo (PERFIL-01).

── POR QUE ESTE ARQUIVO EXISTE, SEPARADO DO `test_rls_isolamento.py` ────

O `test_rls_isolamento.py` já cobre `profiles` com `select`, `update`,
`insert` e `delete` avulsos, e continua cobrindo. O que ele **não** cobre é o
comando que a rota `PATCH /api/me/perfil` de fato emite, e que não existia
quando aquele arquivo foi escrito:

    insert into public.profiles (id, nome) values (...)
    on conflict (id) do update set nome = excluded.nome

É isso que o `upsert` do PostgREST manda. E `upsert` não é "insert ou update":
o barramento dele depende de a linha de destino **existir ou não**, e é isso
que decide qual policy recusa.

* Vítima **sem** linha: sobra o insert puro, e quem barra é
  `profiles_insert_own`.
* Vítima **com** linha: cai no `do update`, e quem barra é
  `profiles_update_own`.

Os dois casos precisam de teste separado, e isso não era óbvio — um barramento
em série esconde o outro. Foi o sabotador `perfil_insert_permissivo` que
mostrou: com a policy de insert escancarada, o teste da vítima **com** perfil
continua passando. O caso da vítima sem perfil ficou em
`test_rls_isolamento.py`, ao lado do insert avulso equivalente, que tinha o
mesmo ponto cego e foi corrigido na mesma passagem.

A outra metade do arquivo são os três mecanismos que a migração `008`
acrescenta, e que só passam a importar quando a tabela deixa de ser inerte:
`updated_at` que se mantém, teto de tamanho do nome, e a finalidade declarada
de `idade` junto do dado.

⚠️ **A `008` precisa ser aplicada no Supabase pelo Vitor.** Aqui ela é
aplicada pelo `conftest`, contra um Postgres descartável — o que estes testes
provam é que o SQL faz o que diz, **não** que o banco de produção o tem.
"""
import pytest

# `nome` e `idade` são o vazamento de PII mais direto desta suíte; o
# `test_rls_isolamento.py` diz isso no cabeçalho da sua seção 3. Os valores
# abaixo são os que o cenário semeia pelo gatilho do signup.
NOME_DA_ANA = "Ana"
NOME_DO_BRUNO = "Bruno"


# =====================================================================
# 1. O caminho de escrita da rota: upsert
# =====================================================================

def test_ana_faz_upsert_do_proprio_perfil(como, cenario):
    """Caminho feliz — é o que a rota emite num `PATCH`."""
    with como(cenario["ana"]) as ana:
        afetadas = ana.contar_afetadas(
            """
            insert into public.profiles (id, nome, idade) values (%s, %s, 22)
            on conflict (id) do update
               set nome = excluded.nome, idade = excluded.idade
            """,
            (cenario["ana"], "Ana Maria"),
        )
        assert afetadas == 1
        linhas = ana.executar(
            "select nome, idade from public.profiles where id = %s", (cenario["ana"],)
        )
    assert linhas == [("Ana Maria", 22)]


def test_ana_nao_faz_upsert_no_perfil_do_bruno(como, cenario):
    """O ataque pelo comando que a rota emite, contra quem JÁ tem perfil.

    ⚠️ **O que este teste cobre é menos do que parece, e isso foi medido.** A
    linha do Bruno existe, então o `on conflict` cai no ramo de UPDATE e é a
    policy de **update** que recusa. Com `profiles_insert_own` escancarada
    (`with check (true)`), este teste **continua passando** — comprovado pelo
    sabotador `perfil_insert_permissivo`.

    Dois barramentos em série tornam cada um invisível a partir do outro: é o
    §1 das lições (*o conjunto coberto é menor que o conjunto que o nome
    anuncia*), e a razão pela qual a cobertura da policy de insert fica em
    `test_rls_isolamento.py::test_ana_nao_faz_upsert_no_perfil_de_quem_ainda_nao_tem`,
    onde a vítima não tem linha e não há segundo barramento para esconder o
    primeiro.
    """
    with como(cenario["ana"]) as ana:
        ana.negado(
            """
            insert into public.profiles (id, nome, idade) values (%s, 'Invadido', 1)
            on conflict (id) do update
               set nome = excluded.nome, idade = excluded.idade
            """,
            (cenario["bruno"],),
        )


def test_o_perfil_do_bruno_continua_intacto_depois_da_tentativa(como, cenario):
    """A negativa não basta: confere-se que o dado dele não mudou.

    Um comando recusado que tivesse gravado algo antes de ser recusado
    apareceria como negado e teria vazado a escrita. Separado em teste próprio
    porque a sessão da Ana não enxerga a linha do Bruno — quem confere é o
    catálogo, por fora.
    """
    with como(cenario["ana"]) as ana:
        ana.negado(
            """
            insert into public.profiles (id, nome) values (%s, 'Invadido')
            on conflict (id) do update set nome = excluded.nome
            """,
            (cenario["bruno"],),
        )

    with como(cenario["bruno"]) as bruno:
        linhas = bruno.executar(
            "select nome from public.profiles where id = %s", (cenario["bruno"],)
        )
    assert linhas == [(NOME_DO_BRUNO,)]


def test_ana_nao_muda_o_proprio_id_para_o_do_bruno(como, cenario):
    """A variante de sequestro: gravar na própria linha mudando o `id`.

    É o análogo, em `profiles`, do
    `test_ana_nao_transfere_o_proprio_dispositivo_para_o_bruno`. Aqui o `id` é
    a chave primária e referencia `auth.users`, então o caminho é tentar
    inserir com o id alheio — coberto acima — ou alterar o próprio para o
    alheio, que é o que este testa.

    **Observação de método, e o motivo de este comentário existir:** escrito
    primeiro com `contar_afetadas` esperando zero, por analogia com os demais
    testes de negativa de `profiles`. Reprovou, e a mensagem é a explicação —
    *"new row violates row-level security policy"*. A diferença é qual metade
    da policy barra: quando o `using` esconde a linha, o comando afeta zero em
    silêncio; quando o `with check` reprova a linha **resultante**, o Postgres
    levanta exceção. Aqui a linha é visível (é a da própria Ana) e o que
    reprova é o `with check` — logo, exceção. A asserção foi corrigida para o
    que o banco faz, e não o contrário.
    """
    with como(cenario["ana"]) as ana:
        ana.negado(
            "update public.profiles set id = %s where id = %s",
            (cenario["bruno"], cenario["ana"]),
        )


def test_o_perfil_nasce_pelo_gatilho_e_a_idade_nasce_nula(catalogo, cenario):
    """Pré-condição da fonte de verdade, e o estado inicial de `idade`.

    Nulo é valor válido e declarado: a idade é opcional porque serve a um aviso
    de aplicabilidade (ver `docs/DECISAO-FONTE-DO-PERFIL.md` §5), e campo
    obrigatório para alimentar um aviso seria coleta desproporcional.
    """
    linhas = catalogo("select nome, idade from public.profiles order by nome")
    assert linhas == [(NOME_DA_ANA, None), (NOME_DO_BRUNO, None)]


# =====================================================================
# 2. `updated_at` que se mantém (migração 008)
# =====================================================================

def test_updated_at_se_move_na_escrita(como, cenario):
    """O gatilho, não a existência dele.

    Antes da `008` esta coluna ficava congelada em `now()` da criação, porque
    nada escrevia na tabela. Com a tabela canônica, ela passaria a afirmar
    "criado e nunca mais tocado" sobre uma linha corrigida hoje — coluna de
    data que não acompanha a escrita é pior que coluna ausente, porque parece
    informação.
    """
    with como(cenario["ana"]) as ana:
        antes = ana.executar(
            "select updated_at from public.profiles where id = %s", (cenario["ana"],)
        )[0][0]
        ana.executar(
            "update public.profiles set nome = 'Ana Maria' where id = %s",
            (cenario["ana"],),
        )
        depois = ana.executar(
            "select updated_at from public.profiles where id = %s", (cenario["ana"],)
        )[0][0]

    assert depois > antes


def test_updated_at_se_move_mesmo_sem_mudar_valor(como, cenario):
    """`set nome = nome` é escrita, e a data tem de reconhecer isso.

    Um gatilho que comparasse valores antes de tocar a data deixaria de marcar
    a tentativa de correção que não mudou nada — e "quando foi a última
    escrita" é diferente de "quando o valor mudou".
    """
    with como(cenario["ana"]) as ana:
        antes = ana.executar(
            "select updated_at from public.profiles where id = %s", (cenario["ana"],)
        )[0][0]
        ana.executar(
            "update public.profiles set nome = nome where id = %s", (cenario["ana"],)
        )
        depois = ana.executar(
            "select updated_at from public.profiles where id = %s", (cenario["ana"],)
        )[0][0]

    assert depois > antes


def test_o_gatilho_de_updated_at_nao_e_security_definer(catalogo):
    """Privilégio que não é preciso não se concede (SEC-06).

    O gatilho roda no contexto de quem escreve, e quem escreve é o dono da
    linha — o RLS já autorizou antes de o gatilho disparar. `security definer`
    aqui seria poder sobrando, e poder sobrando em função de gatilho é o tipo
    de coisa que ninguém revisa depois.
    """
    linhas = catalogo(
        """
        select p.prosecdef from pg_proc p
          join pg_namespace n on n.oid = p.pronamespace
         where n.nspname = 'public' and p.proname = 'tocar_updated_at'
        """
    )
    assert linhas, "funcao public.tocar_updated_at ausente (migracao 008 nao aplicada?)"
    assert linhas[0][0] is False


def test_o_gatilho_de_updated_at_nao_e_executavel_por_ninguem(catalogo):
    """`create function` concede EXECUTE a `PUBLIC` por padrão no PostgreSQL.

    Sem o `revoke` da `008`, criar esta função AMPLIARIA o que o papel
    `dormio_ingestao` pode executar — e foi
    `test_rls_ingestao.py::test_o_papel_executa_exatamente_tres_funcoes` que
    reprovou na primeira execução da migração, nomeando a função nova.

    Este teste é o par daquele, pelo outro lado: aquele enumera o que o papel
    de ingestão pode e reprova quando a lista cresce; este afirma que **esta**
    função não é executável por `public`, `anon`, `authenticated` nem
    `dormio_ingestao`. O gatilho continua disparando porque o Postgres confere
    o privilégio na criação do gatilho, não a cada disparo — e os dois testes
    de `updated_at` acima provam que ele dispara.
    """
    papeis = ("public", "anon", "authenticated", "dormio_ingestao")
    podem = catalogo(
        """
        select papel from unnest(%s::text[]) as papel
         where has_function_privilege(
                 papel, 'public.tocar_updated_at()', 'execute')
        """,
        (list(papeis),),
    )
    assert podem == [], f"tocar_updated_at executavel por: {[p[0] for p in podem]}"


# =====================================================================
# 3. Teto de tamanho do nome (migração 008)
# =====================================================================

def test_nome_gigante_e_recusado_pelo_banco(como, cenario):
    """O caminho que não passa por validação nenhuma do projeto.

    `authenticated` tem GRANT de UPDATE em `profiles`, e o navegador fala
    direto com o PostgREST usando a chave `anon` (pública por design). Logo, o
    teto de 120 de `perfil.py` e o do `lib/perfil.ts` **não** são o último
    portão: o titular escreve na própria linha sem passar por nenhum dos dois.
    É o mesmo raciocínio da `007` sobre a lista de campos de `dispositivos.py`.
    """
    with como(cenario["ana"]) as ana:
        ana.negado(
            "update public.profiles set nome = %s where id = %s",
            ("A" * 201, cenario["ana"]),
        )


def test_nome_no_teto_do_banco_passa(como, cenario):
    """O limite é 200 inclusive — e é MAIOR que o 120 da interface, de
    propósito: iguais, qualquer afrouxamento futuro do campo na tela viraria
    erro de constraint, que é a pior forma de descobrir uma divergência."""
    with como(cenario["ana"]) as ana:
        afetadas = ana.contar_afetadas(
            "update public.profiles set nome = %s where id = %s",
            ("A" * 200, cenario["ana"]),
        )
    assert afetadas == 1


@pytest.mark.parametrize("idade", [-1, 150, 1000])
def test_idade_fora_da_faixa_e_recusada_pelo_banco(como, cenario, idade):
    """A constraint é da `001`; o teste é novo porque antes **nada escrevia**
    na coluna, e constraint que nenhum caminho exercita é afirmação."""
    with como(cenario["ana"]) as ana:
        ana.negado(
            "update public.profiles set idade = %s where id = %s",
            (idade, cenario["ana"]),
        )


@pytest.mark.parametrize("idade", [0, 22, 149, None])
def test_idade_dentro_da_faixa_passa(como, cenario, idade):
    with como(cenario["ana"]) as ana:
        afetadas = ana.contar_afetadas(
            "update public.profiles set idade = %s where id = %s",
            (idade, cenario["ana"]),
        )
    assert afetadas == 1


# =====================================================================
# 4. A finalidade declarada viaja com o banco, não só com o repositório
# =====================================================================

def test_a_finalidade_de_idade_esta_declarada_no_proprio_esquema(catalogo):
    """`comment on column`, e não só um parágrafo em `docs/`.

    O `LGPD-04` descreve o modo de falha: *"é exatamente o tipo de estrutura
    que alguém preenche um dia porque já estava lá"*. A defesa contra isso não
    é a coluna existir com finalidade escrita num documento que pode descolar
    do esquema — é a finalidade estar legível de dentro do banco, por quem
    abrir a tabela.
    """
    linhas = catalogo(
        """
        select col_description('public.profiles'::regclass, ordinal_position)
          from information_schema.columns
         where table_schema = 'public' and table_name = 'profiles'
           and column_name = 'idade'
        """
    )
    assert linhas, "coluna public.profiles.idade ausente"
    comentario = linhas[0][0] or ""
    assert comentario, (
        "profiles.idade sem comentario: a finalidade declarada nao esta no "
        "esquema (migracao 008 nao aplicada?)"
    )
    # O que precisa estar dito: que é opcional, e que NÃO entra em cálculo.
    assert "OPCIONAL" in comentario
    assert "NAO entra em calculo" in comentario


def test_o_papel_do_metadado_esta_declarado_na_funcao_que_o_le(catalogo):
    """`handle_new_user` é o único lugar do servidor que lê o metadado.

    Declarar isso no `comment on function` é o que impede a releitura errada
    daqui a seis meses: a função parece uma cópia redundante, e é a semeadura
    da fonte de verdade.
    """
    linhas = catalogo(
        """
        select obj_description(p.oid)
          from pg_proc p join pg_namespace n on n.oid = p.pronamespace
         where n.nspname = 'public' and p.proname = 'handle_new_user'
        """
    )
    assert linhas, "funcao public.handle_new_user ausente"
    comentario = linhas[0][0] or ""
    assert "Semeia" in comentario, (
        "handle_new_user sem o comentario da 008: o papel dela nao esta "
        "declarado no esquema"
    )
