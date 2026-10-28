"""Gerenciamento de dispositivos do usuário (AUTH-05).

Um usuário tem muitos dispositivos; cada dispositivo tem um dono. Todas as
operações usam o cliente montado com o JWT de quem pediu, então o **RLS decide
a posse** — não há verificação de dono escrita em Python que possa ser
esquecida numa rota futura.

Sobre o token: o banco guarda apenas o SHA-256 (SEC-02). O valor em claro
existe uma única vez, na resposta do pareamento. Não há como recuperá-lo
depois — só gerar outro. É o mesmo comportamento de token de API do GitHub e
do próprio Supabase, e é o que impede que um vazamento do banco entregue as
credenciais dos dispositivos.

Desde a SEC-08 o hash NÃO fica em `devices`: fica em `public.device_tokens`,
tabela sem GRANT para `anon`/`authenticated` e portanto não exposta pelo
PostgREST. Ver o cabeçalho de `migrations/007` para o porquê — em resumo, a
lista de campos abaixo é apresentação, não proteção, e por um tempo o
comentário dela dizia o contrário.
"""
import logging

logger = logging.getLogger(__name__)

# Campos devolvidos ao cliente.
#
# ESTA LISTA NÃO É UM CONTROLE DE ACESSO. Ela é o que a interface precisa, e
# nada mais. Quem impede o cliente de ler o que não deve é o GRANT e o RLS no
# banco — o navegador fala direto com o PostgREST usando a chave `anon` (que é
# pública por design) e não passa por este arquivo.
#
# O comentário que estava aqui antes afirmava que `token_hash` ficava de fora
# "porque é material sensível", como se a omissão protegesse a coluna. Não
# protegia: `select=token_hash` via PostgREST devolvia. O conserto de verdade
# foi tirar a coluna desta tabela (SEC-08 / migrations/007), e é por isso que
# ela não aparece mais nem como omissão deliberada — ela não existe aqui.
CAMPOS = "id, nome, tipo, created_at, last_seen_at, revoked_at"

# Classes de instrumento (DATA-05). Nao e o nome — nome e escolha do usuario.
# O tipo e o que permite separar acoplamentos diferentes na UI e na analise:
# um travesseiro mede perto da cabeca; um celular no colchao mede um corpo de
# massa alta, amortecido, e compartilhado com quem dorme do lado.
TIPOS = ("travesseiro", "celular")
TIPO_PADRAO = "travesseiro"

NOME_PADRAO = "Smart Dormio"
# Nome do dispositivo criado pelo pareamento automatico (APP-08).
NOME_CELULAR = "Meu celular"
NOME_MAXIMO = 60


def validar_nome(valor):
    """Devolve (nome, erro). Nome vazio vira o padrão, não erro."""
    if valor is None:
        return NOME_PADRAO, None
    if not isinstance(valor, str):
        return None, "nome deve ser texto"

    nome = valor.strip()
    if not nome:
        return NOME_PADRAO, None
    if len(nome) > NOME_MAXIMO:
        return None, f"nome deve ter no maximo {NOME_MAXIMO} caracteres"
    return nome, None


def listar(client, usuario_id):
    """Dispositivos do usuário, mais recentes primeiro."""
    try:
        resposta = (
            client.table("devices")
            .select(CAMPOS)
            .eq("user_id", usuario_id)
            .order("created_at", desc=True)
            .execute()
        )
        return resposta.data or []
    except Exception:
        logger.exception("Falha ao listar devices.")
        return None


def validar_tipo(valor):
    """Devolve `(tipo, None)` ou `(None, motivo)`. Ausente usa o padrao."""
    if valor is None:
        return TIPO_PADRAO, None
    if not isinstance(valor, str) or valor not in TIPOS:
        return None, f"tipo deve ser um de {list(TIPOS)}"
    return valor, None


def criar(client, nome, token_hash, tipo=TIPO_PADRAO):
    """Cria o dispositivo e a credencial dele. Devolve a linha criada ou None.

    Vai por `parear_dispositivo()` no banco (SEC-08): a credencial vive em
    `device_tokens`, tabela sem GRANT para `authenticated`, então o cliente do
    usuário não consegue — e não deve — escrever nela direto.

    NÃO RECEBE `usuario_id`, e a ausência é o ponto: a função no banco deriva o
    dono de `auth.uid()`. Antes, o `user_id` era informado aqui e conferido pelo
    RLS no insert; agora não há por onde informá-lo errado. Uma linha de código
    a menos entre uma sessão válida e a conta de outra pessoa.
    """
    try:
        resposta = client.rpc(
            "parear_dispositivo",
            {"p_nome": nome, "p_tipo": tipo, "p_token_hash": token_hash},
        ).execute()
        linhas = resposta.data or []
        return linhas[0] if linhas else None
    except Exception:
        logger.exception("Falha ao criar device.")
        return None


def buscar_do_dono(client, usuario_id, device_id):
    """Devolve o dispositivo ATIVO daquele dono, ou None.

    Usado na ingestao por sessao (APP-08): antes de gravar, confere que o
    `device_id` informado pertence a quem pediu.

    O filtro por `user_id` acompanha o RLS, como no resto do modulo — se um
    cair, o outro segura. E `revoked_at is null` importa: revogar precisa
    valer para os dois caminhos de ingestao, senao o caminho por sessao
    seria uma porta que a revogacao nao fecha.
    """
    try:
        resposta = (
            client.table("devices")
            .select(CAMPOS)
            .eq("id", device_id)
            .eq("user_id", usuario_id)
            .is_("revoked_at", "null")
            .limit(1)
            .execute()
        )
        linhas = resposta.data or []
        return linhas[0] if linhas else None
    except Exception:
        logger.exception("Falha ao buscar device do dono.")
        return None


def primeiro_do_tipo(client, usuario_id, tipo):
    """Dispositivo ATIVO mais antigo daquele tipo, ou None.

    Serve ao pareamento automatico do celular: em vez de criar um dispositivo
    novo a cada coleta — o que encheria a conta de orfaos e tornaria o painel
    inutil — reaproveita o que ja existe.

    Mais antigo, e nao mais recente, de proposito: se por algum motivo houver
    duplicados, a escolha e estavel entre chamadas.
    """
    try:
        resposta = (
            client.table("devices")
            .select(CAMPOS)
            .eq("user_id", usuario_id)
            .eq("tipo", tipo)
            .is_("revoked_at", "null")
            .order("created_at", desc=False)
            .limit(1)
            .execute()
        )
        linhas = resposta.data or []
        return linhas[0] if linhas else None
    except Exception:
        logger.exception("Falha ao buscar device por tipo.")
        return None


def renomear(client, usuario_id, device_id, nome):
    """Renomeia. O filtro por user_id acompanha o RLS — se um cair, o outro segura."""
    try:
        resposta = (
            client.table("devices")
            .update({"nome": nome})
            .eq("id", device_id)
            .eq("user_id", usuario_id)
            .execute()
        )
        linhas = resposta.data or []
        return linhas[0] if linhas else None
    except Exception:
        logger.exception("Falha ao renomear device.")
        return None


def revogar(client, usuario_id, device_id, agora):
    """Revoga por soft delete.

    A linha permanece de propósito: as leituras já gravadas referenciam este
    `device_id`, e apagá-lo transformaria histórico legítimo em dado órfão.
    O token para de valer imediatamente (SEC-02 rejeita `revoked_at` não nulo).
    """
    try:
        resposta = (
            client.table("devices")
            .update({"revoked_at": agora})
            .eq("id", device_id)
            .eq("user_id", usuario_id)
            .is_("revoked_at", "null")
            .execute()
        )
        linhas = resposta.data or []
        return linhas[0] if linhas else None
    except Exception:
        logger.exception("Falha ao revogar device.")
        return None
