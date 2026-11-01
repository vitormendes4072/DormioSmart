#!/usr/bin/env python3
"""Confere a consulta de diagnóstico das migrações e a ordem segura de aplicá-las.

── POR QUE EXISTE ────────────────────────────────────────────────────────

As migrações deste projeto são aplicadas à mão no SQL Editor do Supabase, e nada
registra quais rodaram. Em 2026-10-28 a única forma de saber o estado do banco
de produção foi `migrations/DIAGNOSTICO-migracoes-aplicadas.sql`, que procura no
catálogo as marcas que cada migração deixa. Uma consulta assim pode afirmar
"aplicada" sem estar — e ela decide o que se aplica em produção. Por isso é
conferida aqui, contra bancos montados de propósito.

Duas verificações, cada uma num banco novo por cenário:

  (1) DIAGNÓSTICO — aplica 001, 003…010 uma a uma; a cada passo, a consulta
      tem de marcar `true` exatamente as aplicadas até ali. E a parte da 002
      (dado, não esquema) tem de contar uma leitura sem dono e voltar a zero
      depois do backfill.

  (2) ORDEM — as operações que o código de `main` (produção até o release)
      faz no banco, em três estados: A = 001, 003, 004 (a produção em 28/10);
      B = A + 005, 006, 008, 009; C = B + 007. Exige A = B (as quatro podem entrar
      antes do release) e que C quebre EXATAMENTE as duas operações que usam
      `devices.token_hash` (por isso a 007 só entra com o release). O C é o
      controle: se ele não quebrasse nada, a verificação não estaria vendo.

Limites, ditos para não serem descobertos depois: é Postgres puro com os papéis
e GRANTs imitando o Supabase (`tests/rls/esquema_base.sql` e
`grants_pos_migracao.sql`), sem o PostgREST na frente; e (2) cobre as operações
que o código de `main` faz no banco, não chamadas que o frontend de `main` faça
além delas.

    DORMIO_RLS_DATABASE_URL=postgresql://postgres:...@127.0.0.1:5432/qualquer \\
        python web-app/tests/migracoes/verificar_migracoes.py

Precisa de um usuário que crie bancos (o do CI e o do Postgres de teste são
superusuários). Cria e apaga bancos `migr_<pid>_*`; não toca no banco da URL.
Recusa host remoto, pela mesma razão que `tests/rls/conftest.py`.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import psycopg2

AQUI = Path(__file__).resolve().parent
WEB = AQUI.parent.parent
MIG = WEB / "migrations"
RLS = WEB / "tests" / "rls"
DIAG = MIG / "DIAGNOSTICO-migracoes-aplicadas.sql"
ORDEM = ["001", "003", "004", "005", "006", "007", "008", "009", "010", "011"]
ARQ = {p.name[:3]: p for p in MIG.glob("0[0-9][0-9]_*.sql")}

ANA = "00000000-0000-0000-0000-00000000000a"
NOVO = "00000000-0000-0000-0000-00000000000b"
DISP = "00000000-0000-0000-0000-0000000000d1"


def url_base() -> str:
    url = os.environ.get("DORMIO_RLS_DATABASE_URL", "")
    if not url:
        sys.exit("ERRO: defina DORMIO_RLS_DATABASE_URL (Postgres descartável).")
    host = urlparse(url).hostname or ""
    if host not in ("127.0.0.1", "localhost", "::1") or "supabase" in url:
        sys.exit(f"ERRO: recuso rodar contra host remoto ({host}). Só Postgres local.")
    return url


def com_banco(url: str, nome: str) -> str:
    p = urlparse(url)
    return urlunparse(p._replace(path="/" + nome))


class Bancos:
    """Cria bancos descartáveis e garante que todos saiam no fim."""

    def __init__(self, url):
        self.admin = com_banco(url, "postgres")
        self.criados = []

    def novo(self, sufixo):
        nome = f"migr_{os.getpid()}_{sufixo}"
        a = psycopg2.connect(self.admin)
        a.autocommit = True
        a.cursor().execute(f'drop database if exists "{nome}"')
        a.cursor().execute(f'create database "{nome}"')
        a.close()
        self.criados.append(nome)
        c = psycopg2.connect(com_banco(self.admin, nome))
        c.autocommit = True
        return c

    def limpar(self):
        a = psycopg2.connect(self.admin)
        a.autocommit = True
        for nome in self.criados:
            # `with (force)` derruba conexões que um erro no meio tenha
            # deixado abertas; sem ele, um cenário que falha deixa o banco
            # para trás no servidor (aconteceu na primeira execução).
            a.cursor().execute(f'drop database if exists "{nome}" with (force)')
        a.close()


def rodar(cur, caminho):
    cur.execute(caminho.read_text(encoding="utf-8"))


def montar(bancos, sufixo, migracoes, dado_antigo=False):
    c = bancos.novo(sufixo)
    cur = c.cursor()
    rodar(cur, RLS / "esquema_base.sql")
    antes = [m for m in migracoes if m in ("001", "003", "004")]
    depois = [m for m in migracoes if m not in antes]
    for m in antes:
        rodar(cur, ARQ[m])
    # Os GRANTs das tabelas que a 001 cria entram UMA vez, aqui — como na
    # produção, onde elas existem desde agosto. Reaplicá-los DEPOIS das
    # migrações novas desfaria qualquer `revoke` que uma delas fizesse, e a
    # verificação (2) não veria uma migração que tira privilégio do código de
    # main (medido em 28/10: a sabotagem passava). O que as migrações novas
    # criam herda os privilégios padrão de `esquema_base.sql`, como no Supabase.
    if "001" in antes:
        rodar(cur, RLS / "grants_pos_migracao.sql")
    if dado_antigo:
        # O que existe em produção antes das migrações novas: uma conta e um
        # dispositivo pareado pelo caminho antigo (token_hash em devices).
        cur.execute("insert into auth.users (id, email) values (%s, 'ana@exemplo.com')", (ANA,))
        cur.execute("insert into public.devices (id, user_id, nome, tipo, token_hash) "
                    "values (%s, %s, 'travesseiro', 'travesseiro', 'hash-antigo')", (DISP, ANA))
        cur.execute("insert into public.sleep_data (user_id, device_id) values (%s, %s)", (ANA, DISP))
    for m in depois:
        rodar(cur, ARQ[m])
    return c


def diagnostico(cur):
    cur.execute(DIAG.read_text(encoding="utf-8"))
    return {linha[0]: linha for linha in cur.fetchall()}


# ── (1) a consulta de diagnóstico ────────────────────────────────────────
def verificar_diagnostico(bancos) -> list[str]:
    erros = []
    for k in range(len(ORDEM) + 1):
        aplicadas = ORDEM[:k]
        c = montar(bancos, f"diag{k}", aplicadas)
        res = diagnostico(c.cursor())
        marcas = []
        for m in ORDEM:
            obtido, esperado = res[m][2], m in aplicadas
            marcas.append(f"{m}:{'T' if obtido else 'F'}")
            if obtido is not esperado:
                erros.append(f"diagnóstico, aplicadas até {aplicadas[-1] if aplicadas else 'nenhuma'}: "
                             f"{m} saiu {obtido}, esperado {esperado} ({res[m][3]}; falta: {res[m][4]})")
        print(f"  aplicadas até {aplicadas[-1] if aplicadas else 'nenhuma':>7}: {' '.join(marcas)}")
        c.close()

    c = montar(bancos, "diag002", ORDEM)
    cur = c.cursor()
    cur.execute("insert into public.sleep_data default values")
    com_orfa = diagnostico(cur)["002"][3]
    cur.execute("insert into auth.users (id, email) values (%s, 'b@exemplo.com')", (ANA,))
    cur.execute("update public.sleep_data set user_id = %s where user_id is null", (ANA,))
    sem_orfa = diagnostico(cur)["002"][3]
    print(f"  002: com uma leitura sem dono -> {com_orfa!r}; depois do backfill -> {sem_orfa!r}")
    if not com_orfa.startswith("1 "):
        erros.append(f"diagnóstico da 002 não contou a leitura sem dono: {com_orfa!r}")
    if not sem_orfa.startswith("0 "):
        erros.append(f"diagnóstico da 002 não voltou a zero: {sem_orfa!r}")
    c.close()

    # A ordem REAL da produção não é a numérica: a 009 entra antes da 007
    # (a 007 espera o release). Nessa ordem, `device_tokens` e
    # `parear_dispositivo` nascem DEPOIS da 009 e dependem das revogações da
    # própria 007 — que é o que se confere aqui, além de tudo terminar `true`.
    # A 010 (DATA-07b, 30/10) entra depois de tudo, antes do release que a usa.
    # A 011 (DATA-08, 01/11) só mexe no banco; o backend não muda.
    ordem_real = ["001", "003", "004", "005", "006", "008", "009", "007", "010", "011"]
    c = montar(bancos, "diagreal", ordem_real)
    cur = c.cursor()
    res = diagnostico(cur)
    falsas = [m for m in ORDEM if res[m][2] is not True]
    cur.execute("""select has_function_privilege('anon', 'public.parear_dispositivo(text,text,text)', 'execute'),
                          exists (select 1 from information_schema.table_privileges
                                   where table_schema = 'public' and table_name = 'device_tokens'
                                     and grantee in ('anon', 'authenticated'))""")
    anon_pareia, cliente_na_tabela = cur.fetchone()
    print(f"  ordem real ({' → '.join(ordem_real)}): falsas={falsas or 'nenhuma'}, "
          f"anon pareia={anon_pareia}, cliente em device_tokens={cliente_na_tabela}")
    if falsas:
        erros.append(f"ordem real da produção: diagnóstico com {falsas} não aplicadas")
    if anon_pareia or cliente_na_tabela:
        erros.append("ordem real da produção: a 007 depois da 009 deixa `anon` em "
                     f"parear_dispositivo={anon_pareia} ou cliente em device_tokens={cliente_na_tabela}")
    c.close()
    return erros


# ── (2) a ordem segura em relação ao código de main ──────────────────────
OPERACOES = [
    ("svc: insere leitura", "service_role", None,
     f"insert into public.sleep_data (user_id, device_id) values ('{ANA}', '{DISP}') returning id"),
    ("svc: /health", "service_role", None,
     "select created_at from public.sleep_data limit 1"),
    ("svc: dispositivo por token_hash", "service_role", None,
     "select id, user_id, revoked_at from public.devices where token_hash = 'hash-antigo'"),
    ("svc: atualiza last_seen_at", "service_role", None,
     f"update public.devices set last_seen_at = now() where id = '{DISP}' returning id"),
    ("usuária: lê as próprias leituras", "authenticated", ANA,
     f"select id from public.sleep_data where user_id = '{ANA}'"),
    ("usuária: lista os dispositivos", "authenticated", ANA,
     "select id, nome from public.devices"),
    ("usuária: pareia (insert direto em devices)", "authenticated", ANA,
     f"insert into public.devices (user_id, nome, tipo, token_hash) "
     f"values ('{ANA}', 'novo', 'celular', 'hash-novo') returning id"),
    ("usuária: lê o próprio perfil", "authenticated", ANA,
     "select id, nome from public.profiles"),
    ("usuária: edita o próprio nome", "authenticated", ANA,
     f"update public.profiles set nome = 'Ana' where id = '{ANA}' returning id"),
    ("cadastro cria o perfil (gatilho)", "supabase_auth_admin", None,
     f"insert into auth.users (id, email) values ('{NOVO}', 'novo@exemplo.com') returning id"),
]
QUEBRADAS_PELA_007 = {"svc: dispositivo por token_hash", "usuária: pareia (insert direto em devices)"}


def executar_operacoes(conn):
    cur = conn.cursor()
    # O Supabase insere em auth.users com este papel, não com superusuário.
    cur.execute("do $$ begin if not exists (select 1 from pg_roles where rolname = "
                "'supabase_auth_admin') then create role supabase_auth_admin nologin; end if; end $$")
    cur.execute("grant usage on schema auth to supabase_auth_admin")
    cur.execute("grant insert, select on auth.users to supabase_auth_admin")
    conn.autocommit = False
    saida = {}
    for rotulo, papel, sub, sql in OPERACOES:
        cur = conn.cursor()
        try:
            if sub:
                cur.execute("select set_config('request.jwt.claims', %s, true)",
                            (json.dumps({"sub": sub, "role": papel}),))
            cur.execute(f"set local role {papel}")
            cur.execute(sql)
            resultado = f"ok, {cur.rowcount} linha(s)"
            if rotulo.startswith("cadastro"):
                cur.execute("reset role")
                cur.execute("select count(*) from public.profiles where id = %s", (NOVO,))
                resultado += f", perfil criado={cur.fetchone()[0]}"
            saida[rotulo] = resultado
        except psycopg2.Error as e:
            saida[rotulo] = "ERRO: " + str(e).splitlines()[0][:80]
        conn.rollback()
    return saida


def verificar_ordem(bancos) -> list[str]:
    res = {}
    for nome, extras in (("A", ()), ("B", ("005", "006", "008", "009")),
                         ("C", ("005", "006", "008", "009", "007"))):
        c = montar(bancos, f"ordem{nome}", ["001", "003", "004", *extras], dado_antigo=True)
        res[nome] = executar_operacoes(c)
        c.close()
    erros = []
    for rotulo, *_ in OPERACOES:
        a, b, c_ = res["A"][rotulo], res["B"][rotulo], res["C"][rotulo]
        print(f"  {rotulo:44} A: {a[:22]:22} B: {b[:22]:22} C: {c_[:40]}")
        if not a.startswith("ok"):
            erros.append(f"ordem: no estado da produção, '{rotulo}' já falha: {a}")
        if a != b:
            erros.append(f"ordem: 005/006/008/009 mudam '{rotulo}' para o código de main: {a} -> {b}")
        quebrou = c_ != b
        if quebrou != (rotulo in QUEBRADAS_PELA_007):
            erros.append(f"ordem: a 007 {'quebrou' if quebrou else 'NÃO quebrou'} '{rotulo}' "
                         f"({b} -> {c_}); o esperado é quebrar exatamente "
                         f"{sorted(QUEBRADAS_PELA_007)}")
    return erros


def main() -> int:
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(encoding="utf-8")
    bancos = Bancos(url_base())
    try:
        print("(1) a consulta de diagnóstico, migração a migração")
        erros = verificar_diagnostico(bancos)
        print("(2) as operações do código de main, antes e depois de cada grupo")
        erros += verificar_ordem(bancos)
    finally:
        bancos.limpar()
    if erros:
        print("\nREPROVADO:", file=sys.stderr)
        for e in erros:
            print("  -", e, file=sys.stderr)
        return 1
    print("\nOK — o diagnóstico acerta os 11 estados e a 002; 005/006/008/009 não mudam "
          "nada para o código de main; a 007 quebra exatamente as 2 operações de token_hash.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
