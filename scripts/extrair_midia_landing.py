"""Extrai os WebP do HTML do protótipo integrado em b25e03e.

Execute depois de copiar uma nova exportação para frontend/public:
    python scripts/extrair_midia_landing.py
Revise os atributos de carregamento tardio e os hashes CSP da nova exportação.
"""
import argparse
import base64
import hashlib
import re
from pathlib import Path

HTML = Path(__file__).resolve().parents[1] / "frontend" / "public" / "landing-prototipo.html"
WEBP_INLINE = re.compile(rb"data:image/webp;base64,([A-Za-z0-9+/=]+)")


def extrair(caminho):
    original = caminho.read_bytes()

    def salvar(match):
        imagem = base64.b64decode(match[1], validate=True)
        nome = hashlib.sha256(imagem).hexdigest() + ".webp"
        relativo = Path("midia", "landing", nome)
        destino = caminho.parent / relativo
        destino.parent.mkdir(parents=True, exist_ok=True)
        if not destino.exists() or destino.read_bytes() != imagem:
            destino.write_bytes(imagem)
        return ("/" + relativo.as_posix()).encode("ascii")

    html = WEBP_INLINE.sub(salvar, original)
    if html != original:
        caminho.write_bytes(html)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html", type=Path, default=HTML, nargs="?")
    extrair(parser.parse_args().html)
