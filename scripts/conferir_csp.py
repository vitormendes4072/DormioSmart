"""Confere a Content-Security-Policy do `vercel.json` contra o site gerado (SEC-20).

A CSP do site libera script inline só por hash (`'sha256-...'` em
`script-src`), sem `'unsafe-inline'`. Isso quebra em silêncio: quem mudar um
caractere no script do tema do `index.html` ou num dos blocos da landing faz o
navegador bloquear aquele script na produção, e nenhum teste do frontend vê.
Este script calcula o hash de cada script inline das páginas servidas e
reprova se:

- algum script inline não tiver o hash na política (o navegador o bloquearia);
- a política tiver hash que não corresponde a script nenhum (sobra: libera um
  script que não existe mais, e esconde a política real);
- `script-src` tiver `'unsafe-inline'` ou `'unsafe-eval'`;
- a rota dos cabeçalhos não for a primeira do `vercel.json` ou não tiver
  `"continue": true` (sem isso ela engole as rotas seguintes);
- faltar um dos cabeçalhos de segurança.

Lê o site **gerado** (`frontend/dist`), que é o que a Vercel serve: o
`index.html` passa pelo Vite. Rodar depois de `npm run build`.

O hash é do texto do script como o navegador o vê: o parser de HTML troca
CRLF e CR soltos por LF antes de tudo, então o resultado não depende do fim
de linha do checkout.

Uso:  python scripts/conferir_csp.py [--dist frontend/dist] [--vercel vercel.json]
"""
import argparse
import base64
import hashlib
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PAGINAS = ("index.html", "landing-prototipo.html")
CABECALHOS_EXIGIDOS = (
    "Content-Security-Policy",
    "X-Frame-Options",
    "X-Content-Type-Options",
    "Referrer-Policy",
    "Permissions-Policy",
)
TIPOS_EXECUTAVEIS = {"", "text/javascript", "application/javascript", "module"}


class ScriptsInline(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.scripts = []
        self._dentro = False
        self._texto = []

    def handle_starttag(self, tag, attrs):
        if tag != "script":
            return
        a = dict(attrs)
        if "src" in a or (a.get("type") or "").strip().lower() not in TIPOS_EXECUTAVEIS:
            return
        self._dentro, self._texto = True, []

    def handle_data(self, data):
        if self._dentro:
            self._texto.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self._dentro:
            self.scripts.append("".join(self._texto))
            self._dentro = False


def hash_csp(texto):
    texto = texto.replace("\r\n", "\n").replace("\r", "\n")
    return "sha256-" + base64.b64encode(hashlib.sha256(texto.encode("utf-8")).digest()).decode()


def scripts_da_pagina(caminho):
    leitor = ScriptsInline()
    leitor.feed(caminho.read_text(encoding="utf-8"))
    leitor.close()
    return leitor.scripts


def rota_dos_cabecalhos(config):
    rotas = config.get("routes") or []
    for i, rota in enumerate(rotas):
        if "Content-Security-Policy" in (rota.get("headers") or {}):
            return i, rota
    return None, None


def conferir(dist, vercel):
    falhas = []
    config = json.loads(vercel.read_text(encoding="utf-8"))
    i, rota = rota_dos_cabecalhos(config)
    if rota is None:
        return ["o vercel.json não tem rota com Content-Security-Policy"]
    if i != 0:
        falhas.append(f"a rota dos cabeçalhos é a {i + 1}ª; tem de ser a primeira")
    if rota.get("continue") is not True:
        falhas.append('a rota dos cabeçalhos não tem "continue": true')
    if rota.get("src") != "/(.*)":
        falhas.append(f'a rota dos cabeçalhos cobre "{rota.get("src")}", e não o site inteiro')
    cabecalhos = rota["headers"]
    for nome in CABECALHOS_EXIGIDOS:
        if not cabecalhos.get(nome):
            falhas.append(f"falta o cabeçalho {nome}")

    diretivas = {}
    for parte in cabecalhos["Content-Security-Policy"].split(";"):
        palavras = parte.split()
        if palavras:
            diretivas[palavras[0]] = palavras[1:]
    script_src = diretivas.get("script-src")
    if script_src is None:
        return falhas + ["a CSP não tem script-src"]
    for proibido in ("'unsafe-inline'", "'unsafe-eval'"):
        if proibido in script_src:
            falhas.append(f"script-src tem {proibido}")
    na_politica = {t.strip("'") for t in script_src if re.fullmatch(r"'sha256-[A-Za-z0-9+/=]+'", t)}

    nas_paginas = {}
    for nome in PAGINAS:
        caminho = dist / nome
        if not caminho.is_file():
            falhas.append(f"{caminho} não existe (rodar `npm run build` antes)")
            continue
        for n, texto in enumerate(scripts_da_pagina(caminho), 1):
            nas_paginas.setdefault(hash_csp(texto), []).append(f"{nome}, script inline {n}")

    for h, onde in sorted(nas_paginas.items()):
        if h not in na_politica:
            falhas.append(f"{', '.join(onde)}: o hash {h} não está no script-src (o navegador bloquearia)")
    for h in sorted(na_politica - set(nas_paginas)):
        falhas.append(f"o script-src libera {h}, que não é de script nenhum das páginas (sobra)")
    return falhas, len(nas_paginas)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--dist", default=str(RAIZ / "frontend" / "dist"))
    p.add_argument("--vercel", default=str(RAIZ / "vercel.json"))
    p.add_argument("--imprimir", action="store_true", help="imprime os hashes das páginas, para colar no vercel.json")
    a = p.parse_args()
    dist, vercel = Path(a.dist), Path(a.vercel)
    if a.imprimir:
        for nome in PAGINAS:
            for n, texto in enumerate(scripts_da_pagina(dist / nome), 1):
                print(f"'{hash_csp(texto)}'  # {nome}, script inline {n}")
        return 0
    resultado = conferir(dist, vercel)
    falhas, total = resultado if isinstance(resultado, tuple) else (resultado, 0)
    if falhas:
        print(f"FALHOU — {len(falhas)} problema(s) na CSP do vercel.json (SEC-20):")
        for f in falhas:
            print(f"  ✗ {f}")
        return 1
    print(f"OK — {total} scripts inline, todos com hash no script-src, sem sobra; cabeçalhos completos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
