from database import get_supabase_client

def testar():
    try:
        supabase = get_supabase_client()
        # Tenta buscar qualquer dado da tabela (mesmo que esteja vazia)
        res = supabase.table("sleep_data").select("count", count="exact").limit(1).execute()
        print("✅ Conexão com Supabase: SUCESSO!")
        print(f"📊 Total de registros na tabela: {res.count}")
    except Exception as e:
        print("❌ Erro na conexão!")
        print(f"Detalhes: {e}")

if __name__ == "__main__":
    testar()