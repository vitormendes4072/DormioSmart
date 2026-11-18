"""Análise da bancada do VIA-01: os blocos parado, cabeça e corpo se separam?

O protocolo está em `docs/PROTOCOLO-VIA-01.md`. A placa roda o firmware de
produto; as épocas chegam à produção, e o trecho de console do protocolo baixa
um JSON com as features (`/api/features`), o rótulo e o pico de cada época
(`/api/sleep-history`), a saída do modelo (`/api/inferencia`, quando a janela
basta) e os horários dos blocos anotados pelo autor.

── O CRITÉRIO, FIXADO ANTES DE VER OS DADOS ─────────────────────────────

Para cada par de blocos (A×B, A×C, B×C), cada feature é comparada pelo delta
de Cliff: a probabilidade de uma época de um bloco ter valor maior que uma do
outro, menos a probabilidade do contrário. Vai de −1 a 1; 0 é sobreposição
total, ±1 é separação completa. Com ~8 épocas por bloco, um p-valor sozinho
diria pouco, e o delta diz o tamanho da diferença.

Um par **separa** se as duas condições valerem:

1. ao menos uma feature tem |δ| ≥ `DELTA_QUE_SEPARA` (0,8, equivalente a uma
   AUC de 0,9);
2. esse máximo não sai do acaso: num teste de permutação, que embaralha as
   épocas entre os dois blocos `PERMUTACOES` vezes (semente fixa) e recalcula
   o maior |δ| entre as oito features, a fração de embaralhamentos com máximo
   igual ou maior que o observado fica abaixo de `ALFA` (0,05).

A condição 2 existe porque a 1 sozinha não diz quão raro é o máximo entre oito
features. No controle de 16/11, blocos sintéticos **idênticos**, com 9 épocas
cada, deram |δ| = 0,88 numa delas; a permutação mostrou que era um sorteio raro
(p ≈ 0,006), e não um defeito, mas sem ela não haveria como saber. Escolher a
melhor de oito infla o resultado; a permutação compara com o melhor de oito sob
o acaso. O teste mede a taxa de falso positivo em várias sementes.

**A pergunta do VIA-01 é o par A×C** (parado × corpo virando): se separa, o
travesseiro enxerga o corpo rolando, e o projeto fica na v1 (só o
travesseiro); se não separa, aciona-se a contingência do `HW-07`.

── O QUE ENTRA EM CADA BLOCO ────────────────────────────────────────────

Uma época entra num bloco se o seu instante estiver a pelo menos
`MARGEM_S` (30 s, uma época) de cada borda. Isso descarta as transições,
onde a época mistura dois blocos. Blocos com o mesmo rótulo (a repetição
A, B, C, A, B, C) são somados.

── USO ──────────────────────────────────────────────────────────────────

    python scripts/analisar_via01.py via01-AAAA-MM-DD.json
    python scripts/analisar_via01.py via01-AAAA-MM-DD.json --json saida.json

Saída 0 se a análise rodou; 2 se o arquivo não permite analisar (bloco sem
época, por exemplo). O veredito vai no texto, não no código de saída.
"""
from __future__ import annotations

import argparse
import random
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

#: |δ| a partir do qual um par de blocos conta como separado. Ver o docstring.
DELTA_QUE_SEPARA = 0.8

#: Embaralhamentos do teste de permutação, e a semente (o resultado é reprodutível).
PERMUTACOES = 2000
SEMENTE = 20261116

#: Nível do teste de permutação sobre o maior |δ| entre as features.
ALFA = 0.05

#: Distância mínima, em segundos, entre o instante da época e a borda do bloco.
MARGEM_S = 30

#: Épocas mínimas por bloco para a comparação valer alguma coisa.
MINIMO_POR_BLOCO = 3

FEATURES = ("enmo_media", "enmo_desvio", "enmo_max", "mag_din_media",
            "zcr", "p_frac", "inclinacao_rel", "d_angulo")

NOMES_DOS_BLOCOS = {"A": "parado", "B": "cabeça", "C": "corpo"}
PARES = (("A", "B"), ("A", "C"), ("B", "C"))


class DadosInsuficientes(ValueError):
    """O arquivo não permite a comparação (bloco vazio, rótulo desconhecido)."""


def instante(texto: str) -> datetime:
    """ISO 8601 com fuso; `Z` aceito. Sem fuso é erro: a janela depende dele."""
    valor = datetime.fromisoformat(texto.replace("Z", "+00:00"))
    if valor.tzinfo is None:
        raise DadosInsuficientes(f"instante sem fuso horário: {texto!r}")
    return valor


def delta_de_cliff(x: list[float], y: list[float]) -> float:
    """P(x > y) − P(x < y), sobre todos os pares. Empates contam zero."""
    if not x or not y:
        raise DadosInsuficientes("delta de Cliff com grupo vazio")
    maior = sum(1 for a in x for b in y if a > b)
    menor = sum(1 for a in x for b in y if a < b)
    return (maior - menor) / (len(x) * len(y))


def mediana(valores: list[float]) -> float:
    ordenados = sorted(valores)
    n = len(ordenados)
    meio = n // 2
    return ordenados[meio] if n % 2 else (ordenados[meio - 1] + ordenados[meio]) / 2


def epocas_por_bloco(blocos: list[dict], epocas: list[dict],
                     margem_s: int = MARGEM_S) -> dict[str, list[dict]]:
    """Agrupa as épocas pelo rótulo do bloco, descartando as das bordas."""
    grupos: dict[str, list[dict]] = {}
    for bloco in blocos:
        rotulo = bloco["rotulo"]
        if rotulo not in NOMES_DOS_BLOCOS:
            raise DadosInsuficientes(f"rótulo de bloco desconhecido: {rotulo!r}")
        inicio = instante(bloco["inicio"])
        fim = instante(bloco["fim"])
        if fim <= inicio:
            raise DadosInsuficientes(f"bloco {rotulo} termina antes de começar")
        de = inicio + timedelta(seconds=margem_s)
        ate = fim - timedelta(seconds=margem_s)
        dentro = [e for e in epocas if de <= instante(e["instante"]) <= ate]
        grupos.setdefault(rotulo, []).extend(dentro)
    for rotulo in NOMES_DOS_BLOCOS:
        if len(grupos.get(rotulo, [])) < MINIMO_POR_BLOCO:
            raise DadosInsuficientes(
                f"bloco {rotulo} ({NOMES_DOS_BLOCOS[rotulo]}) com "
                f"{len(grupos.get(rotulo, []))} época(s); são precisas {MINIMO_POR_BLOCO}")
    return grupos


def valores(epocas: list[dict], feature: str) -> list[float]:
    """Os valores não nulos de uma feature (o `d_angulo` é nulo depois de lacuna)."""
    return [float(e[feature]) for e in epocas if e.get(feature) is not None]


def deltas_por_feature(ea: list[dict], eb: list[dict]) -> dict[str, float]:
    """δ de Cliff de B contra A em cada feature com épocas suficientes nos dois."""
    saida = {}
    for f in FEATURES:
        va, vb = valores(ea, f), valores(eb, f)
        if len(va) >= MINIMO_POR_BLOCO and len(vb) >= MINIMO_POR_BLOCO:
            saida[f] = delta_de_cliff(vb, va)
    return saida


def p_da_permutacao(ea: list[dict], eb: list[dict], observado: float,
                    permutacoes: int = PERMUTACOES, semente: int = SEMENTE) -> float:
    """Fração dos embaralhamentos com maior |δ| ≥ o observado (com correção +1)."""
    rng = random.Random(semente)
    todas = ea + eb
    n = len(ea)
    alcancou = 0
    for _ in range(permutacoes):
        rng.shuffle(todas)
        deltas = deltas_por_feature(todas[:n], todas[n:])
        if deltas and max(abs(d) for d in deltas.values()) >= observado - 1e-12:
            alcancou += 1
    return (alcancou + 1) / (permutacoes + 1)


def comparar(grupos: dict[str, list[dict]], permutacoes: int = PERMUTACOES) -> dict:
    """Delta de Cliff por feature para cada par, a permutação e o veredito do par."""
    pares = {}
    for a, b in PARES:
        por_feature = deltas_por_feature(grupos[a], grupos[b])
        if not por_feature:
            raise DadosInsuficientes(f"par {a}×{b} sem feature comparável")
        melhor = max(por_feature, key=lambda f: abs(por_feature[f]))
        maximo = abs(por_feature[melhor])
        p = p_da_permutacao(grupos[a], grupos[b], maximo, permutacoes)
        pares[f"{a}x{b}"] = {
            "deltas": por_feature,
            "melhor_feature": melhor,
            "melhor_delta": por_feature[melhor],
            "p_permutacao": p,
            "separa": maximo >= DELTA_QUE_SEPARA and p < ALFA,
        }
    return pares


def rotulos_por_bloco(blocos: list[dict], historico: list[dict]) -> dict[str, dict]:
    """Quantas leituras de cada bloco o painel rotulou "Movimento", e o pico mediano."""
    leituras = [
        {"instante": h.get("captured_at") or h.get("created_at"),
         "status": h.get("status"), "pico": h.get("movimento_total")}
        for h in historico if (h.get("captured_at") or h.get("created_at"))
    ]
    grupos = epocas_por_bloco(blocos, leituras) if leituras else {}
    saida = {}
    for rotulo, itens in grupos.items():
        movimento = sum(1 for i in itens if i["status"] == "Movimento")
        picos = [float(i["pico"]) for i in itens if i["pico"] is not None]
        saida[rotulo] = {
            "leituras": len(itens),
            "movimento": movimento,
            "pico_mediano": mediana(picos) if picos else None,
        }
    return saida


def analisar(dados: dict, permutacoes: int = PERMUTACOES) -> dict:
    blocos = dados["blocos"]
    grupos = epocas_por_bloco(blocos, dados["features"]["epocas"])
    resultado = {
        "criterio": {"delta_que_separa": DELTA_QUE_SEPARA, "alfa": ALFA,
                     "permutacoes": permutacoes, "semente": SEMENTE, "margem_s": MARGEM_S},
        "epocas_por_bloco": {r: len(e) for r, e in grupos.items()},
        "medianas": {
            r: {f: mediana(valores(e, f)) for f in FEATURES if valores(e, f)}
            for r, e in grupos.items()
        },
        "pares": comparar(grupos, permutacoes),
    }
    if dados.get("historico"):
        try:
            resultado["rotulo_do_painel"] = rotulos_por_bloco(blocos, dados["historico"])
        except DadosInsuficientes as e:
            resultado["rotulo_do_painel"] = {"indisponivel": str(e)}
    resultado["veredito"] = (
        "v1: o travesseiro separa o corpo virando do repouso"
        if resultado["pares"]["AxC"]["separa"]
        else "aciona o HW-07: o travesseiro não separa o corpo virando do repouso")
    return resultado


def imprimir(resultado: dict) -> None:
    print("VIA-01 — os blocos se separam?")
    print(f"  critério: |δ de Cliff| ≥ {DELTA_QUE_SEPARA} em ao menos uma feature e "
          f"p < {ALFA} na permutação do maior |δ|; margem de {MARGEM_S} s em cada borda")
    for rotulo, n in sorted(resultado["epocas_por_bloco"].items()):
        print(f"  bloco {rotulo} ({NOMES_DOS_BLOCOS[rotulo]}): {n} épocas")
    for par, r in resultado["pares"].items():
        marca = "separa" if r["separa"] else "NÃO separa"
        print(f"  {par}: {marca} (melhor: {r['melhor_feature']}, δ = {r['melhor_delta']:+.2f}, "
              f"p = {r['p_permutacao']:.3f})")
    painel = resultado.get("rotulo_do_painel")
    if painel and "indisponivel" not in painel:
        for rotulo, r in sorted(painel.items()):
            print(f"  rótulo do painel, bloco {rotulo}: {r['movimento']}/{r['leituras']} "
                  f"\"Movimento\", pico mediano {r['pico_mediano']}")
    print(f"  veredito: {resultado['veredito']}")


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("arquivo", type=Path)
    ap.add_argument("--json", type=Path, help="grava o resultado também em JSON")
    args = ap.parse_args(argv)
    try:
        dados = json.loads(args.arquivo.read_text(encoding="utf-8"))
        resultado = analisar(dados)
    except (DadosInsuficientes, KeyError) as e:
        print(f"Não dá para analisar: {e}", file=sys.stderr)
        return 2
    imprimir(resultado)
    if args.json:
        args.json.write_text(json.dumps(resultado, ensure_ascii=False, indent=2),
                             encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
