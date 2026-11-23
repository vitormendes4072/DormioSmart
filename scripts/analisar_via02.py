"""Análise do VIA-02: o travesseiro capta o movimento que o celular capta, na mesma noite?

O protocolo está em `docs/PROTOCOLO-VIA-02.md`. Em cada noite, o travesseiro e o
app gravam juntos, cada um para a conta do autor; o trecho de console do
protocolo baixa, para os dois aparelhos, as épocas com as features
(`/api/features`), o rótulo e o pico de cada época (`/api/sleep-history`) e,
quando a janela basta, a saída do modelo (`/api/inferencia`).

Não diz se a pessoa estava dormindo: dois sensores concordando não provam que
estão certos. Compara dois sensores.

── O CRITÉRIO, FIXADO ANTES DOS DADOS (23/11) ───────────────────────────

1. **Pareamento.** O instante de cada época é o FIM dela (`captured_at`), e ela
   cobre os 30 s anteriores. Cada aparelho ancora a própria grade quando liga,
   então as grades ficam defasadas de 0 a 30 s. Cada época do travesseiro casa
   com a do celular que mais se sobrepõe a ela, com ao menos `SOBREPOSICAO_S`
   (15 s) em comum; no empate exato de 15 s, a do celular que termina depois.
   Sem par, a época fica de fora: trecho sem registro não é discordância.
2. **Atraso entre os relógios.** Desloca-se o celular de −2 a +2 registros e
   fica o deslocamento de maior correlação (Pearson) da intensidade entre os
   pares (empate: o menor em módulo). O deslocamento escolhido é aplicado e
   relatado. Pearson, e não a correlação de postos: numa noite quase toda
   parada, a ordem das épocas paradas é ruído, e os postos dela diluem a
   correlação (medido nos testes: 0,25 no deslocamento certo, e o vizinho
   ganhava por acaso).
3. **Por noite:** dos registros com movimento no celular, quantos o travesseiro
   também viu, e o contrário; o κ de Cohen entre os rótulos; a correlação da
   intensidade (Pearson e Spearman); a fração com movimento em cada um; a
   cobertura de cada aparelho na janela comum. Noite com menos de
   `MINIMO_DE_PARES` (120, uma hora) não entra no veredito.
4. **O veredito**, sobre as noites que entram (são precisas
   `NOITES_PARA_O_VEREDITO`, 5): o travesseiro **capta** o que o celular capta
   se viu ao menos `VIU_MINIMO` (80%) dos registros com movimento no celular,
   e se o limite inferior do intervalo de 95% passa de `LIMITE_INFERIOR` (70%).
   O intervalo vem de um bootstrap por blocos de `BLOCO` (20) pares seguidos
   (10 min), porque registros vizinhos não são independentes; `REAMOSTRAS`
   2 000, semente fixa.
5. **Também se relata**, sem entrar no veredito: o limiar do celular que faria
   a fração com movimento dele igualar a do travesseiro (candidato para o
   `DATA-06`) e, quando veio, se o modelo chega à mesma classe nos dois.

── USO ──────────────────────────────────────────────────────────────────

    python scripts/analisar_via02.py via02-AAAA-MM-DD.json [mais noites...] [--json saida.json]

Saída 0 se a análise rodou; 2 se nenhum arquivo permite analisar.
"""
from __future__ import annotations

import argparse
import bisect
import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

EPOCA_S = 30
SOBREPOSICAO_S = 15
ATRASOS = (-2, -1, 0, 1, 2)
MINIMO_DE_PARES = 120
NOITES_PARA_O_VEREDITO = 5
VIU_MINIMO = 0.80
LIMITE_INFERIOR = 0.70
BLOCO = 20
REAMOSTRAS = 2000
SEMENTE = 20261123
GRAVIDADE = 9.81


class DadosInsuficientes(ValueError):
    """O arquivo não permite a comparação."""


def instante(texto: str) -> datetime:
    valor = datetime.fromisoformat(texto.replace("Z", "+00:00"))
    if valor.tzinfo is None:
        raise DadosInsuficientes(f"instante sem fuso horário: {texto!r}")
    return valor


def serie(aparelho: dict) -> list[dict]:
    """As épocas de um aparelho, em ordem: fim, rótulo, intensidade e a feature de movimento.

    O rótulo e o pico vêm do histórico; a `mag_din_media`, das features, casada
    pelo instante (até 1 s de diferença).
    """
    features = sorted(((instante(e["instante"]), e) for e in (aparelho.get("features") or {}).get("epocas", [])),
                      key=lambda x: x[0])
    tempos = [t for t, _ in features]
    saida = []
    for h in aparelho.get("historico") or []:
        quando = h.get("captured_at")
        if not quando or h.get("status") is None:
            continue
        fim = instante(quando)
        pico = h.get("movimento_total")
        item = {"fim": fim, "movimento": h["status"] == "Movimento",
                "intensidade": abs(float(pico) - GRAVIDADE) if pico is not None else None,
                "mag_din_media": None}
        i = bisect.bisect_left(tempos, fim - timedelta(seconds=1))
        if i < len(tempos) and abs((tempos[i] - fim).total_seconds()) <= 1:
            item["mag_din_media"] = features[i][1].get("mag_din_media")
        saida.append(item)
    saida.sort(key=lambda e: e["fim"])
    return saida


def parear(trav: list[dict], cel: list[dict], atraso: int = 0) -> list[tuple[dict, dict]]:
    """Pares (travesseiro, celular) por sobreposição, com o celular deslocado de `atraso` registros."""
    desloca = timedelta(seconds=atraso * EPOCA_S)
    fins = [e["fim"] - desloca for e in cel]
    pares = []
    for t in trav:
        i = bisect.bisect_left(fins, t["fim"] - timedelta(seconds=SOBREPOSICAO_S))
        melhor, distancia = None, None
        for j in (i, i + 1):
            if j < len(fins):
                d = abs((fins[j] - t["fim"]).total_seconds())
                if d <= EPOCA_S - SOBREPOSICAO_S and (distancia is None or d < distancia
                                                      or (d == distancia and fins[j] > fins[melhor])):
                    melhor, distancia = j, d
        if melhor is not None:
            pares.append((t, cel[melhor]))
    return pares


def _postos(valores: list[float]) -> list[float]:
    ordem = sorted(range(len(valores)), key=lambda i: valores[i])
    postos = [0.0] * len(valores)
    i = 0
    while i < len(ordem):
        j = i
        while j + 1 < len(ordem) and valores[ordem[j + 1]] == valores[ordem[i]]:
            j += 1
        for k in range(i, j + 1):
            postos[ordem[k]] = (i + j) / 2 + 1
        i = j + 1
    return postos


def _pearson(x: list[float], y: list[float]) -> float | None:
    n = len(x)
    if n < 3:
        return None
    mx, my = sum(x) / n, sum(y) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    return sxy / (sxx * syy) ** 0.5 if sxx > 0 and syy > 0 else None


def spearman(x: list[float], y: list[float]) -> float | None:
    return _pearson(_postos(x), _postos(y)) if len(x) >= 3 else None


def _valor(e: dict) -> float | None:
    return e["mag_din_media"] if e["mag_din_media"] is not None else e["intensidade"]


def medir_atraso(trav: list[dict], cel: list[dict]) -> int:
    """O deslocamento do celular, em registros, de maior correlação da intensidade."""
    melhor, maior = 0, None
    for atraso in sorted(ATRASOS, key=abs):
        pares = [(a, b) for a, b in parear(trav, cel, atraso) if _valor(a) is not None and _valor(b) is not None]
        r = _pearson([_valor(a) for a, _ in pares], [_valor(b) for _, b in pares])
        if r is not None and (maior is None or r > maior + 1e-12):
            melhor, maior = atraso, r
    return melhor


def kappa(x: list[bool], y: list[bool]) -> float | None:
    n = len(x)
    if n == 0:
        return None
    po = sum(1 for a, b in zip(x, y) if a == b) / n
    px, py = sum(x) / n, sum(y) / n
    pe = px * py + (1 - px) * (1 - py)
    return (po - pe) / (1 - pe) if pe < 1 else None


def _fracao(contagem: int, total: int) -> float | None:
    return contagem / total if total else None


def limiar_que_iguala(intensidades: list[float], fracao: float) -> float | None:
    """O limiar de intensidade com o qual a fração acima dele fica igual a `fracao`."""
    if not intensidades:
        return None
    ordenadas = sorted(intensidades, reverse=True)
    k = round(fracao * len(ordenadas))
    if k <= 0:
        return ordenadas[0]
    if k >= len(ordenadas):
        return ordenadas[-1] - 1e-9
    return (ordenadas[k - 1] + ordenadas[k]) / 2


def _cobertura(epocas: list[dict], inicio: datetime, fim: datetime) -> float | None:
    esperadas = (fim - inicio).total_seconds() / EPOCA_S
    if esperadas <= 0:
        return None
    return min(1.0, sum(1 for e in epocas if inicio < e["fim"] <= fim) / esperadas)


def _modelo(noite: dict, pares: list[tuple[dict, dict]]) -> dict | None:
    """Concordância do modelo entre os dois aparelhos, quando os dois trouxeram a inferência."""
    classes = {}
    for nome in ("travesseiro", "celular"):
        inf = (noite.get(nome) or {}).get("inferencia") or {}
        classes[nome] = {instante(e["instante"]).replace(microsecond=0): e["classe"] for e in inf.get("epocas", [])}
    if not classes["travesseiro"] or not classes["celular"]:
        return None
    iguais = total = 0
    for a, b in pares:
        ca = classes["travesseiro"].get(a["fim"].replace(microsecond=0))
        cb = classes["celular"].get(b["fim"].replace(microsecond=0))
        if ca is not None and cb is not None:
            total += 1
            iguais += ca == cb
    return {"pares_com_classe": total, "concordancia": _fracao(iguais, total)}


def analisar_noite(noite: dict) -> dict:
    trav, cel = serie(noite.get("travesseiro") or {}), serie(noite.get("celular") or {})
    if not trav or not cel:
        raise DadosInsuficientes("um dos aparelhos não tem época com rótulo")
    atraso = medir_atraso(trav, cel)
    pares = parear(trav, cel, atraso)
    if not pares:
        raise DadosInsuficientes("nenhuma época do travesseiro casa com uma do celular")
    mov_t = [a["movimento"] for a, _ in pares]
    mov_c = [b["movimento"] for _, b in pares]
    ambos = sum(1 for a, b in zip(mov_t, mov_c) if a and b)
    inicio = max(trav[0]["fim"], cel[0]["fim"]) - timedelta(seconds=EPOCA_S)
    fim = min(trav[-1]["fim"], cel[-1]["fim"])
    com_valor = [(a, b) for a, b in pares if _valor(a) is not None and _valor(b) is not None]
    fracao_t = sum(mov_t) / len(pares)
    intensidades_c = [b["intensidade"] for _, b in pares if b["intensidade"] is not None]
    return {
        "pares": len(pares),
        "entra_no_veredito": len(pares) >= MINIMO_DE_PARES,
        "atraso_em_registros": atraso,
        "cobertura_travesseiro": _cobertura(trav, inicio, fim),
        "cobertura_celular": _cobertura(cel, inicio, fim),
        "movimento_no_celular": sum(mov_c),
        "movimento_no_travesseiro": sum(mov_t),
        "movimento_nos_dois": ambos,
        "travesseiro_viu_do_celular": _fracao(ambos, sum(mov_c)),
        "celular_viu_do_travesseiro": _fracao(ambos, sum(mov_t)),
        "kappa": kappa(mov_t, mov_c),
        "pearson_intensidade": _pearson([_valor(a) for a, _ in com_valor], [_valor(b) for _, b in com_valor]),
        "spearman_intensidade": spearman([_valor(a) for a, _ in com_valor], [_valor(b) for _, b in com_valor]),
        "fracao_movimento_travesseiro": fracao_t,
        "fracao_movimento_celular": sum(mov_c) / len(pares),
        "limiar_do_celular_que_iguala": limiar_que_iguala(intensidades_c, fracao_t),
        "modelo": _modelo(noite, pares),
        "_pares": pares,
    }


def _bootstrap_viu(noites: list[dict], reamostras: int = REAMOSTRAS) -> tuple[float, float] | None:
    """IC de 95% de "o travesseiro viu" por bootstrap de blocos de pares seguidos."""
    blocos = []
    for n in noites:
        pares = n["_pares"]
        for i in range(0, len(pares), BLOCO):
            fatia = pares[i:i + BLOCO]
            blocos.append((sum(1 for a, b in fatia if a["movimento"] and b["movimento"]),
                           sum(1 for _, b in fatia if b["movimento"])))
    if not blocos:
        return None
    rng = random.Random(SEMENTE)
    valores = []
    for _ in range(reamostras):
        amostra = [blocos[rng.randrange(len(blocos))] for _ in blocos]
        viu, total = sum(a for a, _ in amostra), sum(t for _, t in amostra)
        if total:
            valores.append(viu / total)
    valores.sort()
    if not valores:
        return None
    return valores[int(0.025 * len(valores))], valores[int(0.975 * len(valores)) - 1]


def analisar(noites: list[dict], reamostras: int = REAMOSTRAS) -> dict:
    resultados = [analisar_noite(n) for n in noites]
    entram = [r for r in resultados if r["entra_no_veredito"]]
    viu = sum(r["movimento_nos_dois"] for r in entram)
    total = sum(r["movimento_no_celular"] for r in entram)
    veredito = {"noites_que_entram": len(entram), "viu": _fracao(viu, total), "capta": None}
    if len(entram) < NOITES_PARA_O_VEREDITO:
        veredito["motivo"] = f"são precisas {NOITES_PARA_O_VEREDITO} noites com ao menos {MINIMO_DE_PARES} pares; há {len(entram)}"
    elif not total:
        veredito["motivo"] = "o celular não registrou movimento nas noites que entram"
    else:
        ic = _bootstrap_viu(entram, reamostras)
        veredito["ic95"] = list(ic) if ic else None
        veredito["capta"] = bool(veredito["viu"] >= VIU_MINIMO and ic and ic[0] > LIMITE_INFERIOR)
    for r in resultados:
        del r["_pares"]
    return {
        "criterio": {"sobreposicao_s": SOBREPOSICAO_S, "atrasos": list(ATRASOS), "minimo_de_pares": MINIMO_DE_PARES,
                     "noites_para_o_veredito": NOITES_PARA_O_VEREDITO, "viu_minimo": VIU_MINIMO,
                     "limite_inferior": LIMITE_INFERIOR, "bloco": BLOCO, "reamostras": reamostras, "semente": SEMENTE},
        "noites": resultados,
        "veredito": veredito,
    }


def _tres(x) -> str:
    return "—" if x is None else f"{x:.3f}"


def imprimir(resultado: dict, nomes: list[str]) -> None:
    print("VIA-02 — o travesseiro capta o movimento que o celular capta?")
    for nome, r in zip(nomes, resultado["noites"]):
        fora = "" if r["entra_no_veredito"] else "  (fora do veredito: noite curta)"
        print(f"  {nome}: {r['pares']} pares, atraso {r['atraso_em_registros']:+d}, "
              f"viu {_tres(r['travesseiro_viu_do_celular'])}, κ {_tres(r['kappa'])}, "
              f"cobertura trav {_tres(r['cobertura_travesseiro'])}, cel {_tres(r['cobertura_celular'])}{fora}")
    v = resultado["veredito"]
    if v["capta"] is None:
        print(f"  veredito: nenhum ({v['motivo']})")
    else:
        print(f"  veredito: o travesseiro {'capta' if v['capta'] else 'NÃO capta'} o que o celular capta "
              f"(viu {v['viu']:.3f}, IC95 {v.get('ic95')})")


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("arquivos", type=Path, nargs="+")
    ap.add_argument("--json", type=Path, help="grava o resultado também em JSON")
    args = ap.parse_args(argv)
    try:
        noites = [json.loads(a.read_text(encoding="utf-8")) for a in args.arquivos]
        resultado = analisar(noites)
    except (DadosInsuficientes, KeyError) as e:
        print(f"Não dá para analisar: {e}", file=sys.stderr)
        return 2
    imprimir(resultado, [a.name for a in args.arquivos])
    if args.json:
        args.json.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
