#!/usr/bin/env python3
"""Impede que documento de fundamentação fique fora do versionamento (CI-05).

── O QUE O CI-05 PEDIA, E POR QUE ASSIM NÃO FUNCIONA ────────────────────

O backlog especificava o item como *"um job que falhe quando há arquivo não
rastreado em `docs/`"*, e estimava três linhas. As três linhas existem:

    git ls-files --others --exclude-standard -- docs/

O problema é onde elas rodariam. `actions/checkout` monta a árvore de trabalho
**a partir do commit**. Num runner não existe arquivo não rastreado em `docs/`
— não porque o repositório esteja limpo, mas porque o arquivo não rastreado
nunca sai da máquina de quem o escreveu. O comando devolve vazio SEMPRE, o job
passa SEMPRE, e o resultado é um selo verde que não verificou nada.

Isto não é hipótese sobre o GitHub: é consequência de o git enviar objetos
commitados e nada mais. A prevenção pedida, posta onde foi pedida, seria
decorativa — e o `GIT-04` aconteceu justamente porque ninguém checava.

── AS DUAS VERIFICAÇÕES, E QUAL DELAS PODE REPROVAR ONDE ────────────────

Por isso este script tem duas, com alcances diferentes e declarados:

  (1) ÓRFÃO NA ÁRVORE  — arquivo em `docs/` que existe, não é rastreado e não
      é ignorado. É o estado exato do `GIT-04`. Só é detectável na máquina de
      quem edita: tem valor local, e nenhum no CI.

  (2) REFERÊNCIA PENDENTE — caminho `docs/*.md` citado por arquivo RASTREADO,
      que não está rastreado nem ignorado. É a forma pela qual o `GIT-04`
      causava dano: o `ML-DATASETS-E-PLANO.md` era a fundamentação que os
      READMEs mandavam ler, e um clone não a trazia. Esta verificação **roda
      no CI e pode reprovar lá**, porque tanto a citação quanto a ausência do
      arquivo viajam no commit.

A (2) é a que fecha a classe de problema; a (1) é a que avisa antes.

── SOBRE OS DOCUMENTOS DELIBERADAMENTE FORA DO GIT ──────────────────────

`docs/METODOLOGIA.md`, `docs/DATASET.md`, `docs/HARDWARE.md`, `docs/fontes/` e
`docs/devlog/` estão no `.gitignore` de propósito (material interno). Eles são
citados por arquivos rastreados, e isso é legítimo.

A distinção que o script usa é a única que importa: **ignorado é decisão,
não rastreado e não ignorado é esquecimento.** Quem quiser tirar um documento
do versionamento tem de dizer isso no `.gitignore` — e aí a linha do
`.gitignore` fica no diff, onde alguém a lê.

── USO ──────────────────────────────────────────────────────────────────

    python scripts/conferir_docs_versionados.py
    python scripts/conferir_docs_versionados.py --apenas referencias

Saída 0 se passou, 1 se achou problema, 2 se o ambiente não permite verificar.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

#: Diretório cujos documentos precisam estar versionados ou explicitamente
#: ignorados. Uma pasta só — ampliar isto sem medir é como se ganha um job
#: que ninguém entende por que ficou vermelho.
PASTA = "docs"

#: Extensões que contam como documento. Diagrama `.mermaid` entra: ele também
#: é fundamentação, e também se perde num clone.
EXTENSOES = (".md", ".mermaid", ".svg")

#: Caminhos citados em prosa. Casa `docs/FOO.md` e `docs/sub/FOO.md`, com ou
#: sem cerca de crase, e para de casar na primeira pontuação que não pode
#: fazer parte de um nome de arquivo.
PADRAO_REFERENCIA = re.compile(
    r"\b" + PASTA + r"/(?:[\w.-]+/)*[\w.-]+(?:" + "|".join(
        re.escape(e) for e in EXTENSOES) + r")\b"
)

#: Nomes que aparecem em prosa como EXEMPLO, nunca como citação de documento
#: real. Achado na primeira execução do script (16/10): ele se acusava a si
#: mesmo. `docs/FOO.md` e `docs/sub/FOO.md` estão no comentário do próprio
#: `PADRAO_REFERENCIA`, para explicar o que o regex casa; `ORFAO-DE-TESTE.md`
#: está no `BACKLOG-COMPLETO.md`, dentro do procedimento de validação **deste
#: script** (`touch docs/ORFAO-DE-TESTE.md` e confirme que a (1) acusa).
#:
#: A isenção vale **só para a verificação (2)**, e por um motivo que não é de
#: conveniência: a (2) pergunta "um clone traz o que o texto manda ler?", e
#: texto que documenta um placeholder não manda ler nada. A (1) pergunta outra
#: coisa — "existe arquivo no disco fora do git?" — e ali o nome não tem
#: isenção nenhuma: se `docs/ORFAO-DE-TESTE.md` existir sem estar versionado,
#: tem de ser acusado, porque é exatamente o que o procedimento de validação
#: manda provocar. Isentar nas duas tornaria o procedimento incapaz de falhar.
#:
#: Comparado pelo nome do arquivo, para que `docs/sub/FOO.md` também entre.
#: Toda isenção aplicada é IMPRESSA na saída — isenção silenciosa é como uma
#: verificação deixa de verificar sem ninguém notar.
EXEMPLOS_EM_PROSA = frozenset({"FOO.md", "ORFAO-DE-TESTE.md"})

#: Extensões de arquivo rastreado onde se procura referência. Binário não
#: entra; `.py`, `.ts` e `.yml` entram porque comentário também manda ler doc.
FONTES_DE_REFERENCIA = (
    ".md", ".mermaid", ".py", ".ts", ".tsx", ".js", ".jsx",
    ".yml", ".yaml", ".sh", ".ino", ".h", ".cpp", ".sql", ".txt", ".json",
)


def git(*args: str, raiz: Path) -> str:
    """Roda git em modo leitura, sem tocar no `index.lock`."""
    ambiente = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
    r = subprocess.run(
        ("git", *args), cwd=raiz, env=ambiente,
        capture_output=True, text=True,
    )
    if r.returncode != 0 and not r.stdout:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


def raiz_do_repo() -> Path:
    r = subprocess.run(
        ("git", "rev-parse", "--show-toplevel"),
        capture_output=True, text=True,
        cwd=Path(__file__).resolve().parent,
    )
    if r.returncode != 0:
        print("ERRO: não estou dentro de um repositório git.", file=sys.stderr)
        sys.exit(2)
    return Path(r.stdout.strip())


def rastreados(raiz: Path) -> set[str]:
    return {l for l in git("ls-files", raiz=raiz).splitlines() if l}


def ignorados(raiz: Path, caminhos: list[str]) -> set[str]:
    """Quais dos caminhos dados o `.gitignore` exclui de propósito.

    `check-ignore --no-index` responde pela regra, e não pelo estado do
    índice: um arquivo que casa uma regra de ignore continua respondendo
    "ignorado" mesmo que alguém já o tenha commitado com `git add -f`.
    """
    if not caminhos:
        return set()
    ambiente = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
    r = subprocess.run(
        ("git", "check-ignore", "--no-index", "--stdin"),
        cwd=raiz, env=ambiente, input="\n".join(caminhos),
        capture_output=True, text=True,
    )
    return {l for l in r.stdout.splitlines() if l}


# =========================================================================
# (1) Órfão na árvore de trabalho — só detectável localmente
# =========================================================================
def conferir_orfaos(raiz: Path) -> list[str]:
    saida = git("ls-files", "--others", "--exclude-standard", "--", PASTA,
                raiz=raiz)
    return sorted(
        l for l in saida.splitlines()
        if l and l.endswith(EXTENSOES)
    )


# =========================================================================
# (2) Referência pendente — roda e reprova no CI
# =========================================================================
def conferir_referencias(
    raiz: Path,
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Devolve (pendentes, isentas_por_exemplo).

    A segunda lista existe para ser impressa: a isenção de `EXEMPLOS_EM_PROSA`
    é estreita, mas tem de ficar visível a cada execução.
    """
    trilha = rastreados(raiz)
    citadas: dict[str, str] = {}

    for arquivo in sorted(trilha):
        if not arquivo.endswith(FONTES_DE_REFERENCIA):
            continue
        caminho = raiz / arquivo
        try:
            texto = caminho.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for achado in PADRAO_REFERENCIA.findall(texto):
            citadas.setdefault(achado, arquivo)

    faltando = [c for c in citadas if c not in trilha]
    deliberadas = ignorados(raiz, faltando)

    pendentes: list[tuple[str, str]] = []
    isentas: list[tuple[str, str]] = []
    for c in faltando:
        if c in deliberadas:
            continue
        if Path(c).name in EXEMPLOS_EM_PROSA:
            isentas.append((c, citadas[c]))
        else:
            pendentes.append((c, citadas[c]))
    return sorted(pendentes), sorted(isentas)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apenas", choices=("orfaos", "referencias"),
                    help="rodar só uma das duas verificações")
    args = ap.parse_args()

    raiz = raiz_do_repo()
    no_ci = bool(os.environ.get("CI"))
    falhou = False

    if args.apenas != "referencias":
        print("(1) documento em docs/ fora do git e fora do .gitignore")
        if no_ci:
            print("    ⓘ  rodando no CI: esta verificação NÃO pode reprovar "
                  "aqui.\n"
                  "       A árvore vem do commit, então arquivo não "
                  "rastreado não existe.\n"
                  "       Quem fecha a classe de problema é a (2). Ver o "
                  "cabeçalho deste script.")
        orfaos = conferir_orfaos(raiz)
        if orfaos:
            falhou = True
            print("    ✗ ÓRFÃOS — existem no disco e não estão no git:")
            for o in orfaos:
                print(f"        {o}")
            print("      Versione (`git add`) ou declare a exclusão no "
                  ".gitignore.\n"
                  "      Foi assim que BACKLOG-COMPLETO.md, "
                  "ML-DATASETS-E-PLANO.md e\n"
                  "      SINTESE-PESQUISA-E-CAMINHOS.md passaram semanas fora "
                  "do repositório (GIT-04).")
        else:
            print("    ✓ nenhum")

    if args.apenas != "orfaos":
        print("(2) documento citado por arquivo versionado que não está no git")
        pendentes, isentas = conferir_referencias(raiz)
        for alvo, quem in isentas:
            print(f"    ⓘ  isento (exemplo em prosa): {alvo}   "
                  f"← em {quem}")
        if pendentes:
            falhou = True
            print("    ✗ REFERÊNCIAS PENDENTES — um clone não traz estes "
                  "arquivos:")
            for alvo, quem in pendentes:
                print(f"        {alvo}   ← citado em {quem}")
            print("      Versione o arquivo, corrija a citação, ou declare a "
                  "exclusão no .gitignore.")
        else:
            print("    ✓ nenhuma")

    print()
    print("REPROVADO" if falhou else "OK")
    return 1 if falhou else 0


if __name__ == "__main__":
    sys.exit(main())
