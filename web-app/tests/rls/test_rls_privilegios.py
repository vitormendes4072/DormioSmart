"""Privilégios padrão do Supabase (SEC-12).

No Supabase, todo objeto que o `postgres` cria em `public` nasce com privilégio
NOMINAL para `anon` e `authenticated` — medido na produção em 2026-10-28
(`pg_default_acl`). As migrações 005–008 faziam `revoke ... from public`, que
não alcança grant nominal, e `anon` executava as funções de ingestão.

A 009 revoga o que já existia e muda o padrão para funções FUTURAS. Os testes
das outras pastas cobrem o que existe hoje; este cobre o que ainda não existe:
uma migração nova que crie função não pode nascer executável pela chave
pública. Sem ele, desfazer a parte 4 da 009 passaria em silêncio até a próxima
migração com função — que é exatamente como o defeito original passou.
"""


def test_funcao_nova_nao_nasce_executavel_por_anon(esquema, _conexao_dona):
    """Uma função nova, criada como as migrações criam, não é executável por `anon`.

    "Como as migrações criam" inclui a convenção do projeto: toda função é
    seguida de `revoke all ... from public` (005–008 fazem). Isso é necessário
    porque o PRÓPRIO Postgres dá EXECUTE a PUBLIC em toda função, e `anon` está
    em PUBLIC — padrão global, que não se revoga por esquema. O que a 009 tira
    é o grant NOMINAL que o Supabase acrescenta por cima, e que o `revoke from
    public` não alcançava. Medido em 28/10: sem o revoke da convenção, a função
    nasce executável por `anon` mesmo com a 009 — o limite está aqui escrito.
    """
    with _conexao_dona.cursor() as cursor:
        cursor.execute("begin")
        try:
            cursor.execute(
                "create function public._sec12_funcao_nova() returns int "
                "language sql as 'select 1'"
            )
            cursor.execute("revoke all on function public._sec12_funcao_nova() from public")
            cursor.execute(
                "select has_function_privilege('anon', 'public._sec12_funcao_nova()', 'execute'), "
                "       has_function_privilege('authenticated', 'public._sec12_funcao_nova()', 'execute')"
            )
            anon, authenticated = cursor.fetchone()
        finally:
            cursor.execute("rollback")
    assert not anon, "função nova nasce executável por `anon` — a parte 4 da 009 foi desfeita"
    assert not authenticated, (
        "função nova nasce executável por `authenticated` — conceder tem de ser explícito, "
        "na migração que cria a função"
    )


def test_a_base_reproduz_os_padroes_do_supabase_para_tabela(esquema, _conexao_dona):
    """Controle do próprio cenário: sem os padrões, os testes de `anon` passariam no vazio.

    Foi assim até 28/10. Tabela nova TEM de nascer com privilégio para `anon` —
    é o comportamento do Supabase que a 009 não muda (a proteção das tabelas é o
    RLS) e que a base de teste precisa reproduzir para os outros testes valerem.
    """
    with _conexao_dona.cursor() as cursor:
        cursor.execute("begin")
        try:
            cursor.execute("create table public._sec12_tabela_nova (id int)")
            cursor.execute(
                "select has_table_privilege('anon', 'public._sec12_tabela_nova', 'select')"
            )
            (anon_le,) = cursor.fetchone()
        finally:
            cursor.execute("rollback")
    assert anon_le, (
        "a base de teste deixou de reproduzir os privilégios padrão do Supabase "
        "(tests/rls/esquema_base.sql, bloco 1b) — os testes de `anon` voltariam a passar no vazio"
    )
