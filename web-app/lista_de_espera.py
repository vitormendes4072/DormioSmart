"""A lista de espera do lançamento (UI-14).

Quem ainda não tem conta deixa o e-mail para ser avisado do lançamento e convidado para os
primeiros testes. A garantia é do BANCO (migração 022): ninguém do cliente lê a tabela, a escrita
só passa por `inscrever_na_lista_de_espera`, e o teto de inscrições por hora vive lá. Este módulo
é a primeira barreira, a que dá ao visitante uma resposta útil:

  · valida o pedido inteiro antes de falar com o banco, e diz qual campo está errado;
  · descarta em silêncio o pedido que preencheu o campo-isca (`site`), que nenhuma pessoa vê;
  · exige as duas confirmações marcadas (o consentimento e os 18 anos) e a versão vigente do
    texto, para que a tela que mostrou um texto antigo não registre consentimento para o novo.

`VERSAO` é a mesma de `public.versao_da_lista_de_espera()` (022) e de `VERSAO_DA_LISTA` no
frontend; `tests/test_lista_de_espera.py` confere as três.
"""
import re

VERSAO = "2026-11-19"

# O mesmo formato que a restrição do banco aceita (022), para o Flask não deixar passar o que o
# banco recusaria com um 503 sem explicação.
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")
EMAIL_MAX = 254
NOME_MAX = 80
# Um pedido legítimo tem uns 200 bytes. Acima disto, nem se lê.
CORPO_MAX = 2048

CAMPOS = {"email", "nome", "consentimento", "maioridade", "versao", "site"}


class PedidoInvalido(ValueError):
    """O pedido não serve; `campo` diz qual parte, para a tela apontar."""

    def __init__(self, mensagem, campo=None):
        super().__init__(mensagem)
        self.campo = campo


class VersaoDesatualizada(ValueError):
    """A tela mostrou um texto de consentimento que não é o vigente."""


def eh_isca(corpo):
    """True quando o campo-isca veio preenchido: quem preenche não é uma pessoa."""
    return isinstance(corpo, dict) and bool(str(corpo.get("site") or "").strip())


def validar(corpo):
    """Devolve `(email, nome)` normalizados, ou levanta `PedidoInvalido`/`VersaoDesatualizada`."""
    if not isinstance(corpo, dict):
        raise PedidoInvalido("o corpo tem de ser um objeto JSON")
    estranhos = sorted(set(corpo) - CAMPOS)
    if estranhos:
        raise PedidoInvalido("campos desconhecidos: " + ", ".join(estranhos))

    email = corpo.get("email")
    if not isinstance(email, str):
        raise PedidoInvalido("informe o e-mail", "email")
    email = email.strip().lower()
    if len(email) > EMAIL_MAX or not _EMAIL.match(email):
        raise PedidoInvalido("e-mail invalido", "email")

    nome = corpo.get("nome")
    if nome is not None and not isinstance(nome, str):
        raise PedidoInvalido("nome invalido", "nome")
    nome = " ".join(nome.split()) if nome else ""
    if len(nome) > NOME_MAX:
        raise PedidoInvalido(f"o nome passa de {NOME_MAX} caracteres", "nome")

    # `is True`, e não verdade: "sim", 1 ou uma lista não são uma caixa marcada.
    if corpo.get("consentimento") is not True:
        raise PedidoInvalido("o consentimento e obrigatorio", "consentimento")
    if corpo.get("maioridade") is not True:
        raise PedidoInvalido("a lista e so para maiores de 18 anos", "maioridade")

    if corpo.get("versao") != VERSAO:
        raise VersaoDesatualizada()

    return email, (nome or None)
