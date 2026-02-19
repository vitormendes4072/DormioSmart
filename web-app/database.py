import os
from supabase import create_client, Client

class Database:
    def __init__(self):
        # Apenas salva as credenciais, NÃO conecta ainda
        self.url = os.environ.get("SUPABASE_URL", "")
        self.key = os.environ.get("SUPABASE_KEY", "")
        self._client = None

    def get_client(self):
        # Conecta apenas quando alguma rota pedir dados
        if self._client is None:
            if not self.url or not self.key:
                print("❌ ERRO: Variáveis SUPABASE_URL ou SUPABASE_KEY ausentes.")
                return None
            try:
                self._client = create_client(self.url, self.key)
            except Exception as e:
                print(f"❌ Erro de conexão com Supabase: {e}")
                return None
        return self._client

    def insert_sleep_data(self, data):
        client = self.get_client()
        if client:
            return client.table("sleep_data").insert(data).execute()
        return None

    def get_latest_data(self, limit=20):
        client = self.get_client()
        if client:
            return client.table("sleep_data") \
                .select("created_at, movimento_total, temp, status") \
                .order("created_at", desc=True) \
                .limit(limit) \
                .execute()
        return None

# Instância única
db = Database()