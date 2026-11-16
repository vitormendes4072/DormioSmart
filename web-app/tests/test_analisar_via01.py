"""A análise do VIA-01 (`scripts/analisar_via01.py`) com dados sintéticos.

O que importa travar: o script não pode "achar" separação em blocos iguais,
tem de achá-la em blocos claramente diferentes, e não pode contar as épocas
das bordas (a transição entre blocos mistura os dois).
"""
import importlib.util
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

_script = Path(__file__).resolve().parents[2] / "scripts" / "analisar_via01.py"
_spec = importlib.util.spec_from_file_location("analisar_via01", _script)
via01 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(via01)

INICIO = datetime(2026, 11, 20, 22, 0, tzinfo=timezone.utc)
BLOCO_S = 300
EPOCA_S = 30


def _blocos(rotulos=("A", "B", "C")):
    saida = []
    for i, r in enumerate(rotulos):
        inicio = INICIO + timedelta(seconds=i * BLOCO_S)
        saida.append({"rotulo": r, "inicio": inicio.isoformat(),
                      "fim": (inicio + timedelta(seconds=BLOCO_S)).isoformat()})
    return saida


def _epoca(t, nivel, rng):
    valores = {f: max(0.0, nivel + rng.gauss(0, 0.01)) for f in via01.FEATURES}
    return {"instante": t.isoformat(), **valores}


def _dados(niveis, rotulos=("A", "B", "C"), semente=1):
    """Uma época a cada 30 s, com o nível de cada bloco; ruído pequeno.

    A semente padrão é uma em que blocos iguais não se separam por acaso (a 7
    se separa: |δ| = 0,88 num par). A taxa de acaso é medida à parte, em
    `test_blocos_iguais_quase_nunca_separam`.
    """
    rng = random.Random(semente)
    epocas = []
    for i, r in enumerate(rotulos):
        for k in range(BLOCO_S // EPOCA_S):
            t = INICIO + timedelta(seconds=i * BLOCO_S + k * EPOCA_S)
            epocas.append(_epoca(t, niveis[r], rng))
    return {"blocos": _blocos(rotulos), "features": {"epocas": epocas}}


def test_delta_de_cliff_nos_extremos():
    assert via01.delta_de_cliff([5, 6, 7], [1, 2, 3]) == 1.0
    assert via01.delta_de_cliff([1, 2, 3], [5, 6, 7]) == -1.0
    assert via01.delta_de_cliff([1, 2, 3], [1, 2, 3]) == 0.0


#: Permutações nos testes: o suficiente para p < 0,05, e rápido no CI.
PERM = 200


def test_blocos_iguais_quase_nunca_separam():
    """O controle que impede o script de inventar separação.

    Uma semente só não basta: em 16/11 a semente 7 deu |δ| = 0,88 por acaso.
    Mede-se a taxa em 30 sementes, 90 pares; o critério é de 5 %.
    """
    separados = 0
    for semente in range(30):
        r = via01.analisar(_dados({"A": 0.1, "B": 0.1, "C": 0.1}, semente=semente),
                           permutacoes=PERM)
        separados += sum(p["separa"] for p in r["pares"].values())
    assert separados <= 9, f"{separados} de 90 pares iguais dados como separados"


def test_blocos_diferentes_separam():
    r = via01.analisar(_dados({"A": 0.0, "B": 0.5, "C": 1.0}), permutacoes=PERM)
    assert all(p["separa"] for p in r["pares"].values())
    assert r["veredito"].startswith("v1")


def test_so_o_corpo_igual_ao_repouso_aciona_o_hw07():
    """Cabeça separa, corpo não: é exatamente o caso que o HW-07 cobre."""
    r = via01.analisar(_dados({"A": 0.1, "B": 0.9, "C": 0.1}), permutacoes=PERM)
    assert r["pares"]["AxB"]["separa"]
    assert not r["pares"]["AxC"]["separa"]
    assert r["veredito"].startswith("aciona o HW-07")


def test_as_bordas_ficam_de_fora():
    """5 min com uma época a cada 30 s: 10 épocas; a do instante zero fica de fora."""
    dados = _dados({"A": 0.1, "B": 0.1, "C": 0.1})
    r = via01.analisar(dados, permutacoes=PERM)
    assert r["epocas_por_bloco"] == {"A": 9, "B": 9, "C": 9}


def test_a_borda_contaminada_nao_cria_separacao():
    """Épocas de transição com valor alto não podem decidir o par."""
    dados = _dados({"A": 0.1, "B": 0.1, "C": 0.1})
    for e in dados["features"]["epocas"]:
        t = via01.instante(e["instante"])
        segundos = (t - INICIO).total_seconds() % BLOCO_S
        if segundos < via01.MARGEM_S:
            for f in via01.FEATURES:
                e[f] = 5.0
    r = via01.analisar(dados, permutacoes=PERM)
    assert not any(p["separa"] for p in r["pares"].values())


def test_repeticao_soma_os_blocos_do_mesmo_rotulo():
    r = via01.analisar(_dados({"A": 0.1, "B": 0.1, "C": 0.1},
                              rotulos=("A", "B", "C", "A", "B", "C")), permutacoes=PERM)
    assert r["epocas_por_bloco"] == {"A": 18, "B": 18, "C": 18}


def test_bloco_sem_epocas_e_recusado():
    dados = _dados({"A": 0.1, "B": 0.1, "C": 0.1})
    dados["features"]["epocas"] = [
        e for e in dados["features"]["epocas"]
        if via01.instante(e["instante"]) < INICIO + timedelta(seconds=2 * BLOCO_S)
    ]
    with pytest.raises(via01.DadosInsuficientes, match="bloco C"):
        via01.analisar(dados)


def test_instante_sem_fuso_e_recusado():
    with pytest.raises(via01.DadosInsuficientes, match="fuso"):
        via01.instante("2026-11-20T22:00:00")


def test_rotulo_do_painel_por_bloco():
    dados = _dados({"A": 0.1, "B": 0.1, "C": 0.1})
    historico = []
    for e in dados["features"]["epocas"]:
        t = via01.instante(e["instante"])
        bloco = int((t - INICIO).total_seconds() // BLOCO_S)
        historico.append({"captured_at": e["instante"],
                          "status": "Repouso" if bloco == 0 else "Movimento",
                          "movimento_total": 9.8 + bloco})
    dados["historico"] = historico
    r = via01.analisar(dados, permutacoes=PERM)
    painel = r["rotulo_do_painel"]
    assert painel["A"]["movimento"] == 0
    assert painel["C"]["movimento"] == painel["C"]["leituras"] == 9
    assert painel["C"]["pico_mediano"] == pytest.approx(11.8)


def test_linha_de_comando(tmp_path, capsys):
    arquivo = tmp_path / "via01.json"
    arquivo.write_text(json.dumps(_dados({"A": 0.0, "B": 0.5, "C": 1.0})), encoding="utf-8")
    saida = tmp_path / "resultado.json"
    assert via01.main([str(arquivo), "--json", str(saida)]) == 0
    assert "veredito: v1" in capsys.readouterr().out
    assert json.loads(saida.read_text(encoding="utf-8"))["pares"]["AxC"]["separa"]


def test_linha_de_comando_com_dado_insuficiente(tmp_path, capsys):
    arquivo = tmp_path / "via01.json"
    arquivo.write_text(json.dumps({"blocos": _blocos(), "features": {"epocas": []}}),
                       encoding="utf-8")
    assert via01.main([str(arquivo)]) == 2
    assert "Não dá para analisar" in capsys.readouterr().err


def test_separacao_completa_com_poucas_epocas_nao_basta():
    """Com 3 épocas por bloco, até δ = 1 sai do acaso com frequência.

    Sem a permutação, este par seria dado como separado; com ela, p ≥ 0,05.
    """
    epocas = []
    for i, rotulo in enumerate(("A", "B", "C")):
        for k, desloc in enumerate((60, 120, 180)):
            t = INICIO + timedelta(seconds=i * BLOCO_S + desloc)
            base = {"A": 0.0, "B": 0.0, "C": 1.0}[rotulo]
            valores = {f: 0.5 for f in via01.FEATURES}
            valores["enmo_media"] = base + k * 0.1
            epocas.append({"instante": t.isoformat(), **valores})
    dados = {"blocos": _blocos(), "features": {"epocas": epocas}}
    r = via01.analisar(dados, permutacoes=PERM)
    assert r["pares"]["AxC"]["melhor_delta"] == 1.0
    assert r["pares"]["AxC"]["p_permutacao"] >= via01.ALFA
    assert not r["pares"]["AxC"]["separa"]


def test_diferenca_real_mas_pequena_nao_separa():
    """p < 0,05 com |δ| < 0,8: a diferença existe, mas não basta para o VIA-01.

    Com 18 épocas por bloco, um deslocamento de ~0,4 desvio-padrão sai do acaso
    sem chegar ao tamanho de efeito exigido. Sem o limiar de δ, separaria.
    """
    r = via01.analisar(_dados({"A": 0.1, "B": 0.1, "C": 0.108},
                              rotulos=("A", "B", "C", "A", "B", "C"), semente=1),
                       permutacoes=PERM)
    par = r["pares"]["AxC"]
    assert par["p_permutacao"] < via01.ALFA
    assert abs(par["melhor_delta"]) < via01.DELTA_QUE_SEPARA
    assert not par["separa"]


def test_rotulo_de_bloco_desconhecido_e_recusado():
    dados = _dados({"A": 0.1, "B": 0.1, "C": 0.1})
    dados["blocos"][1]["rotulo"] = "D"
    with pytest.raises(via01.DadosInsuficientes, match="desconhecido"):
        via01.analisar(dados, permutacoes=PERM)


def test_bloco_que_termina_antes_de_comecar_e_recusado():
    dados = _dados({"A": 0.1, "B": 0.1, "C": 0.1})
    bloco = dados["blocos"][0]
    bloco["inicio"], bloco["fim"] = bloco["fim"], bloco["inicio"]
    with pytest.raises(via01.DadosInsuficientes, match="termina antes"):
        via01.analisar(dados, permutacoes=PERM)
