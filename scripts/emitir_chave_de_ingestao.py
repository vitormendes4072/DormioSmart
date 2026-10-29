#!/usr/bin/env python3
"""Emite o JWT do papel `dormio_ingestao` (SEC-06).

O painel do Supabase emite chave para `anon` e `service_role`, e só. Para um
papel próprio é preciso um JWT assinado com o JWT secret do projeto, carregando
`{"role": "dormio_ingestao"}` — o PostgREST faz `SET ROLE` a partir dessa claim.

    Settings > API > JWT Settings > JWT Secret

USO

    export SUPABASE_JWT_SECRET='o-segredo-do-projeto'
    python scripts/emitir_chave_de_ingestao.py

    # com validade definida (padrão: 5 anos)
    python scripts/emitir_chave_de_ingestao.py --anos 1

O segredo entra por variável de ambiente e NUNCA por argumento de linha de
comando: argumento fica no histórico do shell e aparece na lista de processos
de qualquer usuário da máquina. O script não escreve o resultado em arquivo —
copie da saída para o seu `.env` e para as variáveis de ambiente do servidor.

PRÉ-REQUISITO: `web-app/migrations/005_papel_de_ingestao_minimo.sql` aplicado.
Sem o `grant dormio_ingestao to authenticator` que ele faz, o PostgREST recusa
o token com "unable to set role".

Dependência: PyJWT (já está em web-app/requirements.txt via supabase, mas se
faltar: pip install pyjwt).
"""
import argparse
import datetime as dt
import os
import sys

VARIAVEL_SEGREDO = "SUPABASE_JWT_SECRET"
PAPEL = "dormio_ingestao"


def emitir(segredo, anos):
    import jwt  # PyJWT

    agora = dt.datetime.now(tz=dt.timezone.utc)
    # `iss: supabase` e o par iat/exp são o que o PostgREST e o GoTrue esperam
    # ver num token do projeto. `sub` fica de fora de propósito: este token não
    # representa um usuário, e um `sub` aqui faria `auth.uid()` devolver algo —
    # o que não deve acontecer no caminho de ingestão.
    corpo = {
        "role": PAPEL,
        "iss": "supabase",
        "iat": int(agora.timestamp()),
        "exp": int((agora + dt.timedelta(days=365 * anos)).timestamp()),
    }
    return jwt.encode(corpo, segredo, algorithm="HS256"), corpo


def principal():
    analisador = argparse.ArgumentParser(
        description="Emite o JWT do papel de ingestão (SEC-06).",
        epilog=f"O segredo vem de ${VARIAVEL_SEGREDO}, nunca de argumento.",
    )
    analisador.add_argument(
        "--anos", type=int, default=5, help="validade em anos (padrão: 5)"
    )
    argumentos = analisador.parse_args()

    segredo = os.environ.get(VARIAVEL_SEGREDO, "").strip()
    if not segredo:
        print(
            f"ERRO: ${VARIAVEL_SEGREDO} nao definida.\n\n"
            "  Supabase > Settings > API > JWT Settings > JWT Secret\n"
            f"  export {VARIAVEL_SEGREDO}='...'\n",
            file=sys.stderr,
        )
        return 1

    if argumentos.anos < 1:
        print("ERRO: --anos deve ser >= 1.", file=sys.stderr)
        return 1

    try:
        token, corpo = emitir(segredo, argumentos.anos)
    except ImportError:
        print("ERRO: PyJWT ausente. `pip install pyjwt`", file=sys.stderr)
        return 1

    expira = dt.datetime.fromtimestamp(corpo["exp"], tz=dt.timezone.utc)

    print(f"Papel:   {PAPEL}")
    print(f"Expira:  {expira.date().isoformat()}")
    print()
    print("Ponha isto no .env local e nas variaveis de ambiente do servidor")
    print("(Vercel > Settings > Environment Variables):")
    print()
    print(f"SUPABASE_INGESTAO_KEY={token}")
    print()
    print("Depois: apague a linha acima do historico do terminal, e confira")
    print("com `python web-app/teste_conexao.py`.")
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
