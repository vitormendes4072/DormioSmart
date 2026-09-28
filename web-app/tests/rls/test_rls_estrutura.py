"""O RLS está ligado e as policies são as esperadas (SEC-05).

── POR QUE ISTO É SEPARADO DOS TESTES DE ACESSO ─────────────────────────

`test_rls_isolamento.py` prova que o que existe hoje se comporta bem. Não pega
duas classes de regressão:

  1. **Tabela nova sem RLS.** Uma migração que crie `sessoes_de_captacao` e
     esqueça o `enable row level security` não faz teste de acesso nenhum
     falhar — não há teste pedindo dado de uma tabela que ninguém escreveu
     ainda. A tabela nasce aberta e fica aberta.

  2. **Policy larga acrescentada.** Um `using (true)` "temporário" para
     depurar, ou um `to public` por descuido, abre tudo. Os testes de acesso
     começariam a falhar — mas só os que cobrem a tabela afetada, e a falha
     apareceria como "a Ana viu demais", que é fácil de confundir com problema
     de fixture.

Os testes daqui leem o catálogo do Postgres e afirmam o formato do esquema.
São eles que transformam "o RLS está certo" numa invariante verificada a cada
execução, e não num estado que foi verdadeiro uma vez.
"""
import pytest

# Tabelas que carregam dado pessoal e por isso exigem RLS.
TABELAS_PESSOAIS = ("profiles", "devices", "sleep_data")

# Contagem esperada de policies, conforme o bloco de VERIFICAÇÃO da 001.
# Mudar este número é uma decisão de segurança; o teste existe para que a
# mudança seja explícita e revisada.
POLICIES_ESPERADAS = {
    "profiles": {"SELECT", "INSERT", "UPDATE", "DELETE"},
    "devices": {"SELECT", "INSERT", "UPDATE", "DELETE"},
    # SELECT e DELETE, e deliberadamente NEM INSERT NEM UPDATE.
    #
    #   · sem INSERT: a escrita de leitura de sensor e exclusiva do
    #     dispositivo, pela funcao `registrar_leitura` (SEC-06). Cliente nao
    #     fabrica medicao.
    #   · sem UPDATE: apagar e um direito do titular (LGPD art. 18, V);
    #     reescrever uma medicao nao e. Apagar e visivel — a linha sai.
    #     Editar e invisivel, e destruiria o valor probatorio do conjunto.
    #   · com DELETE desde a 006: sem ele o titular nao tinha caminho nenhum
    #     para eliminar o proprio dado.
    "sleep_data": {"SELECT", "DELETE"},
}


@pytest.mark.parametrize("tabela", TABELAS_PESSOAIS)
def test_rls_habilitado(catalogo, tabela):
    linhas = catalogo(
        "select rowsecurity from pg_tables where schemaname = 'public' and tablename = %s",
        (tabela,),
    )
    assert linhas, f"tabela public.{tabela} nao existe"
    assert linhas[0][0] is True, (
        f"RLS DESLIGADO em public.{tabela}. Com os GRANTs do Supabase para "
        "'authenticated', isso significa acesso total de qualquer conta a "
        "todo o dado de todo mundo."
    )


def test_toda_tabela_de_dado_pessoal_tem_rls(catalogo):
    """Rede para tabela nova.

    Qualquer tabela em `public` com coluna de posse (`user_id`, ou `id` que
    referencia `auth.users`) precisa de RLS. Uma tabela nova de sessões de
    captação, de metas de sono, de exportações — qualquer uma — cai aqui se
    nascer aberta, sem que ninguém precise lembrar de escrever o teste.
    """
    abertas = catalogo(
        """
        select t.tablename
          from pg_tables t
         where t.schemaname = 'public'
           and t.rowsecurity is false
           and exists (
               select 1 from information_schema.columns c
                where c.table_schema = 'public'
                  and c.table_name = t.tablename
                  and c.column_name in ('user_id', 'usuario_id', 'owner_id', 'dono_id')
           )
        """
    )
    assert abertas == [], (
        "tabela com coluna de posse e SEM RLS: "
        + ", ".join(linha[0] for linha in abertas)
    )


@pytest.mark.parametrize("tabela", TABELAS_PESSOAIS)
def test_comandos_cobertos_por_policy_sao_os_esperados(catalogo, tabela):
    linhas = catalogo(
        "select cmd from pg_policies where schemaname = 'public' and tablename = %s",
        (tabela,),
    )
    comandos = {linha[0] for linha in linhas}
    assert comandos == POLICIES_ESPERADAS[tabela], (
        f"o conjunto de comandos com policy em public.{tabela} mudou.\n"
        f"esperado: {sorted(POLICIES_ESPERADAS[tabela])}\n"
        f"encontrado: {sorted(comandos)}\n"
        "Se a mudanca e intencional, atualize POLICIES_ESPERADAS e explique no "
        "commit o que passou a ser permitido e a quem."
    )


def test_nenhuma_policy_vale_para_todos_os_papeis(catalogo):
    """`to public` alcança `anon` também — e `anon` é a chave do bundle."""
    largas = catalogo(
        """
        select tablename, policyname, roles::text
          from pg_policies
         where schemaname = 'public'
           and roles::text in ('{public}', '{anon}')
        """
    )
    assert largas == [], (
        "policy valida para 'public' ou 'anon': "
        + "; ".join(f"{t}.{p} -> {r}" for t, p, r in largas)
    )


def test_nenhuma_policy_tem_qualificador_permissivo(catalogo):
    """Pega o `using (true)` e o `with check (true)`.

    Uma policy com qualificador verdadeiro é indistinguível de RLS desligado
    para o comando que ela cobre, mas `rowsecurity` continua `true` e o painel
    do Supabase continua mostrando a tabela como protegida. É a forma mais
    silenciosa de abrir o banco.
    """
    permissivas = catalogo(
        """
        select tablename, policyname, coalesce(qual, ''), coalesce(with_check, '')
          from pg_policies
         where schemaname = 'public'
           and (qual in ('true', '(true)') or with_check in ('true', '(true)'))
        """
    )
    assert permissivas == [], (
        "policy com qualificador permissivo: "
        + "; ".join(f"{t}.{p}" for t, p, _, _ in permissivas)
    )


@pytest.mark.parametrize("tabela", TABELAS_PESSOAIS)
def test_toda_policy_amarra_no_auth_uid(catalogo, tabela):
    """Cada policy tem que comparar posse com `auth.uid()`.

    É a forma positiva do teste anterior: em vez de listar os qualificadores
    ruins conhecidos, exige o que o correto tem. Uma policy que compare com
    qualquer outra coisa — uma tabela de permissões, um papel, um e-mail — pode
    estar certa, mas não é o modelo deste sistema e precisa de revisão.
    """
    linhas = catalogo(
        """
        select policyname, coalesce(qual, '') || ' ' || coalesce(with_check, '')
          from pg_policies
         where schemaname = 'public' and tablename = %s
        """,
        (tabela,),
    )
    assert linhas, f"public.{tabela} tem RLS mas nenhuma policy"
    for nome, expressao in linhas:
        assert "auth.uid()" in expressao, (
            f"policy {tabela}.{nome} nao compara posse com auth.uid(): {expressao!r}"
        )


def test_policies_de_update_tem_with_check(catalogo):
    """`using` sem `with check` permite mover a linha para outro dono.

    O `using` decide quais linhas dá para alterar; o `with check` decide como
    elas podem ficar DEPOIS. Sem o segundo, o usuário atualiza a própria linha
    trocando o `user_id` — e entrega o próprio dispositivo para outra conta, ou
    rouba a si mesmo do próprio painel. `test_ana_nao_transfere_o_proprio_
    dispositivo_para_o_bruno` cobre o caso concreto; este cobre a classe.
    """
    sem_check = catalogo(
        """
        select tablename, policyname
          from pg_policies
         where schemaname = 'public' and cmd = 'UPDATE' and with_check is null
        """
    )
    assert sem_check == [], (
        "policy de UPDATE sem with_check: "
        + "; ".join(f"{t}.{p}" for t, p in sem_check)
    )


def test_trigger_de_criacao_de_perfil_esta_blindado(catalogo):
    """`handle_new_user` é `security definer`: roda com poder do dono.

    Função `security definer` sem `search_path` fixo é escalada de privilégio
    clássica — quem controla o `search_path` escolhe qual função a definer
    chama. A 001 já faz `set search_path = ''`; o teste impede que uma edição
    futura tire isso.
    """
    linhas = catalogo(
        """
        select p.prosecdef, coalesce(array_to_string(p.proconfig, ','), '')
          from pg_proc p join pg_namespace n on n.oid = p.pronamespace
         where n.nspname = 'public' and p.proname = 'handle_new_user'
        """
    )
    assert linhas, "funcao public.handle_new_user ausente"
    definer, config = linhas[0]
    assert definer is True
    assert "search_path=" in config.replace(" ", ""), (
        "handle_new_user e SECURITY DEFINER sem search_path fixo: "
        f"proconfig = {config!r}"
    )
