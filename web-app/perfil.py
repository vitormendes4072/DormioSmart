"""Perfil do usuário — nome e idade (PERFIL-01, LGPD art. 18, III).

`public.profiles` passou a ser a **fonte de verdade** do nome e da idade: é
dela que o aplicativo lê e é nela que a correção escreve. O raciocínio
completo, inclusive a parte que não é código, está em
`docs/DECISAO-FONTE-DO-PERFIL.md`.

── O QUE ESTE MÓDULO VALIDA, E O QUE ELE NÃO PROTEGE ────────────────────

Valida forma: tipo, faixa, tamanho e campo desconhecido. **Não é controle de
acesso, e não é o único portão de escrita.** `authenticated` tem GRANT de
UPDATE em `profiles`, e o navegador fala direto com o PostgREST usando a chave
`anon` — que é pública por design. Logo, o titular pode escrever na própria
linha sem passar por aqui.

Isso não é falha: o RLS impede escrever na linha **alheia**, que é a
propriedade que importa, e está verificado contra Postgres real em
`tests/rls/test_rls_isolamento.py`. O que esta distinção impede é a conclusão
errada — a mesma da `007` sobre a lista de campos de `dispositivos.py`: *lista
de campos em Python é apresentação, não proteção.* O teto de tamanho que vale
para todo caminho é a constraint `profiles_nome_tamanho` da migração `008`.

── A REGRA DE PRECEDÊNCIA QUE ESTE MÓDULO IMPLEMENTA ────────────────────

`auth.users.raw_user_meta_data.nome` é **insumo de criação**: lido uma vez pelo
gatilho `handle_new_user` no signup, ou pelo reparo de `GET /api/me/perfil`
quando a linha falta (e isso acontece — ver
`migrations/DIAGNOSTICO-perfil-nao-criado.sql`). Depois disso, nada o lê.
"""
import logging

logger = logging.getLogger(__name__)

# Campos devolvidos ao cliente.
#
# Como em `dispositivos.py`: ESTA LISTA NÃO É CONTROLE DE ACESSO (ver o
# cabeçalho). É o que a interface precisa. `id` fica de fora porque o cliente
# já sabe quem é — e porque devolvê-lo convidaria alguém a mandá-lo de volta
# num corpo de requisição, que é precisamente o que a rota não aceita.
CAMPOS = "nome, idade, updated_at"

# Campos que o titular pode alterar. Qualquer outro no corpo é 400, e não
# silenciosamente ignorado: ignorar faria `PATCH {"idadee": 30}` responder
# sucesso sem ter gravado nada — confirmação emitida antes da verificação (§6
# das lições), na forma mais fácil de cometer.
ALTERAVEIS = ("nome", "idade")

# Teto de caracteres do nome nesta camada.
#
# ⚙️ DECISÃO, não medição (§3 das lições). É o mesmo 120 de
# `frontend/src/lib/perfil.ts`, repetido aqui de propósito: a validação do
# cliente existe para a mensagem aparecer antes da ida à rede, e a do servidor
# existe porque validação de cliente não é validação. O banco tem um teto
# MAIOR (200, migração `008`) por ser o backstop do caminho que não passa por
# nenhum dos dois — ver o cabeçalho da migração para o porquê da assimetria.
NOME_MAXIMO = 120

# Faixa de `idade`. ESPELHA a constraint da migração `001`
# (`idade >= 0 and idade < 150`) e não a redefine: divergir daqui produziria
# erro de constraint do Postgres em vez de 400 com mensagem útil.
IDADE_MINIMA = 0
IDADE_MAXIMA = 149


def normalizar_nome(valor):
    """Tira as pontas e colapsa espaço interno.

    Mesma normalização de `normalizarNome` no cliente. Tem de ser a mesma, ou
    "Ana  Maria" gravado pelo cliente e "Ana Maria" gravado por aqui seriam
    dois nomes diferentes na mesma coluna.
    """
    return " ".join(valor.split())


def validar_nome(valor):
    """Devolve `(nome, None)` ou `(None, motivo)`.

    Diferente de `dispositivos.validar_nome`, nome vazio **é erro** e não cai
    para um padrão: dispositivo sem nome ganha "Smart Dormio" porque o nome
    dele é conveniência; pessoa sem nome não ganha nome nenhum inventado pelo
    sistema.
    """
    if not isinstance(valor, str):
        return None, "nome deve ser texto"

    nome = normalizar_nome(valor)
    if not nome:
        return None, "nome nao pode ficar vazio"
    if len(nome) > NOME_MAXIMO:
        return None, f"nome deve ter no maximo {NOME_MAXIMO} caracteres"
    return nome, None


def validar_idade(valor):
    """Devolve `(idade, None)` ou `(None, motivo)`. `None` é valor VÁLIDO.

    `idade` é opcional e permanece opcional: ela existe para um aviso de
    aplicabilidade de coorte (ver a seção 5 de
    `docs/DECISAO-FONTE-DO-PERFIL.md`), e campo obrigatório para alimentar um
    aviso seria coleta desproporcional à finalidade. `null` é como o titular
    **retira** a idade, o que é o art. 18, IV ao alcance de um clique.

    Três recusas que merecem o porquê:

    * **`bool` é recusado explicitamente.** Em Python `isinstance(True, int)` é
      verdadeiro, então sem esta linha `{"idade": true}` gravaria 1 — idade de
      um ano, plausível, errada e silenciosa (§7).
    * **Texto é recusado**, inclusive `"30"`. Aceitar os dois tipos obrigaria
      todo leitor futuro a saber qual deles vem.
    * **`float` é recusado**, inclusive `30.0`. A coluna é `integer`; aceitar
      aqui e deixar o banco arredondar seria decidir no lugar errado.
    """
    if valor is None:
        return None, None
    if isinstance(valor, bool) or not isinstance(valor, int):
        return None, "idade deve ser um numero inteiro ou nulo"
    if valor < IDADE_MINIMA or valor > IDADE_MAXIMA:
        return None, f"idade deve estar entre {IDADE_MINIMA} e {IDADE_MAXIMA}"
    return valor, None


def ler_alteracao(corpo):
    """Traduz o corpo do `PATCH` em `(campos, None)` ou `(None, motivo)`.

    `PATCH` parcial de propósito: só o que vem é alterado. A ausência de um
    campo e o `null` dele são coisas DIFERENTES — ausente é "não mexa",
    `"idade": null` é "apague". Tratar os dois igual tornaria impossível
    retirar a idade sem apagar o nome.

    `user_id`/`id` no corpo não são "ignorados": caem em campo desconhecido e
    respondem 400. Quem é o dono sai do JWT, sempre, e um corpo que tenta
    informá-lo é um pedido mal formado ou uma tentativa — nos dois casos a
    resposta honesta é recusar, não aceitar e descartar a parte perigosa.
    """
    if not isinstance(corpo, dict):
        return None, "corpo deve ser um objeto JSON"

    desconhecidos = sorted(set(corpo) - set(ALTERAVEIS))
    if desconhecidos:
        return None, f"campo desconhecido: {', '.join(desconhecidos)}"

    if not corpo:
        return None, f"informe ao menos um campo: {', '.join(ALTERAVEIS)}"

    campos = {}

    if "nome" in corpo:
        nome, erro = validar_nome(corpo["nome"])
        if erro:
            return None, erro
        campos["nome"] = nome

    if "idade" in corpo:
        idade, erro = validar_idade(corpo["idade"])
        if erro:
            return None, erro
        campos["idade"] = idade

    return campos, None


def ler(client, usuario_id):
    """Perfil do usuário.

    Três retornos distintos, e a distinção é o ponto:

    * `dict`  — a linha existe.
    * `{}`    — **não há linha** para este usuário. Não é erro: é o caso do
                `DIAGNOSTICO-perfil-nao-criado.sql`, que já aconteceu neste
                projeto. Quem chama repara.
    * `None`  — falha de infraestrutura. Nunca confundir com o caso acima:
                tratar indisponibilidade como "perfil vazio" faria a rota
                reparar por cima de um banco que só estava fora do ar.
    """
    try:
        resposta = (
            client.table("profiles")
            .select(CAMPOS)
            .eq("id", usuario_id)
            .limit(1)
            .execute()
        )
        linhas = resposta.data or []
        return linhas[0] if linhas else {}
    except Exception:
        logger.exception("Falha ao ler profiles.")
        return None


def gravar(client, usuario_id, campos):
    """Grava `campos` no perfil do usuário e devolve a linha, ou None.

    `upsert` e não `update`, por um motivo medido e não por simetria: se a
    linha faltar (gatilho ausente — ver o diagnóstico), um `update` afetaria
    zero linhas e a correção do titular falharia em silêncio, com 200 na cara
    dele. O `upsert` cria.

    **O `id` vem de `usuario_id`, que vem do JWT validado — nunca do corpo.**
    E não é este argumento que protege: a policy `profiles_insert_own` exige
    `id = auth.uid()` no insert e a `profiles_update_own` no update, então
    mesmo um `id` alheio escrito aqui seria recusado pelo banco. Os dois
    existem de propósito — se um falhar, o outro segura (a mesma dupla proteção
    de `get_leituras_do_usuario`).
    """
    try:
        resposta = (
            client.table("profiles")
            .upsert({"id": usuario_id, **campos})
            .execute()
        )
        linhas = resposta.data or []
        if not linhas:
            # Upsert que não devolve linha é escrita não confirmada. Responder
            # sucesso aqui seria o FIX-02 outra vez, em outra rota.
            logger.error("Upsert em profiles nao devolveu linha.")
            return None
        return {campo: linhas[0].get(campo) for campo in ("nome", "idade", "updated_at")}
    except Exception:
        logger.exception("Falha ao gravar profiles.")
        return None
