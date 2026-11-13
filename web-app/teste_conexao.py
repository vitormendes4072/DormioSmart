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

from database import db


def testar():
    ok, motivo = db.verificar_conexao()
    if ok:
        print("[ok] Conexao com Supabase: SUCESSO")
        print("     sanidade() respondeu 'ok' -- credencial valida, rede")
        print("     alcancavel e as tres tabelas no lugar.")
    else:
        print("[falha] Conexao com Supabase NAO estabelecida.")
        print(f"        Motivo: {motivo}")
        print("        Verifique SUPABASE_URL e SUPABASE_INGESTAO_KEY no .env")

    if ok:
        print("[ok] Credencial: SUPABASE_INGESTAO_KEY (papel dormio_ingestao).")
        return 0
    print("        Confira também SUPABASE_ANON_KEY e a seção 'Rotação da chave de ingestão' no README.")
    return 1


if __name__ == "__main__":
    raise SystemExit(testar())
