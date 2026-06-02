import os
from supabase import create_client, Client

class Database:
    def __init__(self):
        # Apenas salva as credenciais, NÃO conecta ainda.
        # O backend é server-side (Flask na Vercel) e o navegador nunca acessa o
        # Supabase diretamente, então usamos a chave service_role (secreta),
        # mantendo o RLS ligado no banco. Fallback para SUPABASE_KEY por compatibilidade.
        self.url = os.environ.get("SUPABASE_URL", "")
        self.key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY", "")
        self._client = None

    def get_client(self):
        # Conecta apenas quando alguma rota pedir dados
        if self._client is None:
            if not self.url or not self.key:
                print("❌ ERRO: SUPABASE_URL ou a chave (SUPABASE_SERVICE_ROLE_KEY/SUPABASE_KEY) ausentes.")
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
        # Sempre retorna uma lista: dados em caso de sucesso, [] em qualquer
        # falha (cliente ausente ou erro de consulta). Isso evita que a rota
        # quebre com 500 (FIX-01). O erro é registrado no log do servidor.
        client = self.get_client()
        if client is None:
            return []
        try:
            response = client.table("sleep_data") \
                .select("created_at, movimento_total, temp, status") \
                .order("created_at", desc=True) \
                .limit(limit) \
                .execute()
            return response.data or []
        except Exception as e:
            print(f"❌ Erro ao consultar sleep_data: {e}")
            return []

# Instância única
db = Database()