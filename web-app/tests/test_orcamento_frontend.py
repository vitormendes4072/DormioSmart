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


@pytest.fixture
def dist_para_inspecao(monkeypatch, tmp_path):
    dist = tmp_path / "dist"
    pasta_manifesto = dist / ".vite"
    pasta_manifesto.mkdir(parents=True)
    (pasta_manifesto / "manifest.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(_orcamento, "DIST", dist)
    # Isola a inspeção dos arquivos publicados do cálculo dos orçamentos.
    monkeypatch.setattr(_orcamento, "LIMITES", {})
    return dist


def test_pacote_reprova_aparelho_da_demonstracao_fora_da_rota(dist_para_inspecao, capsys):
    arquivo = dist_para_inspecao / "demo-oculta.js"
    arquivo.write_text('const nome = "Travesseiro";', encoding="utf-8")
    assert _orcamento.main() == 0

    arquivo.write_text('const nome = "Travesseiro de exemplo";', encoding="utf-8")
    assert _orcamento.main() == 1
    assert "Produção contém a demonstração de aparelhos do painel: demo-oculta.js" in capsys.readouterr().err


def test_pacote_reprova_texto_da_demonstracao_no_html_da_raiz_do_dist(dist_para_inspecao, capsys):
    arquivo = dist_para_inspecao / "landing-prototipo.html"
    arquivo.write_text("<p>Cenário da demonstração</p>", encoding="utf-8")

    assert _orcamento.main() == 1
    assert "Produção contém a demonstração da Noite: landing-prototipo.html" in capsys.readouterr().err


def test_pacote_ignora_texto_da_demonstracao_fora_do_dist(dist_para_inspecao, capsys):
    arquivo = dist_para_inspecao.parent / "landing-prototipo.html"
    arquivo.write_text("<p>Cenário da demonstração</p>", encoding="utf-8")

    assert _orcamento.main() == 0
    assert capsys.readouterr().err == ""


def test_landing_conta_iframe_e_imagens_imediatas_sem_contar_lazy(manifesto, tmp_path):
    manifesto["src/pages/Landing.tsx"] = {"file": "landing.js"}
    (tmp_path / _orcamento.PROTOTIPO).write_text(
        '<img src="/midia/landing/imediata.webp" loading="eager">'
        '<img src="/midia/landing/tardia.webp" loading="lazy">'
        '<svg>'
        '<image href="/midia/landing/svg.webp"></image>'
        '<image xlink:href="/midia/landing/svg-xlink.webp"></image>'
        '<image data-href="/midia/landing/foto.webp"></image>'
        '</svg>',
        encoding="utf-8",
    )
    assert _orcamento.arquivos_da_landing(manifesto, tmp_path) == {
        "index.html", "entrada.js", "landing.js", "compartilhado.js",
        "transitivo.js", "global.css", "landing-prototipo.html", "sw.js",
        "midia/landing/imediata.webp", "midia/landing/svg.webp", "midia/landing/svg-xlink.webp",
    }


def test_landing_reprova_se_base64_grande_voltar(manifesto, tmp_path):
    manifesto["src/pages/Landing.tsx"] = {"file": "landing.js"}
    html = f'<img src="data:image/webp;base64,{"A" * 8192}" loading="lazy">'
    (tmp_path / _orcamento.PROTOTIPO).write_text(html, encoding="utf-8")
    with pytest.raises(ValueError, match="imagem data:image acima de 4 kB"):
        _orcamento.arquivos_da_landing(manifesto, tmp_path)
