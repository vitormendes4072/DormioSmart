"""ML-14: audita F1 historico pelas contagens, sem reescrever experimentos.

Saida deterministica e JSON estrito; NaN legado e representado por null com
estado explicito. Os hashes identificam os arquivos efetivamente inspecionados.
Sem contagens, o valor nao pode ser corrigido por este instrumento.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

NOME_SAIDA = "ml14_auditoria_f1.json"
PADRAO = Path(__file__).resolve().parents[1] / "experimentos" / "saida"


def auditar(pasta: Path) -> dict:
    arquivos, divergencias, sem_contagens = [], [], []
    recalculados = 0

    def visitar(no, caminho, arquivo):
        nonlocal recalculados
        if isinstance(no, dict):
            for campo, acertos in (("f1_sono", "vp"), ("f1_vigilia", "vn")):
                if campo not in no:
                    continue
                if not all(k in no for k in ("vp", "vn", "fp", "fn")):
                    sem_contagens.append({"arquivo": arquivo, "caminho": caminho + "." + campo})
                    continue
                contagens = {k: no[k] for k in ("vp", "vn", "fp", "fn")}
                if not all(type(v) is int and v >= 0 for v in contagens.values()):
                    raise ValueError("contagens invalidas em " + arquivo + ":" + caminho)
                recalculados += 1
                denom = 2 * no[acertos] + no["fp"] + no["fn"]
                esperado = 2 * no[acertos] / denom if denom else None
                antigo = no[campo]
                nan = isinstance(antigo, float) and math.isnan(antigo)
                finito = type(antigo) in (int, float) and math.isfinite(antigo)
                igual = nan if esperado is None else (
                    finito and math.isclose(antigo, esperado, rel_tol=1e-12, abs_tol=1e-12))
                if not igual:
                    divergencias.append({
                        "arquivo": arquivo, "caminho": caminho + "." + campo,
                        "contagens": contagens,
                        "estado_anterior": "NaN" if nan else ("finito" if finito else "invalido"),
                        "valor_anterior": antigo if finito else None,
                        "f1_recalculado": esperado,
                    })
            for chave, valor in no.items():
                visitar(valor, caminho + "." + chave, arquivo)
        elif isinstance(no, list):
            for i, valor in enumerate(no):
                visitar(valor, caminho + "[" + str(i) + "]", arquivo)

    for p in sorted(pasta.glob("*.json")):
        if p.name == NOME_SAIDA:
            continue
        # O checkout do Git muda CRLF/LF entre Windows e Linux.
        bruto = p.read_bytes().replace(b"\r\n", b"\n")
        arquivos.append({"arquivo": p.name, "sha256_utf8_lf": hashlib.sha256(bruto).hexdigest()})
        visitar(json.loads(bruto.decode("utf-8")), "$", p.name)

    return {
        "item": "ML-14",
        "criterio": "F1 = 2TP/(2TP+FP+FN); indefinido somente se denominador zero",
        "arquivos": arquivos, "n_arquivos": len(arquivos),
        "n_valores_recalculaveis": recalculados,
        "n_divergencias": len(divergencias),
        "n_arquivos_afetados": len({d["arquivo"] for d in divergencias}),
        "divergencias": divergencias,
        "sem_contagens": sem_contagens,
        "limite": "Sem matriz por sujeito ou predicoes, nao reconstroi medias ou ICs de F1.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pasta", type=Path, default=PADRAO)
    parser.add_argument("--conferir", action="store_true")
    args = parser.parse_args()
    if not args.pasta.is_dir():
        parser.error("pasta de resultados inexistente")
    resultado = auditar(args.pasta)
    if not resultado["n_arquivos"] or not resultado["n_valores_recalculaveis"]:
        parser.error("nenhum resultado com F1 e contagens para auditar")
    texto = json.dumps(resultado, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    destino = args.pasta / NOME_SAIDA
    if args.conferir:
        if not destino.is_file() or destino.read_text(encoding="utf-8") != texto:
            print("FALHOU: auditoria ausente ou divergente; gere novamente.")
            return 1
    else:
        destino.write_text(texto, encoding="utf-8")
    print(f'ML-14: {resultado["n_divergencias"]} divergencias em '
          f'{resultado["n_arquivos_afetados"]}/{resultado["n_arquivos"]} arquivos.')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
