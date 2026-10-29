"""Script utilitário — verifica a conexão com o Supabase.

Uso (a partir da pasta web-app/):
    python teste_conexao.py

Requer .env com SUPABASE_URL e a chave de ingestão preenchidas —
ver web-app/.env.example. Nunca commitar credenciais reais.

── O QUE MUDOU AQUI, E POR QUE (SEC-06) ─────────────────────────────────

Este script contava os registros de `sleep_data`. Deixou de contar, de
propósito: a contagem exige privilégio de LEITURA na tabela, e a chave de
ingestão não tem mais nenhum — é justamente o ganho da migration 005.

Conferir conexão e conferir volume de dado são duas necessidades diferentes,
e só a primeira pertence a um script que roda com a credencial do servidor.
Para ver volume, use o painel do Supabase, que autentica como você.
"""
from dotenv import load_dotenv
load_dotenv()

import os

from database import db


def testar():
    usando_minima = bool(os.environ.get("SUPABASE_INGESTAO_KEY"))

    ok, motivo = db.verificar_conexao()
    if ok:
        print("[ok] Conexao com Supabase: SUCESSO")
        print("     sanidade() respondeu 'ok' -- credencial valida, rede")
        print("     alcancavel e as tres tabelas no lugar.")
    else:
        print("[falha] Conexao com Supabase NAO estabelecida.")
        print(f"        Motivo: {motivo}")
        print("        Verifique SUPABASE_URL e SUPABASE_INGESTAO_KEY no .env")

    print()
    if usando_minima:
        print("[ok] Credencial: SUPABASE_INGESTAO_KEY (papel dormio_ingestao).")
        print("     Privilegio minimo -- nao le dado de usuario.")
    else:
        print("[atencao] Credencial: SUPABASE_SERVICE_ROLE_KEY.")
        print("          Essa chave IGNORA o RLS e tem acesso total ao banco.")
        print("          Emita a chave do papel dormio_ingestao e configure")
        print("          SUPABASE_INGESTAO_KEY -- ver README, secao")
        print("          'Rotacao da chave de ingestao'.")


if __name__ == "__main__":
    testar()
