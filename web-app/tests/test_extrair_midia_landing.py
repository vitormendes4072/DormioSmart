import base64
import hashlib
import importlib.util
from pathlib import Path


_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "extrair_midia_landing.py"
_spec = importlib.util.spec_from_file_location("extrair_midia_landing", _SCRIPT)
_extrator = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_extrator)


def test_extrai_um_arquivo_por_conteudo_e_pode_rodar_duas_vezes(tmp_path):
    imagem = b"RIFF-webp-sintetico"
    inline = b"data:image/webp;base64," + base64.b64encode(imagem)
    html = tmp_path / "landing-prototipo.html"
    html.write_bytes(b'<img src="' + inline + b'">\r\n<image href="' + inline + b'">')
    nome = hashlib.sha256(imagem).hexdigest() + ".webp"
    url = b"/midia/landing/" + nome.encode()

    _extrator.extrair(html)
    primeira = html.read_bytes()
    assert primeira.count(url) == 2
    assert inline not in primeira
    assert b"\r\n" in primeira
    assert (tmp_path / "midia" / "landing" / nome).read_bytes() == imagem

    _extrator.extrair(html)
    assert html.read_bytes() == primeira
    assert [p.name for p in (tmp_path / "midia" / "landing").iterdir()] == [nome]
