"""Compila o `firmware/sketch.ino` para o ESP32 de verdade e mede a RAM (FW-12).

Os testes do firmware rodam no host, com stubs no lugar do Arduino, e o host
nao tem o limite de RAM estatica do ESP32 (`dram0_0_seg`). Em 12/11 o sketch
passava em todos eles e nao ligava para o chip: estourava a RAM estatica em
18 088 B. Este script e a unica verificacao que ve esse limite.

Monta uma copia do sketch numa pasta temporaria (o `arduino-cli` exige que a
pasta tenha o nome do `.ino`), com o `secrets.example.h` no papel do
`secrets.h` -- a memoria e a mesma, e nenhum segredo entra --, compila com o
`partitions.csv` do projeto e imprime a RAM estatica usada.

Uso:
    python scripts/compilar_sketch_esp32.py [--arduino-cli CAMINHO] [--minimo-livre BYTES]
                                            [--firmware PASTA]

`--firmware` compila outra pasta com a mesma estrutura de `firmware/` -- e o
que o CI usa para o controle positivo (CI-12): uma copia sabotada tem de
reprovar.

O `arduino-cli` vem de `--arduino-cli`, da variavel ARDUINO_CLI ou do PATH, com
o pacote `esp32:esp32` instalado. Sai com 1 se nao ligar, ou se a folga de RAM
para o heap ficar abaixo de `--minimo-livre`.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

RAIZ = Path(__file__).resolve().parent.parent
FIRMWARE = RAIZ / "firmware"
ARQUIVOS_DO_SKETCH = [
    "sketch.ino",
    "nucleo_amalgama.cpp",
    "ca_raiz.h",
    "calibracao_da_unidade.h",
    "midia_flash_esp32.h",
    "partitions.csv",
]


def tamanho_da_aplicacao(particoes: Path) -> int:
    """O tamanho da fatia `factory` do partitions.csv: o teto do programa."""
    for linha in particoes.read_text(encoding="utf-8").splitlines():
        campos = [c.strip() for c in linha.split(",")]
        if len(campos) >= 5 and campos[0] == "factory":
            return int(campos[4], 0)
    raise SystemExit("partitions.csv sem a fatia `factory`")


def montar(destino: Path, firmware: Path) -> None:
    sketch = destino / "sketch"
    (sketch / "nucleo").mkdir(parents=True)
    for nome in ARQUIVOS_DO_SKETCH:
        shutil.copy2(firmware / nome, sketch / nome)
    shutil.copy2(firmware / "secrets.example.h", sketch / "secrets.h")
    for arq in (firmware / "nucleo").iterdir():
        if arq.suffix in (".h", ".cpp"):
            shutil.copy2(arq, sketch / "nucleo" / arq.name)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--arduino-cli", default=os.environ.get("ARDUINO_CLI", "arduino-cli"))
    ap.add_argument("--fqbn", default="esp32:esp32:esp32")
    ap.add_argument("--minimo-livre", type=int, default=150_000,
                    help="RAM minima que precisa sobrar para o heap (Wi-Fi, TLS, o lote)")
    ap.add_argument("--firmware", type=Path, default=FIRMWARE,
                    help="pasta com a estrutura de firmware/ (padrao: a do repositorio)")
    args = ap.parse_args()

    teto = tamanho_da_aplicacao(args.firmware / "partitions.csv")
    with tempfile.TemporaryDirectory(prefix="dormio-esp32-") as tmp:
        tmp = Path(tmp)
        montar(tmp, args.firmware)
        cmd = [args.arduino_cli, "compile", "--fqbn", args.fqbn,
               "--build-property", f"upload.maximum_size={teto}",
               "--build-path", str(tmp / "build"), str(tmp / "sketch")]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    saida = r.stdout + r.stderr

    estouro = re.search(r"region `(\w+)' overflowed by (\d+) bytes", saida)
    if estouro:
        print(f"✗ NAO LIGA: a regiao {estouro.group(1)} estourou em {int(estouro.group(2)):,} B".replace(",", " "))
        return 1
    if r.returncode != 0:
        print(saida[-3000:])
        print(f"✗ a compilacao falhou (codigo {r.returncode})")
        return 1

    programa = re.search(r"Sketch uses (\d+) bytes \((\d+)%\)", saida)
    ram = re.search(r"Global variables use (\d+) bytes \((\d+)%\).*?leaving (\d+) bytes", saida)
    if not (programa and ram):
        print(saida[-3000:])
        print("✗ nao achei o resumo de memoria na saida do arduino-cli")
        return 1
    usado, livre = int(ram.group(1)), int(ram.group(3))
    print(f"programa: {int(programa.group(1)):>9} B ({programa.group(2)}% da fatia factory)")
    print(f"RAM fixa: {usado:>9} B ({ram.group(2)}%); sobram {livre} B para o heap")
    if livre < args.minimo_livre:
        print(f"✗ menos de {args.minimo_livre} B para o heap")
        return 1
    print("✓ liga para o ESP32")
    return 0


if __name__ == "__main__":
    sys.exit(main())
