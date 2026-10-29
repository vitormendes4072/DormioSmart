#!/usr/bin/env python3
"""Confere que a produção responde e alcança o banco (INFRA-03).

── POR QUE EXISTE ────────────────────────────────────────────────────────

Em 2026-10-28 o `/health` de produção respondia 503 havia um tempo indeterminado:
o projeto Supabase, no plano gratuito, é **pausado depois de uma semana sem
uso**, e a produção não recebia dado desde setembro. O domínio do projeto nem
resolvia no DNS. Ninguém percebeu, porque nada no repositório olhava a produção.

Este script é chamado por `.github/workflows/saude-producao.yml` a cada 3 dias.
Ele serve a duas coisas, e as duas dependem de o `/health` fazer uma consulta
REAL ao banco (`sleep_data`, limite 1 — ver `verificar_conexao` em
`web-app/database.py`):

  1. **manter o projeto ativo** — supondo que a consulta conte como uso para o
     critério de inatividade do plano gratuito (hipótese, não medida); 3 dias
     deixa folga dentro de uma semana;
  2. **avisar quando cair** — o job reprova, e o GitHub manda e-mail.

── O QUE CONTA COMO "NO AR" ───────────────────────────────────────────────

HTTP 200 **e** corpo JSON com `"banco": "ok"`. Só o 200 não basta: um proxy ou
uma página de erro podem responder 200 com outro corpo. Um 503 com
`"banco": "consulta falhou"` é exatamente o estado de 28/10.

Tenta algumas vezes antes de reprovar, porque a função serverless do Vercel tem
partida a frio e o primeiro pedido pode estourar o prazo — reprovar por isso
seria alarme falso, e alarme falso ensina a ignorar o alarme.

    python scripts/conferir_producao.py
    python scripts/conferir_producao.py --url https://outro-endereco/health
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

URL_PADRAO = "https://dormio-smart.vercel.app/health"


def consultar(url: str, prazo_s: float) -> tuple[bool, str]:
    """Uma tentativa. Devolve (no_ar, descrição do que se viu)."""
    try:
        with urllib.request.urlopen(url, timeout=prazo_s) as r:
            codigo, corpo = r.status, r.read(2000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        codigo, corpo = e.code, e.read(2000).decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return False, f"sem resposta: {e}"
    try:
        banco = json.loads(corpo).get("banco")
    except (json.JSONDecodeError, AttributeError):
        banco = None
    if codigo == 200 and banco == "ok":
        return True, f"HTTP {codigo}, banco ok"
    return False, f"HTTP {codigo}, banco={banco!r}, corpo={corpo[:160]!r}"


def main() -> int:
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--url", default=URL_PADRAO)
    ap.add_argument("--tentativas", type=int, default=3)
    ap.add_argument("--espera", type=float, default=20.0,
                    help="segundos entre tentativas")
    ap.add_argument("--prazo", type=float, default=30.0,
                    help="segundos de espera por resposta")
    args = ap.parse_args()

    visto = ""
    for n in range(1, args.tentativas + 1):
        ok, visto = consultar(args.url, args.prazo)
        print(f"tentativa {n}/{args.tentativas}: {visto}")
        if ok:
            print(f"OK — {args.url} no ar, com o banco alcançável.")
            return 0
        if n < args.tentativas:
            time.sleep(args.espera)
    print(f"FORA DO AR — {args.url}: {visto}\n"
          "Se o banco caiu, a causa mais provável é o projeto Supabase pausado "
          "por inatividade (plano gratuito): reative no painel. Ver INFRA-03.",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
