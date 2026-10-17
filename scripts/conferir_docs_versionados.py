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

── AS TRÊS VERIFICAÇÕES, E QUAL DELAS PODE REPROVAR ONDE ────────────────

Por isso este script tem três, com alcances diferentes e declarados:

  (1) ÓRFÃO NA ÁRVORE  — arquivo em `docs/` que existe, não é rastreado e não
      é ignorado. É o estado exato do `GIT-04`. Só é detectável na máquina de
      quem edita: tem valor local, e nenhum no CI.

  (2) REFERÊNCIA PENDENTE — caminho `docs/*.md` citado por arquivo RASTREADO,
      que não está rastreado nem ignorado. É a forma pela qual o `GIT-04`
      causava dano: o `ML-DATASETS-E-PLANO.md` era a fundamentação que os
      READMEs mandavam ler, e um clone não a trazia. Esta verificação **roda
      no CI e pode reprovar lá**, porque tanto a citação quanto a ausência do
      arquivo viajam no commit.

  (3) PONTEIRO PENDURADO — arquivo IGNORADO de propósito que, mesmo assim, é
      citado por arquivo rastreado, sem constar do inventário abaixo. Também
      roda e reprova no CI, pelo mesmo motivo da (2). Ver a seção seguinte.

A (2) e a (3) fecham a classe de problema; a (1) é a que avisa antes.

── SOBRE OS DOCUMENTOS DELIBERADAMENTE FORA DO GIT ──────────────────────

A distinção que as três usam é a que importa: **ignorado é decisão, não
rastreado e não ignorado é esquecimento.** Quem quiser tirar um documento do
versionamento tem de dizer isso no `.gitignore` — e aí a linha do `.gitignore`
fica no diff, onde alguém a lê.

Até 2026-10-17 o script parava aí, e a versão de 30/09 escreveu, no lugar
desta seção, que `docs/METODOLOGIA.md`, `docs/DATASET.md` e `docs/HARDWARE.md`
"são citados por arquivos rastreados, e isso é legítimo". **A frase está certa
e é insuficiente**, e o `GIT-05` mostrou por quê: ignorar é decisão sobre
*distribuição*, e não diz nada sobre o *ponteiro* que ficou no texto. Um
arquivo rastreado que manda ler um arquivo que o clone não traz deixa o leitor
na mesma situação do `GIT-04` — com uma diferença que não o favorece: no
`GIT-04` o arquivo apareceria com um `git add`, e aqui ele nunca aparece,
porque a ausência é intencional e o ponteiro não.

A (3) não proíbe o ponteiro. Ela exige que cada um esteja em
`PONTEIROS_ACEITOS`, **com motivo escrito**, e imprime o inventário inteiro a
cada execução. É um catraca: o que já existe está declarado, e o próximo
ponteiro novo reprova até alguém decidir o que ele é.

⚠️ **A (3) nasce com oito isenções, que são TODOS os casos existentes.** Isso
está dito aqui de propósito: uma verificação que estreia com a lista de
violações atuais inteira dentro da isenção **não pega nada hoje** — ela só
pega o nono. Quem a ler precisa saber disso para não a confundir com cobertura.
Reduzir a lista é trabalho de decisão, item `GIT-05`, não deste script.

── USO ──────────────────────────────────────────────────────────────────

    python scripts/conferir_docs_versionados.py
    python scripts/conferir_docs_versionados.py --apenas referencias
    python scripts/conferir_docs_versionados.py --apenas ponteiros

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

#: Para a verificação (3): a (2) só olha `docs/`, porque é a pasta de
#: fundamentação. Um ponteiro pendurado pode apontar para a raiz — foi o caso
#: do `ROADMAP.md` —, então a (3) precisa de um padrão mais largo. Exige
#: inicial maiúscula para não casar caminho de código (`src/app.md` não
#: existe, mas `web-app/README.md` sim, e esse é rastreado).
PADRAO_PONTEIRO = re.compile(
    r"\b(?:[\w.-]+/)*[A-Z][\w.-]*(?:" + "|".join(
        re.escape(e) for e in EXTENSOES) + r")\b"
)

#: Ponteiros pendurados ACEITOS: arquivo ignorado de propósito que arquivo
#: rastreado cita assim mesmo. Cada um com o motivo, porque a decisão é o
#: conteúdo do item — a lista sozinha seria só uma lista de desculpas.
#:
#: ⚠️ Esta lista nasceu em 17/10 com TODOS os oito casos existentes dentro.
#: Logo, no dia em que entrou, a (3) **não reprovava nada**. Ela é catraca
#: contra o nono caso, não cobertura dos oito. Reduzi-la é o `GIT-05`.
#:
#: Todo item é IMPRESSO a cada execução, pela mesma razão da
#: `EXEMPLOS_EM_PROSA`: isenção silenciosa é como uma verificação deixa de
#: verificar sem ninguém notar.
PONTEIROS_ACEITOS: dict[str, str] = {
    "ROADMAP.md":
        "Arquivo de trabalho; 8 arquivos rastreados o citam, inclusive "
        "frontend/src/lib/metricas.ts. É o pior caso do GIT-05 e o primeiro "
        "a decidir: ou versiona, ou os 8 param de citar.",
    "HISTORICO.md":
        "Deliberado e já justificado no corpo do trabalho: o diário declara, "
        "na seção 'O que este diário não cobre', que o HISTORICO.md não é "
        "versionado e por isso NÃO pode servir de procedência num capítulo "
        "de TCC. A citação existe para dizer isso. Ponteiro legítimo.",
    "CLAUDE.md":
        "Instruções de ferramenta, não fundamentação. Citado por "
        "web-app/device_auth.py e pelo backlog. Candidato a parar de ser "
        "citado, não a ser versionado.",
    "DOCUMENTO-TCC.md":
        "A monografia em redação. Fora do git por decisão de escopo do "
        "repositório de engenharia. Citado só pelo backlog.",
    "ROTEIRO-APRESENTACAO.md":
        "Material de apresentação, idem DOCUMENTO-TCC.md.",
    "docs/METODOLOGIA.md":
        "Material interno (decisão de 30/09). ⚠️ Mas o README.md rastreado "
        "lista METODOLOGIA, HARDWARE e DATASET na árvore de 'Estrutura' "
        "como 'fundamentação do TCC' — pelo nome, sem caminho, então a (3) "
        "não os pegaria por ali; quem clona lê o nome e não acha o arquivo.",
    "docs/HARDWARE.md":
        "Idem METODOLOGIA.md. Citado também por scripts/calculos_tcc.py, "
        "que é rastreado e roda no CI.",
    "docs/DATASET.md":
        "Idem METODOLOGIA.md.",
}

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


# =========================================================================
# (3) Ponteiro pendurado — arquivo ignorado que texto rastreado manda ler
# =========================================================================
def conferir_ponteiros(
    raiz: Path,
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Devolve (novos, aceitos), ambos como (alvo, quem_cita).

    Um alvo entra aqui quando: é citado por arquivo rastreado, NÃO está
    rastreado, e o `.gitignore` o exclui. Isto é, a ausência é decisão e o
    ponteiro ficou. Se estiver em `PONTEIROS_ACEITOS`, é aceito e impresso;
    senão, reprova.
    """
    trilha = rastreados(raiz)
    citados: dict[str, str] = {}

    for arquivo in sorted(trilha):
        if not arquivo.endswith(FONTES_DE_REFERENCIA):
            continue
        try:
            texto = (raiz / arquivo).read_text(encoding="utf-8",
                                               errors="replace")
        except OSError:
            continue
        for achado in PADRAO_PONTEIRO.findall(texto):
            if achado in trilha:
                continue
            # Só interessa o que existe no disco de quem roda OU o que o
            # .gitignore nomeia: nome solto em prosa ("LIMITACOES-TCC.md",
            # sem a pasta) não é caminho e não é ponteiro.
            citados.setdefault(achado, arquivo)

    deliberados = ignorados(raiz, sorted(citados))

    novos: list[tuple[str, str]] = []
    aceitos: list[tuple[str, str]] = []
    for alvo in sorted(deliberados):
        (aceitos if alvo in PONTEIROS_ACEITOS else novos).append(
            (alvo, citados[alvo]))
    return novos, aceitos


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apenas",
                    choices=("orfaos", "referencias", "ponteiros"),
                    help="rodar só uma das três verificações")
    args = ap.parse_args()

    raiz = raiz_do_repo()
    no_ci = bool(os.environ.get("CI"))
    falhou = False

    if args.apenas not in ("referencias", "ponteiros"):
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

    if args.apenas not in ("orfaos", "ponteiros"):
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

    if args.apenas not in ("orfaos", "referencias"):
        print("(3) arquivo ignorado de propósito que texto versionado manda "
              "ler")
        novos, aceitos = conferir_ponteiros(raiz)
        print(f"    ⓘ  {len(aceitos)} ponteiro(s) aceito(s), declarados em "
              f"PONTEIROS_ACEITOS — a (3) NÃO cobre estes:")
        for alvo, quem in aceitos:
            print(f"        {alvo}   ← ex.: {quem}")
            print(f"            motivo: {PONTEIROS_ACEITOS[alvo]}")
        if novos:
            falhou = True
            print("    ✗ PONTEIROS PENDURADOS NOVOS — ignorados de propósito, "
                  "citados assim mesmo:")
            for alvo, quem in novos:
                print(f"        {alvo}   ← citado em {quem}")
            print("      Decida o que ele é: versione, pare de citá-lo, ou "
                  "acrescente a\n"
                  "      PONTEIROS_ACEITOS **com o motivo escrito**. "
                  "Ver GIT-05 no backlog.")
        else:
            print("    ✓ nenhum ponteiro novo")

    print()
    print("REPROVADO" if falhou else "OK")
    return 1 if falhou else 0


if __name__ == "__main__":
    sys.exit(main())
