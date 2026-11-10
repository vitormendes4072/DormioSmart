"""Toda coluna que a ingestão grava está descrita na política de privacidade (LGPD-11).

── POR QUE EXISTE ──────────────────────────────────────────────────────────

A política de privacidade diz ao titular que dados são coletados (seção 2.2). Ela já ficou atrás
do código três vezes: a idade em 17/10, a tela de correção em 17/10 e, até 10/11, as seis medidas
de movimento por época e a direção da gravidade, que entraram na migração 010 (30/10) e passaram
onze dias gravando sem que a política as citasse. As notas da própria política registravam que
"nada liga uma afirmação desta política a um teste".

Este teste liga a parte que dá para ligar: lê, nas migrações REAIS, a lista de colunas que as duas
funções de gravação inserem (a versão mais recente de cada uma) e exige que:

  1. toda coluna esteja neste mapa — coluna nova reprova até alguém decidir como descrevê-la;
  2. o trecho do mapa esteja na seção 2.2 do texto publicável da política.

── O QUE NÃO COBRE ──────────────────────────────────────────────────────────

O que não é coluna de `sleep_data`: o que fica no celular (seção 2.3), as finalidades (seção 3) e
os direitos (seção 6). E não confere se o texto descreve BEM a coluna — só que ele a cita.
"""
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
MIGRACOES = RAIZ / "web-app" / "migrations"
POLITICA = RAIZ / "docs" / "POLITICA-DE-PRIVACIDADE.md"

FUNCOES = ("registrar_leitura", "registrar_leitura_da_sessao")

# Coluna -> trecho que tem de estar na seção 2.2 (sem diferenciar maiúsculas).
DESCRICAO = {
    "accel_x": "aceleração nos três eixos",
    "accel_y": "aceleração nos três eixos",
    "accel_z": "aceleração nos três eixos",
    "movimento_total": "magnitude",
    "status": "rótulo de estado",
    "temp": "temperatura",
    "gyro_x": "giroscópio",
    "gyro_y": "giroscópio",
    "gyro_z": "giroscópio",
    "captured_at": "quando a medição foi feita",
    "epoca_segundos": "duração da janela",
    "metodo_agregacao": "método",
    "amostras": "número de amostras",
    "enmo_media": "seis medidas de movimento",
    "enmo_desvio": "seis medidas de movimento",
    "enmo_max": "seis medidas de movimento",
    "mag_din_media": "seis medidas de movimento",
    "zcr": "seis medidas de movimento",
    "p_frac": "seis medidas de movimento",
    "g_x": "direção da gravidade",
    "g_y": "direção da gravidade",
    "g_z": "direção da gravidade",
    "fs_features": "taxa de amostragem",
    "user_id": "associar cada leitura ao seu dono",  # seção 3: o dono, não um dado medido
    "device_id": "identificador do aparelho",
}
# `user_id` é o vínculo com a conta, descrito na seção 3, e não na 2.2.
FORA_DA_SECAO_22 = {"user_id"}


def _colunas_inseridas(nome):
    """As colunas do `insert` da versão mais recente de `public.<nome>`."""
    padrao = re.compile(
        rf"create\s+(?:or\s+replace\s+)?function\s+public\.{nome}\s*\(.*?\$\$(.*?)\$\$",
        re.S | re.I,
    )
    ultima = None
    for arquivo in sorted(MIGRACOES.glob("0[0-9][0-9]_*.sql")):
        for corpo in padrao.findall(arquivo.read_text(encoding="utf-8")):
            ultima = (arquivo.name, corpo)
    assert ultima, f"nenhuma migração define public.{nome}"
    arquivo, corpo = ultima
    m = re.search(r"insert\s+into\s+public\.sleep_data\s*\((.*?)\)\s*values", corpo, re.S | re.I)
    assert m, f"{arquivo}: public.{nome} sem insert em sleep_data"
    return arquivo, [c.strip() for c in m.group(1).split(",") if c.strip()]


def _texto_publicavel():
    doc = POLITICA.read_text(encoding="utf-8")
    i = doc.index("── TEXTO")
    j = doc.index("── FIM DO TEXTO")
    return doc[i:j]


def _secao(texto, inicio, fim):
    """O trecho entre os dois títulos, em minúsculas e com o espaço normalizado: a quebra de
    linha do Markdown não pode esconder um trecho que está lá."""
    i = texto.index(inicio)
    return " ".join(texto[i:texto.index(fim, i)].split()).lower()


@pytest.fixture(scope="module")
def politica():
    texto = _texto_publicavel()
    return {"2.2": _secao(texto, "### 2.2", "### 2.3"),
            "3": _secao(texto, "## 3.", "## 4.")}


@pytest.mark.parametrize("funcao", FUNCOES)
def test_toda_coluna_gravada_tem_descricao(funcao):
    arquivo, colunas = _colunas_inseridas(funcao)
    sem = [c for c in colunas if c not in DESCRICAO]
    assert not sem, (
        f"{arquivo}: public.{funcao} grava {sem}, que a política de privacidade não descreve. "
        "Descreva a coluna na seção 2.2 e acrescente-a a DESCRICAO neste teste.")


@pytest.mark.parametrize("funcao", FUNCOES)
def test_a_descricao_de_cada_coluna_esta_na_politica(funcao, politica):
    _, colunas = _colunas_inseridas(funcao)
    faltando = []
    for c in colunas:
        secao = "3" if c in FORA_DA_SECAO_22 else "2.2"
        if DESCRICAO[c].lower() not in politica[secao]:
            faltando.append((c, DESCRICAO[c], secao))
    assert not faltando, f"trechos ausentes da política: {faltando}"


def test_o_leitor_de_migracoes_acha_as_colunas_de_verdade():
    """Guarda do próprio teste: se o regex parar de casar, os dois acima passariam vazios."""
    for funcao in FUNCOES:
        arquivo, colunas = _colunas_inseridas(funcao)
        assert arquivo >= "014", f"public.{funcao} lida de {arquivo}, não da versão mais recente"
        assert {"enmo_media", "g_x", "fs_features", "captured_at"} <= set(colunas)
        assert len(colunas) >= 20
