import logging
import os
from datetime import datetime, timezone

from supabase import create_client
from consulta import LIMITE_PADRAO

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
        # Chave anon: usada para validar o JWT do usuario e para montar o
        # cliente por requisicao que carrega esse JWT (AUTH-03). E publica por
        # design — o isolamento vem do RLS, nao do sigilo dela.
        self.anon_key = os.environ.get("SUPABASE_ANON_KEY", "")
        self._client = None
        self._client_anon = None

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

    def _get_client_anon(self):
        """Cliente com a chave anon, sem sessao. Usado para validar tokens."""
        if self._client_anon is None:
            if not self.url or not self.anon_key:
                logger.error("SUPABASE_URL ou SUPABASE_ANON_KEY ausentes (necessarias no AUTH-03).")
                return None
            try:
                self._client_anon = create_client(self.url, self.anon_key)
            except Exception:
                logger.exception("Falha ao criar cliente anon do Supabase.")
                return None
        return self._client_anon

    def validar_token_de_usuario(self, jwt):
        """Valida o JWT no servidor de Auth. Devolve o id do usuario ou None.

        A validacao e remota de proposito: conferir assinatura localmente
        exigiria gerenciar chaves (e acertar o algoritmo), enquanto o Auth ja
        responde de forma autoritativa, inclusive para token revogado.
        """
        try:
            client = self._get_client_anon()
            if client is None:
                return None
            resposta = client.auth.get_user(jwt)
            usuario = getattr(resposta, "user", None)
            return getattr(usuario, "id", None)
        except Exception:
            # Token expirado/invalido chega aqui como excecao da lib.
            logger.info("Token de usuario rejeitado.")
            return None

    def cliente_do_usuario(self, jwt):
        """Cliente que carrega o JWT do usuario — o RLS enxerga `auth.uid()`.

        Um cliente novo por requisicao, e nao um compartilhado com sessao
        trocada: dois pedidos simultaneos de usuarios diferentes num servidor
        com threads poderiam ler o dado um do outro.
        """
        try:
            if not self.url or not self.anon_key:
                logger.error("SUPABASE_ANON_KEY ausente: leitura por usuario indisponivel.")
                return None
            client = create_client(self.url, self.anon_key)
            client.postgrest.auth(jwt)
            return client
        except Exception:
            logger.exception("Falha ao montar cliente do usuario.")
            return None

    def get_leituras_do_usuario(
        self, jwt, usuario_id, device_id=None, desde=None, ate=None, limite=LIMITE_PADRAO
    ):
        """Leituras do usuario autenticado, mais recentes primeiro.

        Dupla proteção deliberada: o RLS filtra no banco E o `.eq(user_id)`
        filtra na consulta. Redundante de proposito — se o RLS for desligado
        por engano numa migracao, o filtro segura; se o filtro tiver bug, o
        RLS segura. Nenhum dos dois sozinho merece confianca total.

        `device_id` recorta por instrumento (DASH-05). Ate aqui a consulta
        filtrava so por dono, entao quem pareasse dois dispositivos recebia os
        dois **misturados na mesma serie e nas mesmas metricas**, com o limite
        repartido por ordem de chegada. Ninguem esbarrou nisso porque so existe
        um dispositivo — o do autor.

        `device_id` sai da consulta tambem no SELECT: sem ele o cliente nao tem
        como rotular de qual instrumento veio cada ponto quando exibe todos.
        """
        try:
            client = self.cliente_do_usuario(jwt)
            if client is None:
                return []
            consulta = (
                client.table("sleep_data")
                .select(
                    "created_at, movimento_total, temp, status, device_id, "
                    # `epoca_segundos` diz QUANTO TEMPO a linha resume. Sem
                    # ele, o painel nao consegue distinguir "duas horas de
                    # repouso" de "duas horas sem leitura nenhuma" — e passava
                    # a reportar buraco de coleta como pausa (DASH-09).
                    "epoca_segundos"
                )
                .eq("user_id", usuario_id)
            )
            if device_id:
                consulta = consulta.eq("device_id", device_id)
            if desde:
                consulta = consulta.gte("created_at", desde)
            if ate:
                consulta = consulta.lte("created_at", ate)
            resposta = (
                consulta.order("created_at", desc=True).limit(limite).execute()
            )
            return resposta.data or []
        except Exception:
            logger.exception("Falha ao consultar sleep_data do usuario.")
            return []

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
