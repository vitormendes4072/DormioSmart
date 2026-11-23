"""Análise da etapa 3 do CAL-03: em noite real, a calibração tirou o viés da orientação?

Na noite de 10/11, sem calibração, o Moto E7 parado lia a gravidade 2 % maior com
a tela para baixo, e a medida de movimento (`enmo_media`) das épocas paradas
subia de 0,5 a 0,95 mg para 23 mg sem movimento nenhum (diário, 10/11 (iii)). A
etapa 2 fez o app juntar os pontos parados entre noites e calibrar cada noite
nova (diário, 11/11 (viii)). Falta ver, com noites de verdade, se o piso da
medida deixa de depender da posição do celular.

Lê os mesmos arquivos `via02-AAAA-MM-DD.json` do `docs/PROTOCOLO-VIA-02.md`, e
só o aparelho `celular`. Precisa da exportação 2.12.0 ou mais nova, em que
`/api/features` traz, por época, `g`, `g_norma`, `calibrada` e `temp`.

── O CRITÉRIO, FIXADO ANTES DOS DADOS (23/11) ───────────────────────────

1. **Época parada:** `mag_din_media` abaixo de `LIMIAR_PARADO_G` (10 mg), o
   mesmo critério com que o núcleo escolhe os pontos de calibração
   (`firmware/nucleo/calibracao.h`). Época sem `g`, sem `g_norma` ou sem
   `enmo_media` não entra.
2. **Orientação, pelo eixo z da gravidade unitária:** `tela para cima` com
   g_z acima de `COS_ORIENTACAO` (cos 30°), `tela para baixo` com g_z abaixo de
   −`COS_ORIENTACAO`; o resto (em pé, de lado, inclinado) não entra. No Android,
   z sai da tela: parado de tela para cima, g_z ≈ +1.
3. **Por noite e por orientação, separando a época calibrada da que não é:**
   o piso (a mediana de `enmo_media` das épocas paradas, em mg), a mediana de
   `g_norma` e a da temperatura. Grupo com menos de `MINIMO_PARADAS` (30
   épocas, 15 min) não entra.
4. **O veredito, só com as épocas calibradas:** são precisas ao menos
   `NOITES_POR_ORIENTACAO` (2) noites com o grupo válido em cada orientação.
   Com elas, a calibração **tirou o viés** se as duas condições valem:
   - a diferença entre as medianas dos pisos por noite das duas orientações
     fica em até `DIFERENCA_MAXIMA_MG` (3 mg). Sem calibração, foram 22,1 mg
     em 10/11, e 7,9 mg com a calibração de mesa;
   - em cada orientação, a mediana das normas por noite fica a até
     `DESVIO_MAXIMO_DA_NORMA` (0,5 %) de 1 g.
   Sem noites bastantes, o veredito é "inconclusivo".
5. **Também se relata**, sem entrar no veredito: o mesmo para as épocas sem
   calibração (o controle: o viés deve aparecer ali), a primeira noite
   calibrada, a noite com calibração só em parte, a orientação declarada no
   arquivo contra a medida e a linha "Calibração do sensor" anotada do cartão.

Os limiares do núcleo (os 10 mg de época parada e os 2 °C de faixa de
temperatura) seguem provisórios: esta análise os descreve, não os valida.

── USO ──────────────────────────────────────────────────────────────────

    python scripts/analisar_cal03.py via02-AAAA-MM-DD.json [mais noites...] [--json saida.json]

Saída 0 se a análise rodou; 2 se nenhum arquivo permite analisar.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

LIMIAR_PARADO_G = 0.010
COS_ORIENTACAO = 0.8660254037844386  # cos 30°
MINIMO_PARADAS = 30
NOITES_POR_ORIENTACAO = 2
DIFERENCA_MAXIMA_MG = 3.0
DESVIO_MAXIMO_DA_NORMA = 0.005
ORIENTACOES = ("cima", "baixo")
NOME = {"cima": "tela para cima", "baixo": "tela para baixo"}


class DadosInsuficientes(ValueError):
    """O arquivo não permite a análise."""


def _numero(v) -> float | None:
    if isinstance(v, bool) or v is None:
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if x == x and abs(x) != float("inf") else None


def orientacao(g) -> str | None:
    """'cima', 'baixo' ou None, pelo z da gravidade unitária."""
    if not isinstance(g, (list, tuple)) or len(g) != 3:
        return None
    z = _numero(g[2])
    if z is None:
        return None
    if z > COS_ORIENTACAO:
        return "cima"
    if z < -COS_ORIENTACAO:
        return "baixo"
    return None


def epocas_do_celular(dados: dict) -> list[dict]:
    celular = dados.get("celular")
    if not celular or not (celular.get("features") or {}).get("epocas"):
        raise DadosInsuficientes("o arquivo não tem épocas do celular")
    epocas = celular["features"]["epocas"]
    if not any("g" in e and "calibrada" in e for e in epocas):
        raise DadosInsuficientes(
            "a exportação não traz g e calibrada por época (é anterior ao contrato 2.12.0)")
    return epocas


def paradas(epocas: list[dict]) -> list[dict]:
    """Épocas paradas com orientação definida: {orientacao, calibrada, enmo_mg, g_norma, temp}."""
    saida = []
    for e in epocas:
        mag = _numero(e.get("mag_din_media"))
        enmo = _numero(e.get("enmo_media"))
        norma = _numero(e.get("g_norma"))
        lado = orientacao(e.get("g"))
        if mag is None or enmo is None or norma is None or lado is None:
            continue
        if not mag < LIMIAR_PARADO_G:
            continue
        saida.append({"orientacao": lado, "calibrada": e.get("calibrada") is True,
                      "enmo_mg": enmo * 1000.0, "g_norma": norma,
                      "temp": _numero(e.get("temp"))})
    return saida


def _grupo(itens: list[dict]) -> dict:
    temps = [i["temp"] for i in itens if i["temp"] is not None]
    return {"paradas": len(itens), "valido": len(itens) >= MINIMO_PARADAS,
            "piso_mg": statistics.median(i["enmo_mg"] for i in itens) if itens else None,
            "g_norma": statistics.median(i["g_norma"] for i in itens) if itens else None,
            "temp": statistics.median(temps) if temps else None}


def resumo_da_noite(dados: dict, nome: str = "") -> dict:
    epocas = epocas_do_celular(dados)
    com_campo = [e for e in epocas if "calibrada" in e]
    calibradas = sum(1 for e in com_campo if e.get("calibrada") is True)
    p = paradas(epocas)
    grupos = {}
    for cal in (True, False):
        for lado in ORIENTACOES:
            grupos[(cal, lado)] = _grupo([i for i in p if i["calibrada"] is cal and i["orientacao"] == lado])
    contagem = {lado: sum(1 for i in p if i["orientacao"] == lado) for lado in ORIENTACOES}
    medida = max(ORIENTACOES, key=lambda lado: contagem[lado]) if any(contagem.values()) else None
    return {
        "arquivo": nome,
        "inicio": (dados.get("janela") or {}).get("inicio"),
        "epocas": len(epocas),
        "fracao_calibrada": calibradas / len(com_campo) if com_campo else 0.0,
        "orientacao_declarada": dados.get("orientacao_do_celular"),
        "orientacao_medida": medida,
        "linha_de_calibracao": dados.get("linha_de_calibracao"),
        "grupos": grupos,
    }


def comparar(noites: list[dict], calibrada: bool) -> dict:
    """Diferença dos pisos e norma por orientação, com os grupos válidos de `calibrada`."""
    por_lado = {}
    for lado in ORIENTACOES:
        validos = [n["grupos"][(calibrada, lado)] for n in noites if n["grupos"][(calibrada, lado)]["valido"]]
        por_lado[lado] = {
            "noites": len(validos),
            "piso_mg": statistics.median(g["piso_mg"] for g in validos) if validos else None,
            "g_norma": statistics.median(g["g_norma"] for g in validos) if validos else None,
            "temp": statistics.median(g["temp"] for g in validos if g["temp"] is not None)
            if any(g["temp"] is not None for g in validos) else None,
        }
    bastam = all(por_lado[lado]["noites"] >= NOITES_POR_ORIENTACAO for lado in ORIENTACOES)
    diferenca = (por_lado["baixo"]["piso_mg"] - por_lado["cima"]["piso_mg"]
                 if por_lado["cima"]["piso_mg"] is not None and por_lado["baixo"]["piso_mg"] is not None
                 else None)
    return {"por_orientacao": por_lado, "noites_bastam": bastam, "diferenca_mg": diferenca}


def veredito(noites: list[dict]) -> dict:
    calibradas = comparar(noites, True)
    controle = comparar(noites, False)
    if not calibradas["noites_bastam"]:
        decisao, motivo = "inconclusivo", (
            f"são precisas {NOITES_POR_ORIENTACAO} noites calibradas com {MINIMO_PARADAS} "
            "épocas paradas em cada orientação")
    else:
        dif_ok = abs(calibradas["diferenca_mg"]) <= DIFERENCA_MAXIMA_MG
        normas_ok = all(abs(calibradas["por_orientacao"][lado]["g_norma"] - 1.0) <= DESVIO_MAXIMO_DA_NORMA
                        for lado in ORIENTACOES)
        if dif_ok and normas_ok:
            decisao, motivo = "tirou o viés", "diferença e normas dentro do critério"
        else:
            partes = []
            if not dif_ok:
                partes.append(f"diferença de {calibradas['diferenca_mg']:.2f} mg acima de {DIFERENCA_MAXIMA_MG} mg")
            if not normas_ok:
                partes.append(f"norma a mais de {DESVIO_MAXIMO_DA_NORMA:.1%} de 1 g")
            decisao, motivo = "não tirou o viés", "; ".join(partes)
    return {"decisao": decisao, "motivo": motivo, "calibradas": calibradas, "sem_calibracao": controle}


def _fmt(x, casas=2) -> str:
    return "—" if x is None else f"{x:.{casas}f}"


def imprimir(noites: list[dict], resultado: dict) -> None:
    print("Noite                 épocas  calibrada  orientação (declarada/medida)")
    for n in noites:
        print(f"{(n['inicio'] or n['arquivo'])[:20]:20}  {n['epocas']:6}  {n['fracao_calibrada']:8.0%}"
              f"   {n['orientacao_declarada'] or '—'} / {n['orientacao_medida'] or '—'}")
        if 0.0 < n["fracao_calibrada"] < 1.0:
            print("    ⚠ calibração só em parte da noite")
        if n["linha_de_calibracao"]:
            print(f"    cartão: {n['linha_de_calibracao']}")
        for (cal, lado), g in n["grupos"].items():
            if g["paradas"]:
                print(f"    {'calibrada' if cal else 'sem calib.'}  {NOME[lado]:16} paradas {g['paradas']:4}"
                      f"  piso {_fmt(g['piso_mg'])} mg  norma {_fmt(g['g_norma'], 4)} g"
                      f"  temp {_fmt(g['temp'], 1)} °C{'' if g['valido'] else '  (poucas)'}")
    for chave, titulo in (("calibradas", "Épocas calibradas"), ("sem_calibracao", "Sem calibração (controle)")):
        c = resultado[chave]
        print(f"\n{titulo}: diferença baixo − cima {_fmt(c['diferenca_mg'])} mg")
        for lado in ORIENTACOES:
            o = c["por_orientacao"][lado]
            print(f"    {NOME[lado]:16} noites {o['noites']}  piso {_fmt(o['piso_mg'])} mg"
                  f"  norma {_fmt(o['g_norma'], 4)} g  temp {_fmt(o['temp'], 1)} °C")
    print(f"\nVeredito: {resultado['decisao']} ({resultado['motivo']}).")


def _serializavel(noites: list[dict], resultado: dict) -> dict:
    def grupos(n):
        return {f"{'calibrada' if cal else 'sem_calibracao'}_{lado}": g for (cal, lado), g in n["grupos"].items()}
    return {"criterio": {"limiar_parado_g": LIMIAR_PARADO_G, "cos_orientacao": COS_ORIENTACAO,
                         "minimo_paradas": MINIMO_PARADAS, "noites_por_orientacao": NOITES_POR_ORIENTACAO,
                         "diferenca_maxima_mg": DIFERENCA_MAXIMA_MG,
                         "desvio_maximo_da_norma": DESVIO_MAXIMO_DA_NORMA},
            "noites": [dict(n, grupos=grupos(n)) for n in noites], "veredito": resultado}


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("arquivos", nargs="+", type=Path)
    ap.add_argument("--json", type=Path)
    args = ap.parse_args(argv)
    noites = []
    for caminho in args.arquivos:
        try:
            noites.append(resumo_da_noite(json.loads(caminho.read_text(encoding="utf-8")), caminho.name))
        except (DadosInsuficientes, json.JSONDecodeError, OSError) as erro:
            print(f"{caminho.name}: fora da análise — {erro}")
    if not noites:
        return 2
    noites.sort(key=lambda n: n["inicio"] or n["arquivo"])
    resultado = veredito(noites)
    imprimir(noites, resultado)
    if args.json:
        args.json.write_text(json.dumps(_serializavel(noites, resultado), ensure_ascii=False, indent=1),
                             encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
