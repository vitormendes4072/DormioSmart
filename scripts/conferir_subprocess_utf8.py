"""Reprova `subprocess` que lê texto sem declarar a codificação (CI-11).

`subprocess.run(..., text=True)` sem `encoding` decodifica a saída do filho na
página de código do sistema. No Windows com `PYTHONIOENCODING=utf-8`, o filho
escreve em UTF-8, o pai lê em cp1252, a thread de leitura falha e o `stdout`
volta `None`: foi o `TypeError` do verificador do vetor dourado (AUD-09,
medido de novo em 13/11). O Linux do CI não reproduz, porque lá tudo é UTF-8 —
por isso a checagem é no texto do código, e não na execução.

Reprova `text=True` ou `universal_newlines=True` sem `encoding=` em
`subprocess.run`, `check_output` e `Popen`, nas pastas abaixo — o `ml/` inteiro
desde 13/11, quando o Codex corrigiu as cinco de `ml/experimentos` e
`ml/ferramentas` (PR #180).

Uso:  python scripts/conferir_subprocess_utf8.py [arquivo_ou_pasta ...]
"""
import ast
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PASTAS = ("scripts", "web-app", "ml")
CHAMADAS = {"run", "check_output", "Popen", "call", "check_call"}


def problemas(caminho):
    arvore = ast.parse(caminho.read_text(encoding="utf-8"), filename=str(caminho))
    for no in ast.walk(arvore):
        if not isinstance(no, ast.Call):
            continue
        nome = getattr(no.func, "attr", None) or getattr(no.func, "id", None)
        if nome not in CHAMADAS:
            continue
        argumentos = {k.arg: k.value for k in no.keywords if k.arg}
        texto = any(
            isinstance(argumentos.get(k), ast.Constant) and argumentos[k].value is True
            for k in ("text", "universal_newlines")
        )
        if texto and "encoding" not in argumentos:
            yield no.lineno


def arquivos(alvos):
    for alvo in alvos:
        if alvo.is_file():
            yield alvo
        else:
            yield from sorted(p for p in alvo.rglob("*.py")
                              if ".venv" not in p.parts and "node_modules" not in p.parts)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    alvos = [Path(a) for a in sys.argv[1:]] or [RAIZ / p for p in PASTAS]
    achados = [(f, linha) for f in arquivos(alvos) for linha in problemas(f)]
    if achados:
        print(f"FALHOU — {len(achados)} subprocess lendo texto sem encoding (CI-11):")
        for f, linha in achados:
            nome = f.relative_to(RAIZ) if f.is_relative_to(RAIZ) else f
            print(f"  ✗ {nome}:{linha} — acrescente encoding=\"utf-8\", errors=\"replace\"")
        return 1
    print(f"OK — nenhum subprocess lendo texto sem encoding em {', '.join(PASTAS)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
