import json
import re
import sys
import zlib
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit

DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"
LIMITES = {"Dashboard": 260_000, "Login": 155_000, "Landing": 289_800}
PROTOTIPO = "landing-prototipo.html"
IMAGEM_INLINE_GRANDE = re.compile(r"data:image/[^\s\"'<>]{4096,}", re.IGNORECASE)
TEXTO_DA_DEMO_DA_NOITE = "Cenário da demonstração".encode("utf-8")


def arquivos_da_rota(manifesto, pagina):
    chave_da_pagina = f"src/pages/{pagina}.tsx"
    if chave_da_pagina not in manifesto:
        raise ValueError(
            f"{pagina}: página ausente do manifesto do Vite ({chave_da_pagina}). "
            "Confira se a página tem um chunk próprio, carregado sob demanda."
        )
    arquivos = {"index.html"}
    visitados = set()
    fila = [chave_da_pagina, *(chave for chave, item in manifesto.items() if item.get("isEntry"))]
    while fila:
        chave = fila.pop()
        if chave in visitados:
            continue
        visitados.add(chave)
        item = manifesto[chave]
        arquivos.add(item["file"])
        arquivos.update(item.get("css", ()))
        fila.extend(item.get("imports", ()))
    return arquivos


def tamanho_gzip(caminho):
    compressor = zlib.compressobj(level=6, wbits=31)
    return len(compressor.compress(caminho.read_bytes()) + compressor.flush())


class ImagensIniciais(HTMLParser):
    def __init__(self):
        super().__init__()
        self.arquivos = set()

    def handle_starttag(self, tag, attrs):
        atributos = dict(attrs)
        if tag == "img" and atributos.get("loading") != "lazy":
            url = atributos.get("src")
        elif tag == "image":
            url = atributos.get("href") or atributos.get("xlink:href")
        else:
            return
        if url:
            partes = urlsplit(url)
            if not partes.scheme and not partes.netloc:
                self.arquivos.add(partes.path.lstrip("/"))


def arquivos_da_landing(manifesto, dist):
    arquivos = arquivos_da_rota(manifesto, "Landing")
    html = (dist / PROTOTIPO).read_text(encoding="utf-8")
    if IMAGEM_INLINE_GRANDE.search(html):
        raise ValueError(
            f"{PROTOTIPO}: imagem data:image acima de 4 kB. "
            "Execute scripts/extrair_midia_landing.py antes do build."
        )
    imagens = ImagensIniciais()
    imagens.feed(html)
    imagens.close()
    return arquivos | {PROTOTIPO, "sw.js"} | imagens.arquivos


def medir_rota(manifesto, pagina, dist):
    arquivos = arquivos_da_landing(manifesto, dist) if pagina == "Landing" else arquivos_da_rota(manifesto, pagina)
    return (
        sum((dist / arquivo).stat().st_size for arquivo in arquivos),
        sum(
            (dist / arquivo).stat().st_size if Path(arquivo).suffix == ".webp" else tamanho_gzip(dist / arquivo)
            for arquivo in arquivos
        ),
    )


def main():
    manifesto = json.loads((DIST / ".vite" / "manifest.json").read_text(encoding="utf-8"))
    falhou = False
    for pagina, limite in LIMITES.items():
        try:
            bruto, gzip = medir_rota(manifesto, pagina, DIST)
        except ValueError as erro:
            print(erro, file=sys.stderr)
            falhou = True
            continue
        unidade = "B transferidos estimados" if pagina == "Landing" else "B gzip"
        ok = gzip <= limite
        print(f"{pagina}: {bruto} B, {gzip} {unidade}, teto {limite} B ({'OK' if ok else 'EXCEDIDO'})")
        falhou |= not ok
    # A guarda da rota pode bloquear a demo mesmo quando seu chunk foi empacotado.
    # Examine também os assets que a página de produção nunca carrega.
    assets_com_demo = [
        arquivo.relative_to(DIST).as_posix()
        for arquivo in sorted((DIST / "assets").rglob("*"))
        if arquivo.is_file() and TEXTO_DA_DEMO_DA_NOITE in arquivo.read_bytes()
    ]
    if assets_com_demo:
        print(f"Produção contém a demonstração da Noite: {', '.join(assets_com_demo)}", file=sys.stderr)
    else:
        print("Produção sem texto exclusivo da demonstração da Noite (OK)")
    return int(falhou or bool(assets_com_demo))


if __name__ == "__main__":
    sys.exit(main())
