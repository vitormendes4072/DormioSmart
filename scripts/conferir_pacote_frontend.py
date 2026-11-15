import json
import sys
import zlib
from pathlib import Path

DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"
LIMITES = {"Dashboard": 260_000, "Login": 155_000}


def arquivos_da_rota(manifesto, pagina):
    arquivos = {"index.html"}
    visitados = set()
    fila = [f"src/pages/{pagina}.tsx", *(chave for chave, item in manifesto.items() if item.get("isEntry"))]
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


def main():
    manifesto = json.loads((DIST / ".vite" / "manifest.json").read_text(encoding="utf-8"))
    falhou = False
    for pagina, limite in LIMITES.items():
        arquivos = arquivos_da_rota(manifesto, pagina)
        bruto = sum((DIST / arquivo).stat().st_size for arquivo in arquivos)
        gzip = sum(tamanho_gzip(DIST / arquivo) for arquivo in arquivos)
        ok = gzip <= limite
        print(f"{pagina}: {bruto} B, {gzip} B gzip, teto {limite} B ({'OK' if ok else 'EXCEDIDO'})")
        falhou |= not ok
    return int(falhou)


if __name__ == "__main__":
    sys.exit(main())
