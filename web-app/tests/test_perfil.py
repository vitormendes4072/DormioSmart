"""As rotas de perfil (PERFIL-01, LGPD art. 18, III).

Estes testes mockam o banco, como o resto de `tests/`. O que eles verificam é
a **rota**: a validação do corpo, o reparo da linha ausente, o repasse do JWT,
e a honestidade da resposta quando a escrita não acontece.

O que eles **não** provam, e está em `tests/rls/test_rls_isolamento.py` contra
Postgres real: que a Ana não lê nem escreve o perfil do Bruno. Mock nenhum
prova isolamento entre usuários — é o §4 das lições (a suíte de RLS contra
Supabase mockado), e a separação aqui é deliberada pelo mesmo motivo.

O par adversarial desta camada é outro, e é o que ela consegue provar: que
**não existe parâmetro por onde informar o dono**. Ver a seção "o dono nunca
vem do corpo".
"""
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

import database
import perfil
from routes import init_routes

JWT_ANA = "jwt-da-ana"
JWT_BRUNO = "jwt-do-bruno"
ID_ANA = "aaaaaaaa-0000-4000-8000-aaaaaaaaaaaa"
ID_BRUNO = "bbbbbbbb-0000-4000-8000-bbbbbbbbbbbb"

PERFIL_DA_ANA = {"nome": "Ana", "idade": 22, "updated_at": "2026-10-17T12:00:00Z"}

_SESSAO = {"Authorization": f"Bearer {JWT_ANA}"}


def _client():
    app = Flask(__name__)
    init_routes(app)
    app.testing = True
    return app.test_client()


def _autenticado(usuario=ID_ANA):
    return patch.object(database.db, "validar_token_de_usuario", return_value=usuario)


# =====================================================================
# autenticação
# =====================================================================

def test_nenhuma_rota_de_perfil_responde_sem_jwt():
    c = _client()
    respostas = [c.get("/api/me/perfil"), c.patch("/api/me/perfil", json={"nome": "x"})]
    assert [r.status_code for r in respostas] == [401, 401]


def test_sessao_invalida_nao_chega_ao_banco():
    """401 antes de qualquer ida ao banco: token inválido não gasta consulta."""
    with _autenticado(usuario=None), \
         patch.object(database.db, "cliente_do_usuario") as cliente:
        resposta = _client().get("/api/me/perfil", headers=_SESSAO)
    assert resposta.status_code == 401
    cliente.assert_not_called()


# =====================================================================
# GET — leitura
# =====================================================================

def test_get_devolve_nome_e_idade_da_tabela():
    with _autenticado(), \
         patch.object(database.db, "cliente_do_usuario", return_value=MagicMock()), \
         patch.object(perfil, "ler", return_value=dict(PERFIL_DA_ANA)):
        resposta = _client().get("/api/me/perfil", headers=_SESSAO)

    assert resposta.status_code == 200
    assert resposta.get_json() == {**PERFIL_DA_ANA, "perfil_criado_agora": False}


def test_get_usa_o_cliente_do_usuario_com_o_jwt_da_requisicao():
    """O RLS só decide a posse se o JWT chegar ao banco.

    Uma rota que usasse o cliente privilegiado funcionaria igual nos testes de
    rota e **nenhum teste de RLS cairia** — o RLS não seria violado, seria
    ignorado. `tests/test_privilegio_minimo.py` guarda isso lendo a árvore
    sintática; aqui se confere o outro lado: que o token repassado é o da
    requisição, e não um qualquer.
    """
    with _autenticado(), \
         patch.object(database.db, "cliente_do_usuario", return_value=MagicMock()) as cliente, \
         patch.object(perfil, "ler", return_value=dict(PERFIL_DA_ANA)):
        _client().get("/api/me/perfil", headers=_SESSAO)

    cliente.assert_called_once_with(JWT_ANA)


def test_get_repara_a_linha_ausente_semeando_pelo_metadado():
    """O caso do `DIAGNOSTICO-perfil-nao-criado.sql`, que já aconteceu.

    Sem o reparo, quem tem conta sem linha em `profiles` veria nome em branco
    depois de ter digitado o nome no cadastro.
    """
    criado = {"nome": "Ana", "idade": None, "updated_at": "2026-10-17T12:00:00Z"}
    with _autenticado(), \
         patch.object(database.db, "cliente_do_usuario", return_value=MagicMock()), \
         patch.object(database.db, "nome_do_metadado", return_value="Ana"), \
         patch.object(perfil, "ler", return_value={}), \
         patch.object(perfil, "gravar", return_value=criado) as gravar:
        resposta = _client().get("/api/me/perfil", headers=_SESSAO)

    assert resposta.status_code == 200
    assert resposta.get_json() == {**criado, "perfil_criado_agora": True}
    gravar.assert_called_once()
    _, argumentos, _ = gravar.mock_calls[0]
    assert argumentos[1] == ID_ANA
    assert argumentos[2] == {"nome": "Ana"}


def test_get_repara_mesmo_sem_semente():
    """Metadado sem nome, ou Auth fora do ar: o perfil nasce com nome nulo.

    Nulo é estado que a tela sabe mostrar. Perfil inexistente, não — e era o
    que a ausência de reparo deixaria.
    """
    criado = {"nome": None, "idade": None, "updated_at": "2026-10-17T12:00:00Z"}
    with _autenticado(), \
         patch.object(database.db, "cliente_do_usuario", return_value=MagicMock()), \
         patch.object(database.db, "nome_do_metadado", return_value=None), \
         patch.object(perfil, "ler", return_value={}), \
         patch.object(perfil, "gravar", return_value=criado):
        resposta = _client().get("/api/me/perfil", headers=_SESSAO)

    assert resposta.status_code == 200
    assert resposta.get_json()["perfil_criado_agora"] is True
    assert resposta.get_json()["nome"] is None


def test_get_nao_repara_quando_a_leitura_so_falhou():
    """A distinção que o `perfil.ler` existe para fazer.

    `{}` é "não há linha"; `None` é "não deu para ler". Confundir os dois faria
    a rota escrever em cima de um banco que só estava fora do ar — e, no pior
    caso, apagar um nome existente com a semente do metadado.
    """
    with _autenticado(), \
         patch.object(database.db, "cliente_do_usuario", return_value=MagicMock()), \
         patch.object(perfil, "ler", return_value=None), \
         patch.object(perfil, "gravar") as gravar:
        resposta = _client().get("/api/me/perfil", headers=_SESSAO)

    assert resposta.status_code == 503
    gravar.assert_not_called()


def test_get_sem_cliente_responde_503():
    with _autenticado(), \
         patch.object(database.db, "cliente_do_usuario", return_value=None):
        resposta = _client().get("/api/me/perfil", headers=_SESSAO)
    assert resposta.status_code == 503


def test_get_com_reparo_que_falha_responde_503_e_nao_finge_perfil_vazio():
    with _autenticado(), \
         patch.object(database.db, "cliente_do_usuario", return_value=MagicMock()), \
         patch.object(database.db, "nome_do_metadado", return_value="Ana"), \
         patch.object(perfil, "ler", return_value={}), \
         patch.object(perfil, "gravar", return_value=None):
        resposta = _client().get("/api/me/perfil", headers=_SESSAO)

    assert resposta.status_code == 503
    assert "nome" not in resposta.get_json()


# =====================================================================
# PATCH — correção
# =====================================================================

def _patch(corpo, gravado=PERFIL_DA_ANA, usuario=ID_ANA, jwt=JWT_ANA):
    """Chama PATCH e devolve (resposta, mock de perfil.gravar)."""
    with _autenticado(usuario=usuario), \
         patch.object(database.db, "cliente_do_usuario", return_value=MagicMock()), \
         patch.object(perfil, "gravar", return_value=gravado) as gravar:
        resposta = _client().patch(
            "/api/me/perfil", json=corpo, headers={"Authorization": f"Bearer {jwt}"}
        )
    return resposta, gravar


def test_patch_grava_so_o_nome():
    resposta, gravar = _patch({"nome": "Ana Maria"})
    assert resposta.status_code == 200
    assert gravar.mock_calls[0].args[2] == {"nome": "Ana Maria"}


def test_patch_grava_so_a_idade():
    """Parcial de verdade: mexer na idade não pode tocar no nome."""
    resposta, gravar = _patch({"idade": 30})
    assert resposta.status_code == 200
    assert gravar.mock_calls[0].args[2] == {"idade": 30}


def test_patch_com_idade_nula_apaga_a_idade():
    """Art. 18, IV ao alcance de um clique: `null` retira o dado.

    Campo AUSENTE e campo `null` são diferentes, e é essa diferença que
    permite retirar a idade sem apagar o nome.
    """
    resposta, gravar = _patch({"idade": None})
    assert resposta.status_code == 200
    assert gravar.mock_calls[0].args[2] == {"idade": None}


def test_patch_devolve_a_linha_como_ficou_no_banco():
    """Confirmar a escrita, não a intenção (FIX-02).

    O corpo pede "Ana Maria"; o dublê do banco devolve "Ana". A resposta tem de
    ser a do banco — se devolvesse o que foi pedido, uma gravação que o banco
    normalizasse de outro jeito apareceria na tela como se tivesse sido aceita
    exatamente como digitada.
    """
    resposta, _ = _patch({"nome": "Ana Maria"}, gravado=dict(PERFIL_DA_ANA, nome="Ana"))
    assert resposta.get_json()["nome"] == "Ana"


def test_patch_sem_corpo_responde_400():
    resposta, gravar = _patch(None)
    assert resposta.status_code == 400
    gravar.assert_not_called()


def test_patch_vazio_responde_400_e_diz_o_que_mandar():
    resposta, gravar = _patch({})
    assert resposta.status_code == 400
    assert "nome" in resposta.get_json()["error"]
    gravar.assert_not_called()


def test_patch_que_falha_na_gravacao_responde_503():
    """Não há 200 sem escrita confirmada. É o FIX-02 nesta rota."""
    resposta, _ = _patch({"nome": "Ana Maria"}, gravado=None)
    assert resposta.status_code == 503


# --- o dono nunca vem do corpo -------------------------------------------

@pytest.mark.parametrize("campo", ["id", "user_id", "idadee", "email", "nome_completo"])
def test_patch_recusa_campo_desconhecido(campo):
    """`id` e `user_id` caem aqui, e não em "ignorado em silêncio".

    Ignorar responderia **sucesso** a um pedido que não foi atendido — §6 das
    lições na forma mais fácil de cometer. E recusar em vez de descartar deixa
    a tentativa visível no log de acesso em vez de invisível.
    """
    resposta, gravar = _patch({campo: ID_BRUNO})
    assert resposta.status_code == 400
    assert campo in resposta.get_json()["error"]
    gravar.assert_not_called()


def test_patch_com_id_alheio_junto_de_campo_valido_tambem_recusa():
    """O caso que um "ignore o que não conhece" deixaria passar: metade do
    corpo é válida, e a outra metade é uma tentativa de escolher o dono."""
    resposta, gravar = _patch({"nome": "Invadido", "id": ID_BRUNO})
    assert resposta.status_code == 400
    gravar.assert_not_called()


def test_o_dono_gravado_e_o_do_jwt_e_nao_o_do_corpo():
    """Dois titulares, dois ids — e o id vem do token, sempre.

    Isto **não** é o teste de isolamento: ele está em
    `tests/rls/test_rls_isolamento.py`, contra Postgres real. O que se prova
    aqui é mais estreito e ainda assim necessário: o valor que a rota repassa
    como dono é o do JWT validado, e não há parâmetro de requisição que o
    altere.
    """
    _, gravar_ana = _patch({"nome": "Ana"}, usuario=ID_ANA, jwt=JWT_ANA)
    _, gravar_bruno = _patch({"nome": "Bruno"}, usuario=ID_BRUNO, jwt=JWT_BRUNO)

    assert gravar_ana.mock_calls[0].args[1] == ID_ANA
    assert gravar_bruno.mock_calls[0].args[1] == ID_BRUNO


# =====================================================================
# validação do corpo (unidade de `perfil.py`)
# =====================================================================

@pytest.mark.parametrize(
    "valor",
    [
        True,          # isinstance(True, int) e verdadeiro em Python
        False,
        "30",          # texto que parece numero
        30.0,          # float, inclusive redondo
        -1,
        150,
        [30],
    ],
)
def test_idade_invalida_e_recusada(valor):
    idade, erro = perfil.validar_idade(valor)
    assert idade is None
    assert erro


def test_idade_booleana_nao_vira_um_ano():
    """O defeito que `isinstance(True, int)` produziria: `{"idade": true}`
    gravaria 1 — plausível, errado e silencioso (§7 das lições)."""
    assert perfil.validar_idade(True) == (None, "idade deve ser um numero inteiro ou nulo")


@pytest.mark.parametrize("valor", [0, 1, 22, 149, None])
def test_idade_valida_passa(valor):
    idade, erro = perfil.validar_idade(valor)
    assert erro is None
    assert idade == valor


@pytest.mark.parametrize("valor", ["", "   ", "\t\n", 42, None, ["Ana"]])
def test_nome_invalido_e_recusado(valor):
    nome, erro = perfil.validar_nome(valor)
    assert nome is None
    assert erro


def test_nome_longo_demais_e_recusado_antes_do_banco():
    nome, erro = perfil.validar_nome("A" * (perfil.NOME_MAXIMO + 1))
    assert nome is None
    assert str(perfil.NOME_MAXIMO) in erro


def test_nome_no_limite_passa():
    nome, erro = perfil.validar_nome("A" * perfil.NOME_MAXIMO)
    assert erro is None
    assert len(nome) == perfil.NOME_MAXIMO


def test_nome_e_normalizado_como_no_cliente():
    """"Ana  Maria" e "Ana Maria" são o mesmo nome para quem digitou.

    A normalização tem de ser a MESMA dos dois lados: se divergisse, o cliente
    concluiria que nada mudou e o servidor gravaria outra coisa.
    """
    assert perfil.validar_nome("  Ana   Maria  ") == ("Ana Maria", None)


def test_a_faixa_de_idade_espelha_a_constraint_da_migracao_001():
    """Divergir daqui trocaria um 400 com mensagem útil por um erro de
    constraint do Postgres. O par é `idade >= 0 and idade < 150`."""
    assert (perfil.IDADE_MINIMA, perfil.IDADE_MAXIMA) == (0, 149)
