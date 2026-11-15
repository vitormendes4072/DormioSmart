import json
import sys
import zlib
from pathlib import Path

DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"
LIMITES = {"Dashboard": 260_000, "Login": 155_000}


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


def medir_rota(manifesto, pagina, dist):
    arquivos = arquivos_da_rota(manifesto, pagina)
    return (
        sum((dist / arquivo).stat().st_size for arquivo in arquivos),
        sum(tamanho_gzip(dist / arquivo) for arquivo in arquivos),
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
        ok = gzip <= limite
        print(f"{pagina}: {bruto} B, {gzip} B gzip, teto {limite} B ({'OK' if ok else 'EXCEDIDO'})")
        falhou |= not ok
    return int(falhou)


if __name__ == "__main__":
    sys.exit(main())
