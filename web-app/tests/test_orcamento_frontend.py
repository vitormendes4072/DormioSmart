import importlib.util
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "conferir_pacote_frontend.py"
_spec = importlib.util.spec_from_file_location("conferir_pacote_frontend", _SCRIPT)
_orcamento = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_orcamento)


@pytest.fixture
def manifesto():
    return {
        "index.html": {"file": "entrada.js", "isEntry": True, "imports": ["compartilhado"]},
        "src/pages/Dashboard.tsx": {
            "file": "painel.js",
            "imports": ["compartilhado"],
            "css": ["painel.css"],
            "dynamicImports": ["privacidade"],
        },
        "compartilhado": {"file": "compartilhado.js", "imports": ["transitivo"], "css": ["global.css"]},
        "transitivo": {"file": "transitivo.js"},
        "privacidade": {"file": "privacidade.js", "css": ["privacidade.css"]},
    }


@pytest.mark.parametrize(
    ("arquivo", "entra_na_soma"),
    [
        ("transitivo.js", True),
        ("painel.css", True),
        ("global.css", True),
        ("privacidade.js", False),
        ("index.html", True),
    ],
)
def test_orcamento_mede_apenas_arquivos_do_primeiro_carregamento(
    manifesto, tmp_path, arquivo, entra_na_soma,
):
    for nome in ("index.html", *(item["file"] for item in manifesto.values()),
                 "painel.css", "global.css", "privacidade.css"):
        (tmp_path / nome).write_bytes(b"")
    antes = _orcamento.medir_rota(manifesto, "Dashboard", tmp_path)
    alvo = tmp_path / arquivo
    gzip_vazio = _orcamento.tamanho_gzip(alvo)
    alvo.write_bytes(b"carregamento inicial")
    depois = _orcamento.medir_rota(manifesto, "Dashboard", tmp_path)
    variacao = (alvo.stat().st_size, _orcamento.tamanho_gzip(alvo) - gzip_vazio)
    assert tuple(atual - original for original, atual in zip(antes, depois)) == (
        variacao if entra_na_soma else (0, 0)
    )


def test_pagina_ausente_reprova_com_diagnostico(monkeypatch, tmp_path, capsys):
    pasta_manifesto = tmp_path / ".vite"
    pasta_manifesto.mkdir()
    (pasta_manifesto / "manifest.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(_orcamento, "DIST", tmp_path)

    assert _orcamento.main() == 1
    mensagem = capsys.readouterr().err
    assert "Dashboard: página ausente do manifesto" in mensagem
    assert "Login: página ausente do manifesto" in mensagem
