#!/usr/bin/env python3
"""Confere que o firmware valida o certificado do servidor (SEC-15).

── POR QUE EXISTE ────────────────────────────────────────────────────────

Até 2026-11-03 os sketches usavam `setInsecure()`: aceitavam qualquer
certificado, e quem controlasse a rede Wi-Fi podia ler o `X-Device-Token` e
gravar noites falsas na conta do dono (auditoria de 31/10, A5). A correção é
`setCACert(CA_RAIZ)`, com as raízes de `firmware/ca_raiz.h`. Ela pode se
desfazer de quatro jeitos silenciosos, e este script reprova cada um:

  1. um sketch voltar a `setInsecure()`, ou abrir `WiFiClientSecure` sem
     `setCACert(CA_RAIZ)`;
  2. a cópia de `ca_raiz.h` de um sketch divergir da canônica (o Arduino IDE
     1.8 só compila o que está na pasta do sketch, então a cópia é imposta);
  3. um certificado colado errado — confere a impressão digital SHA-256 de
     cada um contra a lista abaixo, e que nenhum sobra ou falta;
  4. com `--producao`: a Vercel trocar para uma CA fora da lista. O
     dispositivo deixaria de enviar (sem perder dado: a flash guarda 11
     dias), e o aviso precisa chegar antes. Roda no monitor da produção.

O que este script NÃO prova: que o `mbedtls` do ESP32 aceita a cadeia. O
`--producao` usa o OpenSSL desta máquina. O handshake na placa é validado na
bancada.

    python scripts/conferir_tls_firmware.py
    python scripts/conferir_tls_firmware.py --producao
"""
from __future__ import annotations

import argparse
import hashlib
import re
import socket
import ssl
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FIRMWARE = RAIZ / "firmware"
CANONICO = FIRMWARE / "ca_raiz.h"
HOST_PADRAO = "dormio-smart.vercel.app"

# Impressões digitais SHA-256 do DER, conferidas em 03/11/2026 contra o pacote
# de raízes da Mozilla e contra a cadeia real da Vercel (WR1 -> GTS Root R1).
ESPERADAS = {
    "GTS Root R1": "d947432abde7b7fa90fc2e6b59101b1280e0e1c7e4e40fa3c6887fff57a7f4cf",
    "GTS Root R4": "349dfa4058c5e263123b398ae795573c4e1313c83fe68f93556cd5e8031b3c7d",
    "ISRG Root X1": "96bcec06264976f37460779acf28c5a7cfe8a3c0aae11a8ffcee05c0bddf08c6",
    "ISRG Root X2": "69729b8e15a86efc177a57afb7171dfc64add28c2fca8cf1507e34453ccb1470",
}

PEM = re.compile(r"-----BEGIN CERTIFICATE-----\n.*?\n-----END CERTIFICATE-----\n", re.S)


def sem_comentarios(codigo: str) -> str:
    """Tira `//` e `/* */` respeitando strings, que têm `https://` dentro."""
    saida, i, n = [], 0, len(codigo)
    while i < n:
        c = codigo[i]
        if c in "\"'":
            j = i + 1
            while j < n and codigo[j] != c:
                j += 2 if codigo[j] == "\\" else 1
            saida.append(codigo[i:j + 1])
            i = j + 1
        elif codigo.startswith("//", i):
            fim = codigo.find("\n", i)
            i = n if fim < 0 else fim
        elif codigo.startswith("/*", i):
            fim = codigo.find("*/", i + 2)
            i = n if fim < 0 else fim + 2
        else:
            saida.append(c)
            i += 1
    return "".join(saida)


def pems_do_cabecalho(texto: str) -> str:
    """Reconstrói o texto de `CA_RAIZ[]` a partir dos literais do C."""
    corpo = sem_comentarios(texto)
    m = re.search(r"CA_RAIZ\[\]\s*=\s*(.*?);", corpo, re.S)
    if not m:
        return ""
    literais = re.findall(r'"((?:[^"\\]|\\.)*)"', m.group(1))
    return "".join(literais).replace("\\n", "\n")


def conferir_estatico() -> list[str]:
    problemas: list[str] = []
    if not CANONICO.exists():
        return [f"{CANONICO.relative_to(RAIZ).as_posix()} não existe"]
    canonico = CANONICO.read_bytes()

    # (2) cópias idênticas
    for copia in sorted(FIRMWARE.rglob("ca_raiz.h")):
        if copia != CANONICO and copia.read_bytes() != canonico:
            problemas.append(f"{copia.relative_to(RAIZ).as_posix()} diverge de firmware/ca_raiz.h")

    # (3) impressões digitais
    pems = PEM.findall(pems_do_cabecalho(canonico.decode("utf-8")))
    vistas = {}
    for p in pems:
        try:
            vistas[hashlib.sha256(ssl.PEM_cert_to_DER_cert(p)).hexdigest()] = p
        except ValueError as e:
            problemas.append(f"certificado ilegível em ca_raiz.h: {e}")
    esperadas = set(ESPERADAS.values())
    for nome, fp in ESPERADAS.items():
        if fp not in vistas:
            problemas.append(f"{nome} ausente ou alterado em ca_raiz.h (SHA-256 {fp[:16]}…)")
    for fp in vistas:
        if fp not in esperadas:
            problemas.append(f"certificado não listado em ca_raiz.h (SHA-256 {fp[:16]}…)")

    # (1) sketches
    for ino in sorted(FIRMWARE.rglob("*.ino")):
        if "testes" in ino.parts:
            continue
        codigo = sem_comentarios(ino.read_text(encoding="utf-8"))
        nome = ino.relative_to(RAIZ).as_posix()
        if re.search(r"\bsetInsecure\s*\(", codigo):
            problemas.append(f"{nome} chama setInsecure()")
        if "WiFiClientSecure" not in codigo:
            continue
        if not re.search(r"\bsetCACert\s*\(\s*CA_RAIZ\s*\)", codigo):
            problemas.append(f"{nome} usa WiFiClientSecure sem setCACert(CA_RAIZ)")
        if not re.search(r'#include\s+"ca_raiz\.h"', codigo):
            problemas.append(f'{nome} não inclui "ca_raiz.h"')
        if not (ino.parent / "ca_raiz.h").exists():
            problemas.append(f"{nome}: falta ca_raiz.h na pasta do sketch")
    return problemas


def conferir_cadeia(host: str, prazo_s: float) -> tuple[bool, str]:
    """Abre TLS com o host confiando SÓ nas raízes do firmware."""
    cadata = pems_do_cabecalho(CANONICO.read_text(encoding="utf-8"))
    contexto = ssl.create_default_context(cadata=cadata)
    try:
        with socket.create_connection((host, 443), timeout=prazo_s) as s:
            with contexto.wrap_socket(s, server_hostname=host) as t:
                emissor = dict(x[0] for x in t.getpeercert()["issuer"])
                return True, f"cadeia aceita (emissor do servidor: {emissor.get('commonName')})"
    except ssl.SSLCertVerificationError as e:
        return False, f"cadeia RECUSADA pelas raízes do firmware: {e.verify_message}"
    except (OSError, ssl.SSLError) as e:
        return False, f"sem conexão: {e}"


def main() -> int:
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--producao", action="store_true",
                    help="confere também a cadeia real do servidor (usa rede)")
    ap.add_argument("--host", default=HOST_PADRAO)
    ap.add_argument("--tentativas", type=int, default=3)
    ap.add_argument("--espera", type=float, default=20.0)
    args = ap.parse_args()

    problemas = conferir_estatico()
    for p in problemas:
        print(f"  ✗ {p}")
    if problemas:
        print(f"FALHOU — {len(problemas)} problema(s) no TLS do firmware (SEC-15).",
              file=sys.stderr)
        return 1
    print(f"  ✓ sketches com setCACert(CA_RAIZ), cópias idênticas, "
          f"{len(ESPERADAS)} raízes com a impressão digital esperada")

    if args.producao:
        visto = ""
        for n in range(1, args.tentativas + 1):
            ok, visto = conferir_cadeia(args.host, 30.0)
            print(f"  tentativa {n}/{args.tentativas}: {args.host}: {visto}")
            if ok:
                break
            if "RECUSADA" in visto or n == args.tentativas:
                print(f"FALHOU — {args.host}: {visto}\n"
                      "Se a Vercel trocou de CA, o dispositivo deixa de enviar: incluir a "
                      "raiz nova em firmware/ca_raiz.h e regravar. Ver SEC-15.",
                      file=sys.stderr)
                return 1
            time.sleep(args.espera)
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
