#!/usr/bin/env python3
"""Confere o resumo do topo do backlog contra as linhas dele (DOC-13).

── POR QUE EXISTE ────────────────────────────────────────────────────────

O backlog tem um resumo no topo (a contagem, o quadro em uma tela e o caminho
crítico) que é escrito à mão e envelhece sem que nada acuse. Em 29/10 o topo
mandava rodar o `DATA-03`, fechado na véspera, e o quadro listava seis itens
fechados como pendentes (§6 das lições, ocorrência 8); em 03/11, depois da
triagem, o quadro voltou a listar itens fechados e foi corrigido à mão duas
vezes. Fechar um item mexe na linha dele; este script confere que o resumo
acompanhou.

── O QUE CONFERE, E O QUE NÃO ────────────────────────────────────────────

1. **A contagem**: reconta, linha a linha, os itens abertos de cada camada
   (seções `# L3`, `# L0`, `# L1`, `# L2`) e compara com a linha
   `**Contagem:** N itens abertos · L0 … L3 …`.
2. **O quadro em uma tela**: os IDs listados em cada camada têm de ser
   EXATAMENTE os abertos daquela camada — nem fechado a mais, nem aberto a
   menos. Entende `CALC-01..04`, `HW-04/06` e `ARQ-01(c)`; ignora o que vem
   depois de `←` (comentário).
3. **O caminho crítico**: nos passos numerados e na linha "Em paralelo",
   nenhum item fechado ou pós-banca pode aparecer, a não ser riscado
   (`~~…~~`). Notas datadas (`✏️`) são histórico e ficam de fora.

**Não confere** a seção "Estado do projeto": é prosa com histórico, e a
regra literal ("item fechado citado") acusaria 161 menções legítimas em
03/11 — alarme que vive tocando ensina a ignorar o alarme. Ela diz isso no
próprio topo.

    python scripts/conferir_backlog.py --conferir
    python scripts/conferir_backlog.py            (só relata)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

BACKLOG = Path(__file__).resolve().parent.parent / "docs" / "BACKLOG-COMPLETO.md"
CAMADAS = ("L0", "L1", "L2", "L3")
ID = re.compile(r"\*\*([A-Z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)+)\*\*")
ID_SOLTO = re.compile(r"\b([A-Z][A-Z0-9]*-[A-Za-z0-9]+)(?:\.\.(\d+)|/(\d+))?")


def _linhas(texto: str) -> list[str]:
    return texto.replace("\r\n", "\n").split("\n")


def _achar(linhas, prefixo):
    for i, l in enumerate(linhas):
        if l.startswith(prefixo):
            return i
    raise SystemExit(f"backlog sem a seção {prefixo!r}")


def itens(linhas):
    """{camada: [IDs abertos]}, e {ID: 'aberto' | 'fechado' | 'pos-banca'}."""
    secoes = sorted([(_achar(linhas, "# L3"), "L3"), (_achar(linhas, "# L0"), "L0"),
                     (_achar(linhas, "# L1"), "L1"), (_achar(linhas, "# L2"), "L2"),
                     (_achar(linhas, "## O caminho crítico"), None)])
    abertos = {c: [] for c in CAMADAS}
    estado = {}
    for (ini, camada), (fim, _) in zip(secoes, secoes[1:]):
        for i in range(ini, fim):
            l = linhas[i]
            if not l.startswith("| ") or l.startswith("| Item") or l.startswith("|---"):
                continue
            celulas = l[2:].split(" | ")
            c1, c2 = celulas[0], (celulas[1] if len(celulas) > 1 else "")
            if "(→" in c1:
                continue
            m = ID.match(c1.lstrip("~"))
            ident = m.group(1) if m else ("Etapa-0" if "Etapa 0" in c1 else f"(sem ID, linha {i + 1})")
            parcial = "🟠" in c1 or "parcial" in c1
            if any(x in c1 for x in ("✅", "⛔")) or (not parcial and any(
                    c2.startswith(x) or c2.startswith("**" + x) for x in ("✅", "⛔"))):
                estado[ident] = "fechado"
                continue
            estado[ident] = "aberto"
            abertos["L3" if re.search(r"\*\*L3\b", c1) else camada].append(ident)
    pos = next((i for i, l in enumerate(linhas) if l.startswith("# Pós-banca")), None)
    if pos is not None:
        for l in linhas[pos:]:
            m = ID.match(l[2:]) if l.startswith("| ") else None
            if m:
                estado[m.group(1)] = "pos-banca"
    return abertos, estado


def _expandir(prefixo_e_num: str, ate: str | None, barra: str | None) -> list[str]:
    if not (ate or barra):
        return [prefixo_e_num]
    base, num = prefixo_e_num.rsplit("-", 1)
    if not num.isdigit():
        return [prefixo_e_num]
    largura = len(num)
    if ate:
        return [f"{base}-{n:0{largura}d}" for n in range(int(num), int(ate) + 1)]
    return [prefixo_e_num, f"{base}-{int(barra):0{largura}d}"]


def ids_do_texto(texto: str) -> list[str]:
    achados = []
    for m in ID_SOLTO.finditer(texto):
        achados.extend(_expandir(m.group(1), m.group(2), m.group(3)))
    return achados


def quadro(linhas):
    """{camada: set(IDs)} lido do quadro em uma tela."""
    ini = _achar(linhas, "## O quadro em uma tela")
    fim = _achar(linhas, "## Concluído desde")
    cabecalhos = {"L3  VOCÊ": "L3", "L1  BANCADA": "L1", "L2  DADO REAL": "L2",
                  "L0  EM PARALELO": "L0", "L3  TAMBÉM DEPENDE": "L3"}
    vistos = {c: set() for c in CAMADAS}
    camada = None
    for l in linhas[ini:fim]:
        if "✏️" in l or "⛓" in l or "✅ FECHADO" in l:
            camada = None
            continue
        for chave, c in cabecalhos.items():
            if chave in l:
                camada = c
        if not l.strip():
            camada = None
            continue
        if camada is None:
            continue
        corpo = l.split("←")[0]
        if "Etapa 0" in corpo:
            vistos[camada].add("Etapa-0")
        for chave in cabecalhos:
            corpo = corpo.replace(chave, "")
        vistos[camada].update(ids_do_texto(corpo))
    return vistos


def caminho_critico(linhas, estado):
    """[(linha, ID, estado)] de item fechado ou pós-banca citado sem riscar."""
    ini = _achar(linhas, "## O caminho crítico")
    acusados, em_nota = [], False
    for i in range(ini + 1, len(linhas)):
        l = linhas[i]
        if l.startswith(">") or l.startswith("## "):
            break
        if re.match(r"^\d+\. ", l) or l.startswith("**Em paralelo"):
            em_nota = False
        if em_nota:
            continue
        corpo = re.sub(r"~~.*?~~", "", l)
        if "✏️" in corpo:
            corpo, em_nota = corpo.split("✏️")[0], True
        for ident in ids_do_texto(corpo):
            if estado.get(ident) in ("fechado", "pos-banca"):
                acusados.append((i + 1, ident, estado[ident]))
    return acusados


def conferir(texto: str) -> list[str]:
    linhas = _linhas(texto)
    abertos, estado = itens(linhas)
    problemas = []

    m = re.search(r"^\*\*Contagem:\*\* (\d+) itens abertos · \*\*L0: (\d+)\*\* · L1: (\d+) · "
                  r"L2: (\d+) · L3: (\d+)\.", texto.replace("\r\n", "\n"), re.M)
    if not m:
        problemas.append("linha **Contagem:** não encontrada no formato esperado")
    else:
        declarado = dict(zip(("total",) + CAMADAS, map(int, m.groups())))
        medido = {c: len(abertos[c]) for c in CAMADAS}
        medido["total"] = sum(medido.values())
        for k in ("total",) + CAMADAS:
            if declarado[k] != medido[k]:
                problemas.append(f"contagem: {k} declarado {declarado[k]}, recontado {medido[k]}")

    vistos = quadro(linhas)
    for c in CAMADAS:
        esperado = set(abertos[c])
        a_mais = sorted(vistos[c] - esperado)
        a_menos = sorted(esperado - vistos[c])
        for ident in a_mais:
            onde = estado.get(ident, "não existe no backlog")
            problemas.append(f"quadro, {c}: {ident} está no quadro e não é aberto de {c} ({onde})")
        for ident in a_menos:
            problemas.append(f"quadro, {c}: {ident} é aberto de {c} e falta no quadro")

    for linha, ident, st in caminho_critico(linhas, estado):
        problemas.append(f"caminho crítico, linha {linha}: {ident} está {st} e aparece sem riscar")
    return problemas


def main() -> int:
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--conferir", action="store_true", help="reprova se houver divergência")
    ap.add_argument("--arquivo", type=Path, default=BACKLOG)
    args = ap.parse_args()

    problemas = conferir(args.arquivo.read_text(encoding="utf-8"))
    for p in problemas:
        print(f"  ✗ {p}")
    if problemas:
        print(f"{'FALHOU' if args.conferir else 'DIVERGE'} — {len(problemas)} divergência(s) entre o "
              "resumo do backlog e as linhas dele (DOC-13).", file=sys.stderr)
        return 1 if args.conferir else 0
    print("OK — contagem, quadro e caminho crítico batem com as linhas do backlog.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
