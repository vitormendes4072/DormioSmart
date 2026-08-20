import logging
import os
from datetime import datetime, timezone

from supabase import create_client

# Log de servidor via `logging`, não `print` (FIX-08).
#
# O `print` com emoji quebrava a requisição inteira em consoles cp1252 (padrão
# no Windows pt-BR): a tentativa de AVISAR sobre credencial ausente levantava
# UnicodeEncodeError e virava 500 — exatamente o que o FIX-01 existe para
# impedir. Mensagens de log agora são ASCII e passam pelo logging, que trata
# encoding e permite configurar nível e destino.
logger = logging.getLogger(__name__)


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
        """Cliente Supabase, criado sob demanda.

        Devolve None em vez de levantar quando não dá para conectar. Todos os
        chamadores dependem disso — ver a nota do FIX-08 no topo do arquivo.
        """
        if self._client is None:
            if not self.url or not self.key:
                logger.error(
                    "SUPABASE_URL ou a chave (SUPABASE_SERVICE_ROLE_KEY/SUPABASE_KEY) ausentes."
                )
                return None
            try:
                self._client = create_client(self.url, self.key)
            except Exception:
                # exc_info leva o traceback ao log sem interpolar a mensagem do
                # driver, que pode conter host e credencial.
                logger.exception("Falha ao conectar no Supabase.")
                return None
        return self._client

    def insert_sleep_data(self, data):
        """Persiste uma leitura. Devolve None se nada foi gravado."""
        try:
            client = self.get_client()
            if client is None:
                return None
            return client.table("sleep_data").insert(data).execute()
        except Exception:
            logger.exception("Falha ao inserir em sleep_data.")
            return None

    def verificar_conexao(self):
        """Checagem leve de saude do banco (WEB-04).

        Devolve (ok, motivo). Nao levanta: o /health precisa responder mesmo
        com o banco fora, senao ele mesmo vira uma fonte de erro. A consulta e
        de contagem com limite 1 — confirma credencial e alcance de rede sem
        trazer dado.
        """
        if not self.url or not self.key:
            return False, "credenciais ausentes"
        try:
            client = self.get_client()
            if client is None:
                return False, "cliente indisponivel"
            client.table("sleep_data").select("created_at").limit(1).execute()
            return True, None
        except Exception:
            # O motivo devolvido e generico de proposito: o /health nao exige
            # autenticacao, entao erro de driver (que pode conter host e
            # credencial) fica so no log.
            logger.exception("/health: consulta de sanidade falhou.")
            return False, "consulta falhou"

    def get_device_by_token_hash(self, token_hash):
        """Resolve o token de um device (SEC-02).

        Devolve o dict do dispositivo ou None — ausente, revogado ou falha de
        consulta caem todos em None, e a rota responde 401. Nunca levanta:
        indisponibilidade do banco não deve virar 500 no caminho de ingestão.
        """
        try:
            client = self.get_client()
            if client is None:
                return None
            response = (
                client.table("devices")
                .select("id, user_id, revoked_at")
                .eq("token_hash", token_hash)
                .limit(1)
                .execute()
            )
            linhas = response.data or []
            if not linhas:
                return None
            device = linhas[0]
            # Revogação é soft delete: a linha continua, mas o token não vale.
            if device.get("revoked_at"):
                return None
            return device
        except Exception:
            logger.exception("Falha ao consultar devices.")
            return None

    def touch_device(self, device_id):
        """Marca o último contato do dispositivo. Best-effort de propósito:
        falhar aqui não pode derrubar uma leitura que já foi persistida."""
        try:
            client = self.get_client()
            if client is None:
                return
            (
                client.table("devices")
                .update({"last_seen_at": datetime.now(timezone.utc).isoformat()})
                .eq("id", device_id)
                .execute()
            )
        except Exception:
            logger.warning("Falha ao atualizar last_seen_at de %s.", device_id, exc_info=True)

    def get_latest_data(self, limit=20):
        """Leituras mais recentes.

        Sempre devolve uma lista: dados em caso de sucesso, [] em qualquer
        falha — cliente ausente, erro de consulta ou erro ao obter o cliente.
        É o que impede a rota de responder 500 (FIX-01/FIX-08).
        """
        try:
            client = self.get_client()
            if client is None:
                return []
            response = (
                client.table("sleep_data")
                .select("created_at, movimento_total, temp, status")
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return response.data or []
        except Exception:
            logger.exception("Falha ao consultar sleep_data.")
            return []


# Instância única
db = Database()
