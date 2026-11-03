"""Migração 012 e a consulta agregada da idade — LGPD-05 e LGPD-06 (03/11).

Postgres de verdade, como o resto desta pasta: a restrição e a supressão de
faixas pequenas só existem no banco, e um mock não exercitaria nenhuma das duas.

O que se trava:
  * a restrição recusa idade 17 e aceita 18 e nulo (LGPD-05);
  * a trava da 012 PARA, sem alterar dado, se já houver menor de 18;
  * a consulta agregada nunca mostra faixa com menos de 5 contas, e não tem
    linha de total (LGPD-06);
  * o comentário da coluna declara as duas finalidades.
"""

from __future__ import annotations

from pathlib import Path

import psycopg2
import psycopg2.errors
import pytest

MIGRACOES = Path(__file__).resolve().parents[2] / "migrations"
CONSULTA = MIGRACOES / "CONSULTA-publico-por-faixa.sql"
M012 = MIGRACOES / "012_idade_minima_18.sql"


@pytest.fixture
def conexao_admin(url_do_banco, esquema, cenario):
    """Conexão de dono, em TRANSAÇÃO, desfeita no fim de cada teste.

    O dono ignora RLS — e aqui isso é o certo: o que se testa é a restrição e a
    consulta, não policy. A `_conexao_dona` da conftest é autocommit e
    sujaria o cenário dos outros testes.
    """
    conexao = psycopg2.connect(url_do_banco)
    yield conexao
    conexao.rollback()
    conexao.close()


def _perfis(cur, idades):
    """Cria uma conta e um perfil por idade dada. Devolve os ids."""
    ids = []
    for i, idade in enumerate(idades):
        uid = f"00000000-0000-4000-8000-{i:012d}"
        cur.execute("insert into auth.users (id, email) values (%s, %s) on conflict do nothing",
                    (uid, f"p{i}@exemplo.com"))
        cur.execute("insert into public.profiles (id, idade) values (%s, %s) "
                    "on conflict (id) do update set idade = excluded.idade", (uid, idade))
        ids.append(uid)
    return ids


def test_idade_17_e_recusada_pelo_banco(conexao_admin):
    with conexao_admin.cursor() as cur:
        with pytest.raises(psycopg2.errors.CheckViolation):
            _perfis(cur, [17])
    conexao_admin.rollback()


@pytest.mark.parametrize("idade", [18, 149, None])
def test_idade_18_e_nula_passam(conexao_admin, idade):
    with conexao_admin.cursor() as cur:
        _perfis(cur, [idade])
    conexao_admin.rollback()


def test_a_trava_para_sem_alterar_dado(conexao_admin):
    """Com um menor de 18 gravado (restrição antiga de volta), a 012 aborta
    com a contagem — e o perfil continua lá, intacto."""
    with conexao_admin.cursor() as cur:
        cur.execute("alter table public.profiles drop constraint profiles_idade_maioridade")
        cur.execute("alter table public.profiles add constraint profiles_idade_check "
                    "check (idade is null or (idade >= 0 and idade < 150))")
        (uid,) = _perfis(cur, [15])
        cur.execute("savepoint antes")
        sql = M012.read_text(encoding="utf-8").replace("begin;", "").replace("commit;", "")
        with pytest.raises(psycopg2.errors.RaiseException, match="LGPD-05: 1 perfil"):
            cur.execute(sql)
        cur.execute("rollback to savepoint antes")
        cur.execute("select idade from public.profiles where id = %s", (uid,))
        assert cur.fetchone()[0] == 15
    conexao_admin.rollback()


def _consulta(cur):
    cur.execute(CONSULTA.read_text(encoding="utf-8"))
    return dict(cur.fetchall())


def test_consulta_suprime_faixa_pequena_e_mostra_as_grandes(conexao_admin):
    with conexao_admin.cursor() as cur:
        cur.execute("delete from public.profiles")
        _perfis(cur, [20, 21] + [30] * 6 + [None] * 5)
        faixas = _consulta(cur)
    conexao_admin.rollback()
    assert faixas["18 a 24"] == "menos de 5"
    assert faixas["25 a 34"] == "6"
    assert faixas["não informada"] == "5"
    assert faixas["65 ou mais"] == "menos de 5"   # zero também é suprimido


def test_consulta_nao_tem_total_nem_idade_individual(conexao_admin):
    with conexao_admin.cursor() as cur:
        cur.execute("delete from public.profiles")
        _perfis(cur, [40] * 7)
        cur.execute(CONSULTA.read_text(encoding="utf-8"))
        colunas = [d[0] for d in cur.description]
        linhas = cur.fetchall()
    conexao_admin.rollback()
    assert colunas == ["faixa", "contas"]
    assert len(linhas) == 7
    assert not any("total" in str(f).lower() for f, _ in linhas)


def test_o_comentario_declara_as_duas_finalidades(catalogo):
    linhas = catalogo(
        "select col_description('public.profiles'::regclass, ordinal_position) "
        "from information_schema.columns where table_schema = 'public' "
        "and table_name = 'profiles' and column_name = 'idade'")
    comentario = linhas[0][0]
    assert "a partir de 18" in comentario
    assert "SO DE FORMA AGREGADA" in comentario
    assert "NAO entra em calculo" in comentario
