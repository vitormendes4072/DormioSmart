"""O cliente privilegiado não escapa do caminho de ingestão (SEC-06).

── A REGRESSÃO QUE ISTO PEGA ────────────────────────────────────────────

Toda rota de usuário consulta com `db.cliente_do_usuario(jwt)`, para que o RLS
decida a posse no banco. O caminho de ingestão é a exceção: ele usa
`db.cliente_de_ingestao()`, que carrega uma chave de serviço.

A regressão perigosa é alguém, um dia, escrever uma rota nova com
`db.cliente_de_ingestao()` — porque é mais simples, porque copiou de outro
lugar, porque estava depurando. Aquela rota funcionaria perfeitamente, passaria
em todo teste de rota, **e nenhum teste de RLS cairia**: o RLS não é violado,
ele é ignorado. É o modo de falha mais silencioso que este sistema tem.

Os testes daqui leem a árvore sintática dos módulos (`ast`) e afirmam QUEM pode
tocar o cliente privilegiado. Não é análise de comportamento — é análise de
código, e é de propósito: o comportamento errado aqui só apareceria com dois
usuários reais e uma rota que ninguém pensou em testar.

── POR QUE A LISTA É EXPLÍCITA ──────────────────────────────────────────

`FUNCOES_AUTORIZADAS` enumera nome por nome, com a justificativa ao lado.
Acrescentar uma entrada é um ato deliberado, que aparece no diff e pede
explicação no commit. Um teste que apenas contasse ocorrências, ou que
permitisse "qualquer coisa em database.py", não teria essa propriedade.
"""
import ast
import pathlib

import pytest

WEB_APP = pathlib.Path(__file__).resolve().parent.parent

# O acessor do cliente privilegiado. Qualquer referência a este nome, em
# qualquer módulo, é exatamente o que este arquivo controla.
ACESSOR = "cliente_de_ingestao"

# O nome ANTIGO, genérico. Foi renomeado justamente para que "pegar um cliente"
# deixasse de parecer uma operação neutra. Se reaparecer, é sinal de código
# ressuscitado de um commit anterior à SEC-06 — e provavelmente com `.table()`
# em cima, que agora falharia por permissão em produção.
ACESSOR_ANTIGO = "get_client"

# ---------------------------------------------------------------------
# As exceções permitidas. Cada uma com o motivo, e cada uma exercitada por
# teste em `tests/rls/test_rls_ingestao.py` sob o papel real.
# ---------------------------------------------------------------------
FUNCOES_AUTORIZADAS = {
    # database.py — a definição do próprio acessor.
    "cliente_de_ingestao": (
        "e o proprio acessor: e aqui que o cliente privilegiado nasce"
    ),
    # database.py — health check. Chama `sanidade()`, que não le dado nenhum.
    "verificar_conexao": (
        "/health precisa responder sem autenticacao. Chama sanidade(), que "
        "confere rede e esquema sem privilegio de tabela"
    ),
    # database.py — resolve token -> (device, dono) via `resolver_dispositivo`.
    "get_device_by_token_hash": (
        "o ESP32 nao tem sessao de usuario: nao existe JWT para montar cliente "
        "do usuario. Chama resolver_dispositivo(), que nao devolve token_hash"
    ),
    # database.py — a gravação do caminho do dispositivo.
    "registrar_leitura": (
        "gravacao da ingestao por token. O dono e resolvido dentro do banco, a "
        "partir do token — nao ha parametro para escolher user_id"
    ),
}

# Módulos onde o acessor pode ser referenciado. `routes.py` NÃO está aqui: a
# rota de ingestão fala com `db.registrar_leitura(...)`, e não pega o cliente.
MODULOS_AUTORIZADOS = {"database.py"}


def _modulos_da_aplicacao():
    """Todo .py da web-app, menos os testes."""
    for caminho in sorted(WEB_APP.glob("*.py")):
        yield caminho


def _arvore(caminho):
    return ast.parse(caminho.read_text(encoding="utf-8"), filename=str(caminho))


def _funcao_que_contem(arvore, alvo):
    """Nome da função mais interna que contém `alvo`, ou None no nível do módulo."""
    encontrado = None
    for no in ast.walk(arvore):
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for descendente in ast.walk(no):
                if descendente is alvo:
                    # Preferir a função mais interna: `init_routes` contém todas
                    # as rotas, e culpar ela esconderia qual rota é o problema.
                    if encontrado is None or _profundidade(no) >= _profundidade(encontrado):
                        encontrado = no
    return encontrado.name if encontrado else None


def _profundidade(no):
    return len(list(ast.walk(no)))


def _referencias(arvore, nome):
    """Todos os nós que mencionam `nome` como atributo ou como chamada."""
    achados = []
    for no in ast.walk(arvore):
        if isinstance(no, ast.Attribute) and no.attr == nome:
            achados.append(no)
        elif isinstance(no, ast.FunctionDef) and no.name == nome:
            achados.append(no)
        elif isinstance(no, ast.Name) and no.id == nome:
            achados.append(no)
    return achados


# =====================================================================
# 1. Quem toca o cliente privilegiado
# =====================================================================

def test_apenas_funcoes_autorizadas_tocam_o_cliente_de_ingestao():
    infratores = []

    for caminho in _modulos_da_aplicacao():
        arvore = _arvore(caminho)
        for no in _referencias(arvore, ACESSOR):
            if isinstance(no, ast.FunctionDef):
                dono = no.name  # a definição do acessor
            else:
                dono = _funcao_que_contem(arvore, no)

            if caminho.name not in MODULOS_AUTORIZADOS or dono not in FUNCOES_AUTORIZADAS:
                infratores.append(f"{caminho.name}:{no.lineno} dentro de {dono!r}")

    assert not infratores, (
        "referencia a `%s` fora das excecoes autorizadas:\n  %s\n\n"
        "Se uma rota nova precisa de fato do cliente privilegiado, ela NAO "
        "esta sujeita ao RLS — nenhum teste de tests/rls/ cairia por causa "
        "dela. Acrescente a excecao em FUNCOES_AUTORIZADAS com a justificativa, "
        "e explique no commit por que o cliente do usuario nao serve."
        % (ACESSOR, "\n  ".join(infratores))
    )


def test_o_acessor_antigo_nao_ressuscitou():
    """`get_client` foi renomeado na SEC-06. Reaparecer é código de antes."""
    achados = []
    for caminho in _modulos_da_aplicacao():
        arvore = _arvore(caminho)
        for no in _referencias(arvore, ACESSOR_ANTIGO):
            # `_get_client_anon` é outro método, e é legítimo: a chave anon não
            # é privilegiada. O nome dele contém o antigo, então filtramos.
            if isinstance(no, ast.FunctionDef) and no.name != ACESSOR_ANTIGO:
                continue
            achados.append(f"{caminho.name}:{no.lineno}")

    assert not achados, (
        "`%s` reapareceu em: %s. Esse nome foi trocado por `%s` justamente "
        "para que pegar o cliente privilegiado deixasse de parecer neutro. "
        "Codigo anterior a SEC-06 provavelmente usa `.table(...)` em cima "
        "dele, o que agora falha por permissao em producao."
        % (ACESSOR_ANTIGO, ", ".join(achados), ACESSOR)
    )


# =====================================================================
# 2. As rotas de usuário usam o cliente do usuário
# =====================================================================

# Rotas que legitimamente NÃO montam cliente do usuário, com o motivo.
ROTAS_SEM_CLIENTE_DO_USUARIO = {
    "health": "sem autenticacao de proposito; chama sanidade()",
    "receive_data": "ingestao: o ESP32 nao tem JWT (caminho por token)",
}


def _rotas_de(arvore):
    """Funções decoradas com @app.route, pelo nome."""
    rotas = {}
    for no in ast.walk(arvore):
        if not isinstance(no, ast.FunctionDef):
            continue
        for decorador in no.decorator_list:
            alvo = decorador.func if isinstance(decorador, ast.Call) else decorador
            if isinstance(alvo, ast.Attribute) and alvo.attr == "route":
                rotas[no.name] = no
    return rotas


def test_toda_rota_de_usuario_consulta_pelo_cliente_do_usuario():
    """Uma rota autenticada que não passe pelo JWT não está sob RLS.

    Procura, no corpo de cada rota, referência a `cliente_do_usuario` (direta
    ou pelo atalho `_cliente_do_usuario`) OU a um método do `db` que já recebe
    o jwt. Rota que não tem nenhum dos dois, e não está na lista de exceções,
    está consultando de outro jeito — e é o que precisa ser olhado.
    """
    arvore = _arvore(WEB_APP / "routes.py")
    rotas = _rotas_de(arvore)
    assert rotas, "nenhuma rota encontrada em routes.py — o parser quebrou?"

    # Métodos de `db` que recebem o jwt e portanto consultam sob o RLS.
    PASSA_JWT = {
        "cliente_do_usuario",
        "get_leituras_do_usuario",
        "registrar_leitura_da_sessao",
        "apagar_minha_conta",
    }

    sem_rls = []
    for nome, no in rotas.items():
        if nome in ROTAS_SEM_CLIENTE_DO_USUARIO:
            continue
        fontes = {
            d.attr
            for d in ast.walk(no)
            if isinstance(d, ast.Attribute)
        } | {
            d.id for d in ast.walk(no) if isinstance(d, ast.Name)
        }
        if not (fontes & PASSA_JWT) and "_cliente_do_usuario" not in fontes:
            sem_rls.append(nome)

    assert not sem_rls, (
        "rota(s) que nao consultam com o JWT do usuario: %s.\n"
        "Uma rota assim nao esta sujeita ao RLS. Se for intencional, "
        "acrescente em ROTAS_SEM_CLIENTE_DO_USUARIO com o motivo."
        % ", ".join(sorted(sem_rls))
    )


# =====================================================================
# 3. A rota de ingestão não carimba o dono em Python
# =====================================================================

def test_a_ingestao_nao_monta_user_id_no_payload():
    """O dono tem de vir do banco, não de um dicionário em Python (SEC-06).

    Antes da 005, `receive_data` montava `"user_id": device["user_id"]`. Estava
    correto — mas era uma linha de Python entre uma chave vazada e a posse de
    dado alheio. Hoje a função no banco resolve o dono a partir do token, e
    reintroduzir a chave no payload seria voltar a permitir escolher o dono.
    """
    arvore = _arvore(WEB_APP / "routes.py")
    rota = _rotas_de(arvore).get("receive_data")
    assert rota is not None

    chaves = [
        no.value
        for no in ast.walk(rota)
        if isinstance(no, ast.Constant) and isinstance(no.value, str)
    ]
    assert "user_id" not in chaves, (
        "`receive_data` voltou a mencionar 'user_id'. O carimbo do dono "
        "pertence a `registrar_leitura`/`registrar_leitura_da_sessao` no banco "
        "(migrations/005): la nao existe parametro para escolher o dono."
    )


# =====================================================================
# 4. A configuração não esconde o privilégio alto
# =====================================================================

def test_o_env_example_documenta_a_chave_de_ingestao():
    """Quem copia o `.env.example` tem de ver a chave certa primeiro."""
    texto = (WEB_APP / ".env.example").read_text(encoding="utf-8")
    assert "SUPABASE_INGESTAO_KEY" in texto, (
        ".env.example nao menciona SUPABASE_INGESTAO_KEY; quem configurar o "
        "projeto vai usar a service_role sem saber que ha opcao melhor."
    )


def test_o_fallback_para_service_role_avisa():
    """Cair na service_role é aceitável em transição, mas não em silêncio."""
    texto = (WEB_APP / "database.py").read_text(encoding="utf-8")
    assert "logger.warning" in texto and "ALTO PRIVILEGIO" in texto, (
        "o fallback para SUPABASE_SERVICE_ROLE_KEY tem de emitir aviso: sem "
        "ele, a configuracao insegura parece a configuracao normal."
    )


@pytest.mark.parametrize(
    "proibido",
    [
        # A chave de serviço não pode ser lida por código de frontend, e o
        # nome da variável com prefixo VITE_ vira bundle público no Vite.
        "VITE_SUPABASE_SERVICE",
        "VITE_SUPABASE_INGESTAO",
    ],
)
def test_nenhuma_chave_privilegiada_com_prefixo_de_bundle(proibido):
    """`VITE_*` é exposto no bundle por definição. Nada privilegiado ali."""
    for caminho in _modulos_da_aplicacao():
        assert proibido not in caminho.read_text(encoding="utf-8"), (
            f"{caminho.name} menciona {proibido}: variavel VITE_ vai para o "
            "bundle publico do frontend."
        )
