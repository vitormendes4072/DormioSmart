"""Confere a DREAMT baixada, arquivo por arquivo, contra as somas oficiais (ML-13).

Fonte
-----
PhysioNet, `dreamt` v2.2.0 — acesso RESTRITO: só baixa quem tem conta e assinou o
*PhysioNet Restricted Health Data Use Agreement 1.5.0* na página do projeto
(https://physionet.org/content/dreamt/2.2.0/). O ZIP inteiro tem 20,3 GB; o
ML-13 só precisa de `data_64Hz/` (o E4 sozinho, com o rótulo P de preparação
preservado — na `data_100Hz` ele vira W) e de quatro arquivos pequenos.

Por que este script não baixa
-----------------------------
A primeira versão baixava com `urllib`, e o PhysioNet respondeu 403: o servidor
recusa o cliente HTTP do Python sem nem pedir a senha (medido em 03/11: o mesmo
pedido com `wget` recebe o 401 com o pedido de senha). O `curl` nativo do
Windows também levou 403, nos 103 arquivos. Fingir ser outro cliente seria
contornar a restrição do servidor — então o download é feito pelo que a página
do PhysioNet documenta: o `wget` (o pacote do `winget` falhou na conferência de
hash em 03/11 e não foi forçado) ou o ZIP inteiro pelo navegador, logado — que
foi o caminho usado, a ~186 KB/s. Este script só confere o resultado:

    wget -r -N -c -np -nH --cut-dirs=3 -P dados/bruto/dreamt --user USUARIO --ask-password \\
         https://physionet.org/files/dreamt/2.2.0/data_64Hz/
    wget -N -P dados/bruto/dreamt --user USUARIO --ask-password \\
         https://physionet.org/files/dreamt/2.2.0/SHA256SUMS.txt  (e Metadata.txt,
         participant_info.csv, LICENSE.txt)

    python -m ferramentas.baixar_dreamt --pasta CAMINHO_DREAMT

Com o ZIP: extrair dele só `data_64Hz/` e os arquivos pequenos para uma
pasta local fora do checkout principal, sem junction. Informar essa pasta
por `--pasta`. A raiz do ZIP tem o nome longo do projeto; no destino ficam
os caminhos relativos do `SHA256SUMS.txt`.

O manifesto completo também lista `data_100Hz/`, fora do escopo do ML-13.
A conferência exige as 103 entradas conhecidas de v2.2.0: 100 CSVs a 64 Hz
e os três metadados. Contagem igual com outro ID não substitui essa lista.

A senha é digitada no `wget` (`--ask-password`), por quem baixa. O termo de
uso proíbe redistribuir os dados; a pasta bruta e suas cópias não entram no Git.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

DESTINO = Path(__file__).resolve().parents[1] / "dados" / "bruto" / "dreamt"
PEQUENOS = ("Metadata.txt", "participant_info.csv", "LICENSE.txt")
PASTA_USADA = "data_64Hz/"
# Lista canônica do SHA256SUMS.txt de DREAMT v2.2.0: não há S041 nem S060.
CSV_ESPERADOS = frozenset(
    f"{PASTA_USADA}S{i:03d}_whole_df.csv"
    for i in range(2, 104) if i not in (41, 60)
)
ARQUIVOS_ESPERADOS = CSV_ESPERADOS | frozenset(PEQUENOS)


def _sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as fh:
        for bloco in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def _somas(caminho: Path) -> dict[str, str]:
    somas = {}
    for numero, linha in enumerate(caminho.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not linha.strip():
            continue
        partes = re.fullmatch(r"([0-9a-fA-F]{64})[ \t]+\*?(\S+)", linha.strip())
        if partes is None:
            raise ValueError(f"linha {numero} malformada")
        digest, nome = partes.groups()
        if nome in somas:
            raise ValueError(f"entrada duplicada: {nome}")
        somas[nome] = digest.lower()
    ausentes = sorted(ARQUIVOS_ESPERADOS - somas.keys())
    if ausentes:
        raise ValueError(f"faltam {len(ausentes)} das 103 entradas esperadas "
                         f"(ex.: {', '.join(ausentes[:3])})")
    return somas


def main() -> int:
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pasta", type=Path, default=DESTINO)
    args = ap.parse_args()

    lista = args.pasta / "SHA256SUMS.txt"
    if not lista.exists():
        print(f"Falta {lista}. Baixe-o com o wget (ver o topo deste arquivo).", file=sys.stderr)
        return 1
    try:
        somas = _somas(lista)
    except (OSError, ValueError, UnicodeError) as exc:
        print(f"MANIFESTO INVÁLIDO: {exc}", file=sys.stderr)
        return 1
    alvos = sorted(ARQUIVOS_ESPERADOS)
    print(f"{len(alvos)} arquivos a conferir em {args.pasta}")

    ok = faltam = diferem = 0
    for rel in alvos:
        alvo = args.pasta / rel
        if not alvo.is_file():
            faltam += 1
            print(f"  FALTA: {rel}")
        elif _sha256(alvo) != somas[rel]:
            diferem += 1
            print(f"  SOMA NÃO CONFERE: {rel} — apague e baixe de novo")
        else:
            ok += 1
    print(f"\nconferem {ok} · faltam {faltam} · diferem {diferem}")
    return 0 if ok == len(ARQUIVOS_ESPERADOS) and faltam == 0 and diferem == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
