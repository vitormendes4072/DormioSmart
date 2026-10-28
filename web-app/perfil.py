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


def _projetar(linha):
    """Só os campos que o cliente vê. Mesma lista do `select`."""
    return {campo: linha.get(campo) for campo in ("nome", "idade", "updated_at")}


def gravar(client, usuario_id, campos):
    """Grava `campos` no perfil do usuário e devolve a linha, ou None.

    **`update`, e `insert` só se não houver linha — e NÃO `upsert`.** A
    diferença parece estilística e não é; é a diferença entre uma suposição e
    uma garantia, e vale escrever por quê.

    O `upsert` do PostgREST manda `insert ... on conflict do update set <...>`,
    e a pergunta que decide se ele serve aqui é: **o que acontece com as
    colunas que o corpo NÃO traz?**

    ⚠️ **A resposta foi conferida na especificação, e o `upsert` teria apagado
    dado do titular.** A documentação do PostgREST (v12.2, seção *Prefer
    Header → Missing*) diz, literalmente:

        "When doing POST and PATCH requests, any missing columns in the
         payload will be inserted as null value by default. To use the DEFAULT
         column value instead, use the Prefer: missing=default header."

    Upsert é um `POST`. E `postgrest.base_request_builder.pre_upsert` só
    acrescenta `missing=default` quando `default_to_null=False` — e o padrão do
    cliente é `default_to_null=True`, isto é, **o header não vai**. Logo, a
    cadeia inteira:

        upsert({"id": ..., "idade": 30})
          -> POST /profiles  Prefer: resolution=merge-duplicates   (sem missing)
          -> coluna ausente no corpo = null
          -> `nome` do titular APAGADO, com 200 na resposta

    Um `PATCH` de idade apagaria o nome. Silenciosamente, no caminho de uma
    tela de **correção** de dado pessoal, e **nenhum teste com dublê pegaria**,
    porque o dublê é o nosso cliente e não o PostgREST — que roda no Supabase e
    não neste repositório. É o §7 das lições (*degradação silenciosa*) com o §6
    em cima (*confirmação emitida antes da verificação*).

    Com `update` e `insert` separados não há o que supor: as duas instruções
    são SQL cujas semânticas são conhecidas, levam exatamente as colunas do
    corpo, e as duas estão exercitadas contra Postgres real em
    `tests/rls/test_rls_perfil.py` — inclusive o caso que importa, *"alterar só
    a idade não apaga o nome"*, e o simétrico.

    (Alternativa descartada: manter o `upsert` passando
    `default_to_null=False`. Faria a coluna ausente cair no `DEFAULT` em vez de
    `null` — que para `profiles.nome`, cujo default é nulo, **dá no mesmo**. O
    header resolve o caso de coluna com default útil, e não o nosso.)

    **Ordem: `update` primeiro.** O caso comum é a linha existir (o gatilho a
    cria no signup). `insert` primeiro erraria por chave duplicada em toda
    correção e dependeria do tratamento da exceção para funcionar.

    **E por que não `update` sozinho:** se a linha faltar — gatilho ausente,
    ver `migrations/DIAGNOSTICO-perfil-nao-criado.sql` — um `update` afeta zero
    linhas, e a correção do titular falharia **em silêncio, com 200 na cara
    dele**. Zero linhas afetadas não é erro para o Postgres; é aqui que ele
    precisa deixar de ser silêncio.

    **O `id` vem de `usuario_id`, que vem do JWT validado — nunca do corpo.** E
    não é este argumento que protege: `profiles_update_own` exige
    `id = auth.uid()` no update e `profiles_insert_own` no insert, então mesmo
    um `id` alheio escrito aqui seria recusado pelo banco. Os dois existem de
    propósito — se um falhar, o outro segura (a mesma dupla proteção de
    `get_leituras_do_usuario`).
    """
    try:
        resposta = (
            client.table("profiles")
            .update(campos)
            .eq("id", usuario_id)
            .execute()
        )
        linhas = resposta.data or []
        if linhas:
            return _projetar(linhas[0])
    except Exception:
        logger.exception("Falha ao atualizar profiles.")
        return None

    # Zero linhas: não há perfil para este usuário. Cria.
    #
    # Nota de alcance, porque a distinção não é observável daqui: zero linhas
    # também é o que o RLS devolve se a linha existisse e **não** fosse deste
    # usuário — e nesse caso o `insert` abaixo é recusado pela policy, que é o
    # desfecho correto. Em nenhum dos dois casos esta função decide posse.
    try:
        resposta = (
            client.table("profiles")
            .insert({"id": usuario_id, **campos})
            .execute()
        )
        linhas = resposta.data or []
        if not linhas:
            # Escrita não confirmada. Responder sucesso aqui seria o FIX-02
            # outra vez, em outra rota.
            logger.error("Insert em profiles nao devolveu linha.")
            return None
        logger.warning(
            "Perfil criado na gravacao: nao havia linha para o usuario. O "
            "gatilho handle_new_user pode nao existir no projeto -- ver "
            "migrations/DIAGNOSTICO-perfil-nao-criado.sql."
        )
        return _projetar(linhas[0])
    except Exception:
        logger.exception("Falha ao criar profiles.")
        return None
