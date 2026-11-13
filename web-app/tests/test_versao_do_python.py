"""O Python que testa o backend no CI e o da producao (CI-10).

A Vercel escolhe o Python do backend pelo `.python-version` da raiz (antes de
13/11 nao havia nenhum, e ela caia no padrao dela, 3.12, enquanto o CI testava
em 3.11). O CI le o mesmo arquivo (`python-version-file`). Este teste prende os
dois: se alguem trocar a versao do job sem trocar o arquivo, ou o contrario,
o CI reprova.

Fora do CI ele pula: na maquina de quem desenvolve o Python e o que estiver
instalado (no Windows do autor, 3.13), e isso nao diz nada sobre a producao.
"""
import os
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]


def versao_declarada():
    texto = (RAIZ / ".python-version").read_text(encoding="utf-8").strip()
    maior, menor = texto.split(".")[:2]
    return int(maior), int(menor)


def test_o_arquivo_declara_uma_versao():
    maior, menor = versao_declarada()
    assert maior == 3 and menor >= 11


@pytest.mark.skipif(os.environ.get("CI") != "true", reason="so vale no CI, que le o .python-version")
def test_o_ci_roda_no_python_da_producao():
    assert sys.version_info[:2] == versao_declarada(), (
        f"o CI roda {sys.version_info[0]}.{sys.version_info[1]}, "
        f"e o .python-version (o da Vercel) diz {versao_declarada()}"
    )
