#!/usr/bin/env python3
"""Verificação por mutação da suíte de RLS (SEC-05).

── POR QUE ISTO EXISTE ──────────────────────────────────────────────────

Uma suíte de segurança que nunca falhou não provou nada. É perfeitamente
possível escrever 90 testes de RLS que passam num banco sem RLS — basta um
GRANT faltando, uma fixture vazia, uma claim mal montada. O resultado é o pior
possível: o relatório verde que se queria ver, sem a garantia que ele afirma.

Este script sabota o esquema de propósito, de um jeito por vez, e confere que a
suíte ACUSA cada sabotagem. Um sabotador que passe despercebido é uma regressão
da suíte — e vem antes de qualquer outro trabalho.

Rodar depois de TODA mudança de esquema (migração nova, policy nova, GRANT
novo). O custo é de segundos.

── USO ──────────────────────────────────────────────────────────────────

    export DORMIO_RLS_DATABASE_URL="postgresql://postgres@127.0.0.1:5433/postgres"
    python tests/rls/verificar_por_mutacao.py

    # um só, para investigar
    python tests/rls/verificar_por_mutacao.py --apenas rls_desligado

A sabotagem é aplicada acrescentando SQL ao fim de `grants_pos_migracao.sql`
numa CÓPIA da árvore, em /tmp. O repositório não é tocado.
"""
import argparse
import pathlib
import shutil
import subprocess
import sys
import tempfile

AQUI = pathlib.Path(__file__).resolve().parent
WEB_APP = AQUI.parent.parent
ARQUIVO_ALVO = pathlib.Path("tests/rls/grants_pos_migracao.sql")

# ---------------------------------------------------------------------
# Os sabotadores.
#
# `minimo` é quantos testes devem cair, no mínimo. Não é o número exato de
# propósito: acrescentar teste novo aumentaria a contagem e faria este script
# falhar por motivo errado. O que importa é que NÃO seja zero — e, onde a
# sabotagem é específica, que o teste NOMEADO em `exige` esteja entre os que
# caem, para que a suíte não acuse por acidente.
# ---------------------------------------------------------------------
SABOTADORES = {
    # --- SEC-05: o RLS por dono ---
    "rls_desligado": dict(
        descricao="RLS desligado em sleep_data",
        sql="alter table public.sleep_data disable row level security;",
        minimo=10,
        exige="test_anon_nao_le_nada",
    ),
    "policy_permissiva": dict(
        descricao="policy using(true) em sleep_data",
        sql="create policy sd_tudo on public.sleep_data for select to authenticated using (true);",
        minimo=5,
        exige="test_nenhuma_policy_tem_qualificador_permissivo",
    ),
    "update_sem_with_check": dict(
        descricao="devices_update_own sem with check",
        sql="""
            drop policy devices_update_own on public.devices;
            create policy devices_update_own on public.devices for update
                to authenticated using (user_id = (select auth.uid()));
        """,
        minimo=1,
        exige="test_policies_de_update_tem_with_check",
    ),
    "policy_para_anon": dict(
        descricao="policy de select para anon em profiles",
        sql="create policy prof_anon on public.profiles for select to anon using (true);",
        minimo=3,
        exige="test_anon_nao_le_nada",
    ),
    "insert_liberado": dict(
        descricao="insert liberado em sleep_data para authenticated",
        sql="""
            create policy sd_insert on public.sleep_data for insert
                to authenticated with check (user_id = (select auth.uid()));
        """,
        minimo=2,
        exige="test_ana_nao_fabrica_leitura_nem_no_proprio_nome",
    ),
    "tabela_nova_sem_rls": dict(
        descricao="tabela nova com user_id e sem RLS",
        sql="""
            create table public.sessoes_de_captacao (
                id bigserial primary key,
                user_id uuid references auth.users(id),
                inicio timestamptz
            );
            grant select, insert, update, delete
                on public.sessoes_de_captacao to anon, authenticated;
        """,
        minimo=1,
        exige="test_toda_tabela_de_dado_pessoal_tem_rls",
    ),
    "definer_sem_search_path": dict(
        descricao="handle_new_user sem search_path fixo",
        sql="""
            create or replace function public.handle_new_user()
            returns trigger language plpgsql security definer as $SAB$
            begin
                insert into public.profiles (id, nome)
                values (new.id, new.raw_user_meta_data ->> 'nome')
                on conflict (id) do nothing;
                return new;
            end; $SAB$;
        """,
        minimo=1,
        exige="test_trigger_de_criacao_de_perfil_esta_blindado",
    ),
    "grants_retirados": dict(
        descricao='GRANTs retirados de authenticated (simula "tudo quebrado")',
        sql="""
            revoke all on public.profiles, public.devices, public.sleep_data
                from authenticated;
        """,
        minimo=15,
        # O caminho feliz é o que tem de cair aqui. Se a suíte passasse com o
        # banco inacessível, ela não valeria nada — é o sabotador mais
        # importante da lista.
        exige="test_ana_le_apenas_o_proprio_profile",
    ),
    # --- SEC-06: o privilégio da ingestão ---
    "ingestao_com_select": dict(
        descricao="papel de ingestao ganha select em sleep_data",
        sql="grant select on public.sleep_data to dormio_ingestao;",
        minimo=2,
        exige="test_o_papel_nao_tem_privilegio_de_tabela",
    ),
    "ingestao_com_bypassrls": dict(
        descricao="papel de ingestao ganha BYPASSRLS",
        sql="alter role dormio_ingestao bypassrls;",
        minimo=1,
        exige="test_o_papel_existe_e_nao_ignora_o_rls",
    ),
    "ingestao_alcanca_a_sessao": dict(
        descricao="papel de ingestao ganha a funcao do caminho por sessao",
        sql="""
            grant execute on function public.registrar_leitura_da_sessao(uuid, jsonb)
                to dormio_ingestao;
        """,
        minimo=1,
        exige="test_o_papel_nao_grava_pelo_caminho_da_sessao",
    ),
    "anon_alcanca_a_ingestao": dict(
        descricao="anon ganha execute em registrar_leitura",
        sql="grant execute on function public.registrar_leitura(text, jsonb) to anon;",
        minimo=1,
        exige="test_anon_nao_executa_funcao_de_ingestao",
    ),
    "gravacao_aceita_o_dono_do_json": dict(
        descricao="registrar_leitura passa a aceitar user_id do JSON",
        sql="""
            create or replace function public.registrar_leitura(
                p_token_hash text, p_leitura jsonb
            ) returns bigint language plpgsql volatile security definer
            set search_path = '' as $SAB$
            declare v_device uuid; v_dono uuid; v_id bigint;
            begin
                select d.id, d.user_id into v_device, v_dono from public.devices d
                 where d.token_hash = p_token_hash and d.revoked_at is null limit 1;
                if v_device is null then return null; end if;
                insert into public.sleep_data (movimento_total, user_id, device_id)
                values (
                    (p_leitura ->> 'movimento_total')::double precision,
                    -- A sabotagem: o JSON escolhe o dono.
                    coalesce((p_leitura ->> 'user_id')::uuid, v_dono),
                    v_device
                ) returning id into v_id;
                return v_id;
            end; $SAB$;
        """,
        minimo=1,
        exige="test_a_ingestao_nao_escolhe_o_dono_pelo_json",
    ),
    "definer_da_005_sem_search_path": dict(
        descricao="resolver_dispositivo sem search_path fixo",
        sql="""
            create or replace function public.resolver_dispositivo(p_token_hash text)
            returns table (id uuid, user_id uuid) language sql stable security definer
            as $SAB$
                select d.id, d.user_id from public.devices d
                 where d.token_hash = p_token_hash and d.revoked_at is null limit 1
            $SAB$;
        """,
        minimo=1,
        exige="test_toda_funcao_definer_tem_search_path_fixo",
    ),
}


def rodar(nome, sabotador, url):
    """Aplica um sabotador numa cópia da árvore e devolve (ok, resumo)."""
    with tempfile.TemporaryDirectory(prefix=f"mut-{nome}-") as temporario:
        arvore = pathlib.Path(temporario) / "web-app"
        shutil.copytree(
            WEB_APP,
            arvore,
            ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.pyc"),
        )

        alvo = arvore / ARQUIVO_ALVO
        with alvo.open("a", encoding="utf-8") as arquivo:
            arquivo.write(f"\n-- SABOTAGEM: {sabotador['descricao']}\n")
            arquivo.write(sabotador["sql"] + "\n")

        processo = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/rls", "-q", "--no-header", "-p", "no:cacheprovider"],
            cwd=arvore,
            env={**__import__("os").environ, "DORMIO_RLS_DATABASE_URL": url},
            capture_output=True,
            text=True,
        )
        saida = processo.stdout + processo.stderr

        caidos = [
            linha.split("::")[-1].split()[0]
            for linha in saida.splitlines()
            if linha.startswith("FAILED")
        ]

        if not caidos:
            return False, "NENHUM teste caiu — a suite nao acusa esta sabotagem"
        if len(caidos) < sabotador["minimo"]:
            return False, (
                f"caíram {len(caidos)}, esperado >= {sabotador['minimo']}: "
                + ", ".join(caidos[:6])
            )
        exigido = sabotador.get("exige")
        if exigido and not any(exigido in c for c in caidos):
            return False, (
                f"{len(caidos)} testes caíram, mas `{exigido}` NAO estava entre "
                "eles — a suite pode estar acusando por acidente"
            )
        return True, f"{len(caidos)} testes caíram"


def principal():
    analisador = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    analisador.add_argument("--apenas", help="roda um sabotador só, pelo nome")
    argumentos = analisador.parse_args()

    import os

    url = os.environ.get("DORMIO_RLS_DATABASE_URL", "").strip()
    if not url:
        print(
            "ERRO: DORMIO_RLS_DATABASE_URL nao definida.\n"
            "      Ver web-app/tests/rls/README.md.",
            file=sys.stderr,
        )
        return 2

    escolhidos = SABOTADORES
    if argumentos.apenas:
        if argumentos.apenas not in SABOTADORES:
            print(
                f"ERRO: sabotador '{argumentos.apenas}' nao existe. Opcoes:\n  "
                + "\n  ".join(SABOTADORES),
                file=sys.stderr,
            )
            return 2
        escolhidos = {argumentos.apenas: SABOTADORES[argumentos.apenas]}

    # Confere primeiro que a suíte passa SEM sabotagem. Sem isso, um "todos os
    # sabotadores detectados" poderia significar apenas que tudo está quebrado.
    print("Referencia (sem sabotagem): ", end="", flush=True)
    processo = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/rls", "-q", "--no-header", "-p", "no:cacheprovider"],
        cwd=WEB_APP,
        env={**os.environ, "DORMIO_RLS_DATABASE_URL": url},
        capture_output=True,
        text=True,
    )
    if processo.returncode != 0:
        print("FALHOU")
        print(
            "\nA suite nao passa nem sem sabotagem. Conserte isso primeiro — "
            "senao os sabotadores nao dizem nada.\n"
        )
        print(processo.stdout[-3000:])
        return 1
    print("passa\n")

    falhas = []
    for nome, sabotador in escolhidos.items():
        print(f"  {nome:34s} ", end="", flush=True)
        ok, resumo = rodar(nome, sabotador, url)
        print(("[detectado] " if ok else "[NAO DETECTADO] ") + resumo)
        if not ok:
            falhas.append((nome, sabotador["descricao"], resumo))

    print()
    if falhas:
        print(f"REGRESSAO: {len(falhas)} de {len(escolhidos)} sabotagens passaram "
              "sem ser detectadas:\n")
        for nome, descricao, resumo in falhas:
            print(f"  · {nome}: {descricao}\n    {resumo}")
        print(
            "\nIsto vem antes de qualquer outro trabalho: a suite esta "
            "afirmando uma garantia que nao verifica."
        )
        return 1

    print(f"OK: {len(escolhidos)} de {len(escolhidos)} sabotagens detectadas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
