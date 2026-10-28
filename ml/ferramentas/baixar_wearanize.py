#!/usr/bin/env python3
"""Baixa a coleção ABERTA Wearanize+ OA do Radboud Data Repository.

    python -m ferramentas.baixar_wearanize --n-sujeitos 10

=============================================================================
POR QUE WebDAV E NÃO O PORTAL
=============================================================================
A coleção é **Open access** (`filesOpenAccess: true`, licença CC-BY-4.0), mas o
endpoint de download do portal — `/api/collectionfiles/.../files/download` —
**não responde sem sessão iniciada**. Testado em 2026-09-14: pendura até o
timeout.

O que funciona anônimo é o **WebDAV**, que é inclusive o caminho que a
documentação do RDR recomenda para volume (com *Anonymous Login* no Cyberduck).
Verificado ponta a ponta, sem cadastro, sem cookie:

    100 x channels.tsv .............. HTTP 200 (100/100, zero falhas)
    participants.tsv ................ HTTP 200
    PROPFIND de diretório ........... HTTP 207
    EDF de 480 MB, `Range: bytes=0-24575` ... HTTP 206 Partial Content

O 206 é o que importa aqui: **o servidor aceita requisição de faixa**, então
download interrompido retoma de onde parou em vez de recomeçar. Para ~45 GB
isso não é conforto, é viabilidade.

=============================================================================
QUANTO ISSO BAIXA
=============================================================================
Medido em 20 sujeitos: EDF de **486 MB em média** (mín. 285, máx. 553).

    --n-sujeitos 10     ~5 GB    piloto — suficiente para o ML-02
    --n-sujeitos 20    ~10 GB
    --n-sujeitos 92    ~45 GB    o N do experimento pulso -> cabeça (ML-03)
    --n-sujeitos 100   ~49 GB    o PlugNPlay inteiro

=============================================================================
CONDIÇÕES DE USO — não são burocracia
=============================================================================
CC-BY-4.0 **mais** duas condições declaradas pelos autores, que valem também
para a coleção aberta:

  "both the Wearanize+ and Wearanize+ OA datasets may only be used for
   scientific research purposes. By using either dataset, you agree that you
   will not attempt to identify any participant."

E citação obrigatória de DUAS coisas, mesmo usando só a OA:
  - o artigo:  doi:10.1093/sleepadvances/zpaf094
  - o dataset primário: doi:10.34973/j6jf-9e62   <- sim, o primário, não a OA

`dados/` é gitignored. Isso não é higiene de repositório: é condição de uso.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

# O relatório usa símbolos (✓, –, →): no Windows o console cai para cp1252 por
# padrão e quebra no primeiro caractere fora dessa tabela.
for _fluxo in (sys.stdout, sys.stderr):
    if hasattr(_fluxo, "reconfigure"):
        _fluxo.reconfigure(encoding="utf-8")

BASE = "https://webdav.data.ru.nl/dcmn/DSC_wrnzpoa_t0000925a_195_v1"
SUBPASTA = "Wearanize+_OA_PlugNPlay_v1.1"

DESTINO_PADRAO = Path(__file__).resolve().parents[1] / "dados" / "bruto" / "wearanize"

#: Arquivos de documentação e metadados da coleção — leves, sempre baixados.
#: O LICENSE.txt não é opcional: é o texto das condições de uso.
ARQUIVOS_RAIZ = ("ABOUT.txt", "LICENSE.txt", "README.txt", "MANIFEST.txt")
ARQUIVOS_PNP = (
    "participants.tsv",
    "participants.json",
    "dataset_description.json",
    "README.txt",
)

#: Por sujeito. O `.edf` é o dado; os três sidecars BIDS são metadados leves e
#: o `channels.tsv` é o que permite auditar canais sem abrir 500 MB.
PADRAO_SUJEITO = (
    "{s}/eeg/{s}_task-sleep_eeg.edf",
    "{s}/eeg/{s}_task-sleep_channels.tsv",
    "{s}/eeg/{s}_task-sleep_channels.json",
    "{s}/eeg/{s}_task-sleep_eeg.json",
)

TEMPO_LIMITE_S = 120
TENTATIVAS = 5
BLOCO = 1 << 20  # 1 MiB


def _url(caminho_relativo: str) -> str:
    return f"{BASE}/{quote(caminho_relativo)}"


def _tamanho_remoto(caminho_relativo: str) -> int | None:
    """Tamanho total do arquivo remoto. `None` só se o arquivo não existir (404).

    ⚠️ Não usa HEAD. Este servidor (nginx/WebDAV do RDR) responde HTTP 200 a um
    HEAD mas **sem cabeçalho `Content-Length`** — confirmado em `ABOUT.txt`,
    `LICENSE.txt`, `README.txt`, `MANIFEST.txt` e nos sidecars por sujeito.
    Usar HEAD e tratar a ausência de `Content-Length` como "arquivo não existe"
    (o que este código fazia antes) é o bug: ele derrubava a checagem de
    metadados inteira, chamando de "ausente no servidor" oito arquivos que
    respondem 200.

    Um GET com `Range: bytes=0-0` resolve: o servidor responde 206 com
    `Content-Range: bytes 0-0/<total>`, que dá o tamanho sem baixar o arquivo
    inteiro — confirmado com `curl` nos mesmos arquivos.
    """
    req = urllib.request.Request(_url(caminho_relativo), headers={"Range": "bytes=0-0"})
    try:
        with urllib.request.urlopen(req, timeout=TEMPO_LIMITE_S) as r:
            cr = r.headers.get("Content-Range")
            if cr and "/" in cr:
                total = cr.rsplit("/", 1)[-1]
                if total.isdigit():
                    return int(total)
            n = r.headers.get("Content-Length")
            return int(n) if n is not None else None
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


@dataclass
class Resultado:
    caminho: Path
    bytes_baixados: int
    ja_completo: bool
    retomado: bool


def baixar(
    caminho_relativo: str,
    destino: Path,
    forcar: bool = False,
    silencioso: bool = False,
) -> Resultado:
    """Baixa um arquivo, **retomando** se já houver um parcial em disco.

    A retomada usa `Range: bytes=N-` e exige HTTP 206 na resposta. Se o servidor
    responder 200 (ignorou a faixa), o arquivo é reescrito do zero em vez de
    concatenado — concatenar sobre um 200 corromperia silenciosamente, que é
    exatamente o tipo de erro que só aparece três semanas depois.
    """
    destino.parent.mkdir(parents=True, exist_ok=True)
    esperado = _tamanho_remoto(caminho_relativo)
    if esperado is None:
        raise FileNotFoundError(f"não existe no servidor: {caminho_relativo}")

    if destino.exists() and not forcar:
        atual = destino.stat().st_size
        if atual == esperado:
            return Resultado(destino, 0, ja_completo=True, retomado=False)
        if atual > esperado:
            if not silencioso:
                print(f"  ! {destino.name}: maior que o remoto, refazendo", file=sys.stderr)
            destino.unlink()

    inicio = destino.stat().st_size if destino.exists() and not forcar else 0
    retomado = inicio > 0
    if forcar and destino.exists():
        destino.unlink()
        inicio = 0

    for tentativa in range(1, TENTATIVAS + 1):
        try:
            req = urllib.request.Request(_url(caminho_relativo))
            if inicio:
                req.add_header("Range", f"bytes={inicio}-")
            with urllib.request.urlopen(req, timeout=TEMPO_LIMITE_S) as r:
                if inicio and r.status != 206:
                    # Servidor ignorou a faixa. Recomeçar é a única opção segura.
                    inicio, retomado = 0, False
                    destino.unlink(missing_ok=True)
                modo = "ab" if inicio else "wb"
                baixados = inicio
                t0 = time.monotonic()
                with open(destino, modo) as fh:
                    while True:
                        pedaco = r.read(BLOCO)
                        if not pedaco:
                            break
                        fh.write(pedaco)
                        baixados += len(pedaco)
                        if not silencioso and esperado:
                            pct = 100.0 * baixados / esperado
                            mbs = (baixados - inicio) / 1e6 / max(time.monotonic() - t0, 1e-9)
                            print(
                                f"\r  {destino.name}: {pct:5.1f}% "
                                f"({baixados/1e6:.0f}/{esperado/1e6:.0f} MB, {mbs:.1f} MB/s)",
                                end="",
                                file=sys.stderr,
                            )
            if not silencioso and esperado and esperado > 10 * BLOCO:
                print(file=sys.stderr)
            final = destino.stat().st_size
            if final != esperado:
                raise OSError(f"tamanho final {final} != esperado {esperado}")
            return Resultado(destino, final - inicio, ja_completo=False, retomado=retomado)

        except (urllib.error.URLError, OSError, TimeoutError) as e:
            if tentativa == TENTATIVAS:
                raise
            espera = 2 ** tentativa
            print(
                f"\n  ! {destino.name}: {type(e).__name__}: {e} — "
                f"tentativa {tentativa}/{TENTATIVAS}, reesperando {espera}s",
                file=sys.stderr,
            )
            time.sleep(espera)
            inicio = destino.stat().st_size if destino.exists() else 0
            retomado = inicio > 0

    raise RuntimeError("inalcançável")


def _sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as fh:
        for bloco in iter(lambda: fh.read(1 << 22), b""):
            h.update(bloco)
    return h.hexdigest()


def _cabecalho_edf_coerente(caminho: Path) -> tuple[bool, str]:
    """Verificação de integridade barata e específica do formato.

    Mais forte que comparar tamanho: relê o cabeçalho EDF e confere que
    `bytes_cabecalho + n_registros * bytes_por_registro` bate com o tamanho do
    arquivo. Um download truncado no meio passa no teste de "existe" e falha
    aqui, que é onde deve falhar.
    """
    try:
        with open(caminho, "rb") as fh:
            fixo = fh.read(256)
            if len(fixo) < 256:
                return False, "menor que um cabeçalho EDF"
            ns = int(fixo[252:256].decode("latin-1").strip())
            n_bytes_cab = int(fixo[184:192].decode("latin-1").strip())
            n_reg = int(fixo[236:244].decode("latin-1").strip())
            if n_bytes_cab != 256 * (ns + 1):
                return False, f"cabeçalho inconsistente ({n_bytes_cab} para {ns} sinais)"
            resto = fh.read(n_bytes_cab - 256)
        desloc = ns * (16 + 80 + 8 + 8 + 8 + 8 + 8 + 80)
        amostras = [
            int(resto[desloc + 8 * i: desloc + 8 * (i + 1)].decode("latin-1").strip())
            for i in range(ns)
        ]
        esperado = n_bytes_cab + n_reg * sum(amostras) * 2
        real = caminho.stat().st_size
        if real != esperado:
            return False, f"{real} bytes, cabeçalho prevê {esperado}"
        return True, f"{ns} canais, {n_reg} registros de 30 s — OK"
    except Exception as e:  # noqa: BLE001 — qualquer falha aqui é "arquivo ruim"
        return False, f"{type(e).__name__}: {e}"


def verificar(destino: Path, com_hash: bool = False) -> int:
    """Confere o que está em disco. Devolve o nº de problemas encontrados."""
    pnp = destino / SUBPASTA
    if not pnp.is_dir():
        print(f"nada em {pnp}", file=sys.stderr)
        return 1

    problemas = 0
    sujeitos = sorted(d.name for d in pnp.glob("sub-*") if d.is_dir())
    print(f"Verificando {len(sujeitos)} sujeito(s) em {pnp}")
    for s in sujeitos:
        edf = pnp / s / "eeg" / f"{s}_task-sleep_eeg.edf"
        if not edf.exists():
            print(f"  ✗ {s}: EDF ausente")
            problemas += 1
            continue
        ok, detalhe = _cabecalho_edf_coerente(edf)
        marca = "✓" if ok else "✗"
        extra = ""
        if ok and com_hash:
            extra = f" sha256={_sha256(edf)[:16]}…"
        print(f"  {marca} {s}: {detalhe}{extra}")
        problemas += 0 if ok else 1

    print(f"\n{len(sujeitos) - problemas}/{len(sujeitos)} íntegros.")
    if problemas:
        print("Rode de novo sem --verificar: o download retoma de onde parou.")
    return problemas


def listar_sujeitos_remotos() -> list[str]:
    """IDs `sub-NNN` do PlugNPlay, lidos do `participants.tsv` do servidor.

    Usa o `participants.tsv` e não um PROPFIND porque é um único GET de 2 KB e
    dá a lista **canônica** dos 100 do PlugNPlay, já ordenada.
    """
    with urllib.request.urlopen(
        _url(f"{SUBPASTA}/participants.tsv"), timeout=TEMPO_LIMITE_S
    ) as r:
        texto = r.read().decode("utf-8")
    linhas = [l for l in texto.splitlines() if l.strip()]
    return [l.split("\t")[0].strip() for l in linhas[1:]]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Baixa a coleção aberta Wearanize+ OA (CC-BY-4.0, sem cadastro).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exemplos:\n"
            "  python -m ferramentas.baixar_wearanize --n-sujeitos 10\n"
            "  python -m ferramentas.baixar_wearanize --sujeitos sub-005 sub-007\n"
            "  python -m ferramentas.baixar_wearanize --verificar\n"
            "  python -m ferramentas.baixar_wearanize --so-metadados\n"
        ),
    )
    p.add_argument("--destino", type=Path, default=DESTINO_PADRAO)
    p.add_argument(
        "--n-sujeitos",
        type=int,
        default=10,
        help="quantos sujeitos baixar, em ordem de ID (padrão: 10, ~5 GB)",
    )
    p.add_argument("--sujeitos", nargs="+", help="IDs explícitos, ex.: sub-005 sub-007")
    p.add_argument(
        "--so-metadados",
        action="store_true",
        help="baixa apenas os .tsv/.json/.txt (poucos MB) — bom para auditar canais",
    )
    p.add_argument("--verificar", action="store_true", help="checa integridade do que já está em disco")
    p.add_argument("--hash", action="store_true", help="com --verificar, calcula sha256 (lento)")
    p.add_argument("--forcar", action="store_true", help="rebaixa mesmo se completo")
    args = p.parse_args(argv)

    destino: Path = args.destino

    if args.verificar:
        return 1 if verificar(destino, com_hash=args.hash) else 0

    print("Wearanize+ OA — DOI 10.34973/xrmf-5726 — CC-BY-4.0")
    print("Uso científico apenas. Não tentar reidentificar participantes.")
    print("Citar doi:10.1093/sleepadvances/zpaf094 E doi:10.34973/j6jf-9e62.\n")

    # --- documentação da coleção (inclui LICENSE.txt) ----------------------
    print("Metadados da coleção:")
    for nome in ARQUIVOS_RAIZ:
        try:
            r = baixar(nome, destino / nome, forcar=args.forcar, silencioso=True)
            print(f"  ✓ {nome}{' (já em disco)' if r.ja_completo else ''}")
        except FileNotFoundError:
            print(f"  – {nome} (ausente no servidor)")
    for nome in ARQUIVOS_PNP:
        try:
            r = baixar(
                f"{SUBPASTA}/{nome}",
                destino / SUBPASTA / nome,
                forcar=args.forcar,
                silencioso=True,
            )
            print(f"  ✓ {SUBPASTA}/{nome}{' (já em disco)' if r.ja_completo else ''}")
        except FileNotFoundError:
            print(f"  – {SUBPASTA}/{nome} (ausente no servidor)")

    # --- quais sujeitos ----------------------------------------------------
    if args.sujeitos:
        sujeitos = list(args.sujeitos)
    else:
        todos = listar_sujeitos_remotos()
        sujeitos = todos[: args.n_sujeitos]
        print(f"\n{len(todos)} sujeitos no PlugNPlay; baixando os {len(sujeitos)} primeiros.")

    if args.so_metadados:
        print("\nSidecars (--so-metadados):")
        for s in sujeitos:
            for padrao in PADRAO_SUJEITO[1:]:
                rel = f"{SUBPASTA}/{padrao.format(s=s)}"
                try:
                    baixar(rel, destino / SUBPASTA / padrao.format(s=s),
                           forcar=args.forcar, silencioso=True)
                except FileNotFoundError:
                    pass
            print(f"  ✓ {s}")
        print("\nPronto. Nenhum EDF baixado (--so-metadados).")
        return 0

    # --- estimativa antes de gastar banda ----------------------------------
    print("\nMedindo o volume...")
    total = 0
    faltando = 0
    for s in sujeitos:
        rel = f"{SUBPASTA}/{PADRAO_SUJEITO[0].format(s=s)}"
        n = _tamanho_remoto(rel)
        if n is None:
            print(f"  ! {s}: EDF não existe no servidor", file=sys.stderr)
            continue
        total += n
        local = destino / SUBPASTA / PADRAO_SUJEITO[0].format(s=s)
        faltando += n - (local.stat().st_size if local.exists() else 0)
    print(f"  total {total/1e9:.1f} GB · falta baixar {max(faltando,0)/1e9:.1f} GB")

    # --- baixar ------------------------------------------------------------
    print()
    baixados = 0
    for i, s in enumerate(sujeitos, 1):
        print(f"[{i}/{len(sujeitos)}] {s}")
        for padrao in PADRAO_SUJEITO:
            rel = f"{SUBPASTA}/{padrao.format(s=s)}"
            alvo = destino / SUBPASTA / padrao.format(s=s)
            try:
                r = baixar(rel, alvo, forcar=args.forcar, silencioso=not rel.endswith(".edf"))
            except FileNotFoundError:
                print(f"  – {alvo.name} (ausente no servidor)")
                continue
            if r.ja_completo:
                print(f"  = {alvo.name} (já completo)")
            elif r.retomado:
                print(f"  ↻ {alvo.name} (retomado, +{r.bytes_baixados/1e6:.0f} MB)")
            baixados += r.bytes_baixados

    print(f"\nBaixados {baixados/1e9:.2f} GB para {destino}")
    print("Conferindo integridade...")
    problemas = verificar(destino)
    if problemas == 0:
        print("\nPróximo passo:")
        print("  python -m pytest testes -q")
        print("  python -m experimentos.ml02_baselines --dataset wearanize --posicao cabeca")
    return 1 if problemas else 0


if __name__ == "__main__":
    raise SystemExit(main())
