"""Script utilitário — verifica a conexão com o Supabase e conta os registros.

Uso (a partir da pasta web-app/):
    python teste_conexao.py

Requer .env com SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY preenchidos.
Nunca commitar credenciais reais — ver web-app/.env.example.
"""
from dotenv import load_dotenv
load_dotenv()

from database import db


def testar():
    client = db.get_client()
    if client is None:
        print("❌ Falha ao obter cliente Supabase.")
        print("   Verifique SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY no seu .env")
        return

    try:
        res = (
            client.table("sleep_data")
            .select("count", count="exact")
            .limit(1)
            .execute()
        )
        print("✅ Conexão com Supabase: SUCESSO!")
        print(f"📊 Total de registros na tabela: {res.count}")
    except Exception as e:
        print("❌ Erro na consulta!")
        print(f"   Detalhes: {e}")


if __name__ == "__main__":
    testar()
