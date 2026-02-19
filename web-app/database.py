import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

class Database:
    def __init__(self):
        self.url = os.environ.get("SUPABASE_URL")
        self.key = os.environ.get("SUPABASE_KEY")
        self.client: Client = create_client(self.url, self.key)

    def insert_sleep_data(self, data):
        return self.client.table("sleep_data").insert(data).execute()

    def get_latest_data(self, limit=20):
        return self.client.table("sleep_data") \
            .select("created_at, movimento_total, temp, status") \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()

# Instância única para ser importada
db = Database()