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

    python -m ferramentas.baixar_dreamt

Com o ZIP: extrair dele só `data_64Hz/` e os arquivos pequenos para
`ml/dados/bruto/dreamt/` (a raiz do ZIP é uma pasta com o nome longo do
projeto; o que fica em `dreamt/` são os caminhos do `SHA256SUMS.txt`).

A senha é digitada no `wget` (`--ask-password`), por quem baixa. Os arquivos
ficam em `ml/dados/bruto/dreamt/`, que o git ignora: o termo de uso proíbe
redistribuir o dado, e nada daqui pode entrar no repositório.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

DESTINO = Path(__file__).resolve().parents[1] / "dados" / "bruto" / "dreamt"
PEQUENOS = ("Metadata.txt", "participant_info.csv", "LICENSE.txt")
PASTA_USADA = "data_64Hz/"


def _sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as fh:
        for bloco in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def _somas(caminho: Path) -> dict[str, str]:
    somas = {}
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        partes = linha.split()
        if len(partes) >= 2:
            somas[partes[1].lstrip("*")] = partes[0].lower()
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
    somas = _somas(lista)
    alvos = sorted(p for p in somas if p.startswith(PASTA_USADA)) + [p for p in PEQUENOS if p in somas]
    print(f"{len(alvos)} arquivos a conferir em {args.pasta}")

    ok = faltam = diferem = 0
    for rel in alvos:
        alvo = args.pasta / rel
        if not alvo.exists():
            faltam += 1
            print(f"  FALTA: {rel}")
        elif _sha256(alvo) != somas[rel]:
            diferem += 1
            print(f"  SOMA NÃO CONFERE: {rel} — apague e baixe de novo")
        else:
            ok += 1
    print(f"\nconferem {ok} · faltam {faltam} · diferem {diferem}")
    return 0 if faltam == 0 and diferem == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
