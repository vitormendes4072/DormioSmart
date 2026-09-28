import logging
import os

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
        #
        # A chave do caminho de ingestão (SEC-06). Ordem de preferência:
        #
        #   1. SUPABASE_INGESTAO_KEY — JWT do papel `dormio_ingestao`, que só
        #      tem EXECUTE em três funções e NENHUM privilégio de tabela. É a
        #      configuração correta; ver migrations/005 e o README.
        #   2. SUPABASE_SERVICE_ROLE_KEY — cai aqui só até a chave nova ser
        #      emitida. Funciona, mas NÃO reduz privilégio nenhum: a
        #      service_role ignora RLS e tem acesso total. O aviso no
        #      `cliente_de_ingestao` existe para que isso não passe em silêncio.
        self.url = os.environ.get("SUPABASE_URL", "")
        self.ingestao_key = os.environ.get("SUPABASE_INGESTAO_KEY", "")
        self.key = (
            self.ingestao_key
            or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
            or os.environ.get("SUPABASE_KEY", "")
        )
        # Chave anon: usada para validar o JWT do usuario e para montar o
        # cliente por requisicao que carrega esse JWT (AUTH-03). E publica por
        # design — o isolamento vem do RLS, nao do sigilo dela.
        self.anon_key = os.environ.get("SUPABASE_ANON_KEY", "")
        self._client = None
        self._client_anon = None

    def cliente_de_ingestao(self):
        """Cliente do caminho de ingestão (SEC-06). Criado sob demanda.

        ESTE CLIENTE NÃO CONSEGUE LER DADO DE USUÁRIO. Com a chave correta
        (`SUPABASE_INGESTAO_KEY`) ele carrega o papel `dormio_ingestao`, que
        tem EXECUTE em `sanidade`, `resolver_dispositivo` e `registrar_leitura`
        e nenhum privilégio de tabela. Qualquer `.table(...)` por aqui falha
        por permissão — e é proposital: é o que faz o pior caso de um
        vazamento desta chave ser "insere lixo" em vez de "lê o banco todo".

        Só o caminho de ingestão e o `/health` devem usá-lo. Toda rota de
        usuário usa `cliente_do_usuario`, para que o RLS decida a posse.
        `tests/test_privilegio_minimo.py` falha se isso deixar de valer.

        Devolve None em vez de levantar quando não dá para conectar. Todos os
        chamadores dependem disso — ver a nota do FIX-08 no topo do arquivo.
        """
        if self._client is None:
            if not self.url or not self.key:
                logger.error(
                    "SUPABASE_URL ou a chave (SUPABASE_SERVICE_ROLE_KEY/SUPABASE_KEY) ausentes."
                )
                return None
            if not self.ingestao_key:
                # Um aviso por processo, no momento em que a chave de alto
                # privilégio entra em uso de fato. Silenciar isto seria deixar
                # a configuração insegura parecer a configuração normal.
                logger.warning(
                    "Ingestao usando chave de ALTO PRIVILEGIO "
                    "(SUPABASE_SERVICE_ROLE_KEY). Emita a chave do papel "
                    "dormio_ingestao e configure SUPABASE_INGESTAO_KEY -- ver "
                    "web-app/README.md, secao 'Rotacao da chave de ingestao'."
                )
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
                    "epoca_segundos, "
                    # `captured_at` diz QUANDO a linha foi medida (DASH-12).
                    # `created_at` e a hora de CHEGADA, gerada pelo banco. Sem
                    # este campo, o painel aceitava a DURACAO declarada pelo
                    # dispositivo e ignorava o INSTANTE declarado pelo mesmo
                    # dispositivo — incoerencia que fazia latencia de rede
                    # parecer irregularidade de cadencia, e que faria o buffer
                    # offline do HW-05 chegar todo empilhado em poucos
                    # segundos de `created_at`.
                    #
                    # A ORDENACAO segue por `created_at`: ele nunca e nulo
                    # (`default now()`), e ordenar por uma coluna que pode ser
                    # nula deixaria as linhas antigas em posicao arbitraria.
                    # O cliente reordena pelo instante de medicao com fallback
                    # — ver `instanteDaLeitura` em `types/sleep.ts`.
                    "captured_at"
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

    def registrar_leitura(self, token_hash, leitura):
        """Persiste uma leitura do caminho do dispositivo (SEC-02, SEC-06).

        Devolve o id da linha criada, ou None se nada foi gravado.

        O TOKEN VAI JUNTO DE PROPÓSITO. A função no banco resolve o dono a
        partir dele e carimba a linha — não existe parâmetro para escolher o
        `user_id`. Antes isto era uma linha de Python em `routes.py`: correta,
        mas era o que separava uma chave vazada da posse de dado alheio. Agora
        é estrutural. Ver migrations/005.

        Nulo do banco significa "token não resolve" (ausente, desconhecido ou
        revogado). A rota trata isso como 401, como já fazia.
        """
        try:
            client = self.cliente_de_ingestao()
            if client is None:
                return None
            resposta = client.rpc(
                "registrar_leitura",
                {"p_token_hash": token_hash, "p_leitura": leitura},
            ).execute()
            return getattr(resposta, "data", None)
        except Exception:
            logger.exception("Falha ao registrar leitura.")
            return None

    def registrar_leitura_da_sessao(self, jwt, device_id, leitura):
        """Persiste uma leitura do caminho do celular (APP-08, SEC-06).

        Vai pelo cliente do USUÁRIO, não por chave privilegiada: a função no
        banco deriva o dono de `auth.uid()` e confere a posse do dispositivo
        antes de gravar. Este caminho deixou de tocar a service_role.

        Devolve o id da linha criada, ou None quando o dispositivo não é do
        usuário, está revogado, ou não existe — os três iguais, para não
        revelar id de dispositivo alheio.
        """
        try:
            client = self.cliente_do_usuario(jwt)
            if client is None:
                return None
            resposta = client.rpc(
                "registrar_leitura_da_sessao",
                {"p_device_id": device_id, "p_leitura": leitura},
            ).execute()
            return getattr(resposta, "data", None)
        except Exception:
            logger.exception("Falha ao registrar leitura por sessao.")
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
            client = self.cliente_de_ingestao()
            if client is None:
                return False, "cliente indisponivel"
            # `sanidade()` em vez do antigo `select from sleep_data`: confirma
            # credencial, rede e esquema sem exigir privilégio de leitura em
            # tabela nenhuma. Era esse select que obrigava o papel de ingestão
            # a poder ler TODO o dado de sono (SEC-06).
            resposta = client.rpc("sanidade").execute()
            estado = getattr(resposta, "data", None)
            if estado != "ok":
                return False, "esquema incompleto"
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
            client = self.cliente_de_ingestao()
            if client is None:
                return None
            # `resolver_dispositivo()` em vez do antigo select em `devices`: a
            # revogação é aplicada dentro da função e `token_hash` não volta.
            # Era aquele select que obrigava o papel de ingestão a poder LISTAR
            # o hash do token de todo dispositivo de todo usuário (SEC-06).
            resposta = client.rpc(
                "resolver_dispositivo", {"p_token_hash": token_hash}
            ).execute()
            linhas = getattr(resposta, "data", None) or []
            if not linhas:
                return None
            return linhas[0]
        except Exception:
            logger.exception("Falha ao resolver dispositivo.")
            return None


# Instância única
db = Database()
