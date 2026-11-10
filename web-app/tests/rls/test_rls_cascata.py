"""Apagar o usuário direto em `auth.users` leva as leituras junto (DATA-12, migração 015).

É o que o painel do Supabase faz em Authentication → Delete user. Sem a 015,
a produção recusa essa exclusão por chave estrangeira: a coluna `user_id` foi
criada pelo painel sem cascata, e a 001 não a recriou (`add column if not
exists`). O esquema de teste reproduz isso desde o DATA-12; sem a 015 na lista
de migrações, estes testes caem.

A eliminação pelo app (`apagar_minha_conta`) não depende da cascata — apaga as
leituras antes — e é coberta por `test_rls_eliminacao.py`.
"""


def _contar(sessao, sql, args):
    sessao.cursor.execute(sql, args)
    return sessao.cursor.fetchone()[0]


def test_apagar_o_usuario_direto_leva_as_leituras(como, cenario):
    with como(cenario["ana"]) as sessao:
        sessao.cursor.execute("set local role postgres")
        antes = _contar(sessao, "select count(*) from public.sleep_data where user_id = %s",
                        (cenario["ana"],))
        assert antes >= 1, "o cenario precisa de leitura da Ana para o teste valer"

        sessao.cursor.execute("delete from auth.users where id = %s", (cenario["ana"],))

        depois = _contar(sessao, "select count(*) from public.sleep_data where user_id = %s",
                         (cenario["ana"],))
        assert depois == 0, "as leituras da Ana sobreviveram a exclusao da conta"


def test_apagar_o_usuario_direto_nao_toca_no_bruno(como, cenario):
    with como(cenario["ana"]) as sessao:
        sessao.cursor.execute("set local role postgres")
        do_bruno = _contar(sessao, "select count(*) from public.sleep_data where user_id = %s",
                           (cenario["bruno"],))
        sessao.cursor.execute("delete from auth.users where id = %s", (cenario["ana"],))
        assert _contar(sessao, "select count(*) from public.sleep_data where user_id = %s",
                       (cenario["bruno"],)) == do_bruno


def test_a_chave_de_user_id_tem_cascata(catalogo):
    linhas = catalogo("""
        select confdeltype::text from pg_constraint
         where conname = 'sleep_data_user_id_fkey'
           and conrelid = 'public.sleep_data'::regclass
    """)
    assert linhas, "sleep_data_user_id_fkey nao existe"
    linha = linhas[0]
    assert linha[0] == "c", f"sleep_data_user_id_fkey sem on delete cascade (confdeltype={linha[0]!r})"
