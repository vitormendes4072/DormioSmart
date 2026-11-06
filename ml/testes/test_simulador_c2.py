"""O simulador da C2 (`scripts/simulador_c2.py`, SIM-02).

O simulador só tem valor enquanto for indistinguível do dispositivo para o
servidor. Por isso estes testes não conferem o simulador contra uma cópia das
regras: conferem contra o CÓDIGO DO SERVIDOR (`web-app/validacao.py`,
`lote.py`, `features_noite.py`) e contra as constantes nos arquivos do
FIRMWARE, lidas do disco.

O que NÃO se testa aqui: que o sinal sintético se parece com sono de verdade.
Não se parece o bastante para medir nada — ver o topo do simulador.
"""

from __future__ import annotations

import json
import math
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pytest

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))
sys.path.insert(0, str(RAIZ / "web-app"))

import features_noite  # noqa: E402  (web-app)
import lote as lote_servidor  # noqa: E402  (web-app)
import simulador_c2 as sim  # noqa: E402
from validacao import validar_captacao, validar_leitura  # noqa: E402  (web-app)

from src.features import FEATURES_DO_DISPOSITIVO, NOMES_FEATURES, features_de_epoca  # noqa: E402

INICIO = datetime(2026, 11, 1, 23, 0, tzinfo=timezone(timedelta(hours=-3)))


@pytest.fixture(scope="module")
def noite():
    """3 h, semente fixa: tem latência, sono, viradas e despertar final."""
    epocas = list(sim.NoiteSintetica(INICIO, 360, seed=7))
    return epocas, [sim.payload_da_epoca(e) for e in epocas]


# =====================================================================
# 1. As constantes vêm do firmware, não de memória
# =====================================================================
def _ler(rel):
    return (RAIZ / rel).read_text(encoding="utf-8")


def test_constantes_batem_com_o_firmware():
    payload_h = _ler("firmware/nucleo/payload.h")
    assert float(re.search(r"GRAVIDADE_MS2 = ([\d.]+)f", payload_h).group(1)) == sim.GRAVIDADE_MS2
    assert float(re.search(r"LIMIAR_MOVIMENTO_MS2 = ([\d.]+)f", payload_h).group(1)) == sim.LIMIAR_MOVIMENTO_MS2
    assert re.search(r'METODO_AGREGACAO = "([^"]+)"', payload_h).group(1) == sim.METODO_AGREGACAO
    assert int(re.search(r"MAX_LEITURAS_POR_LOTE = (\d+)", _ler("firmware/nucleo/lote.h")).group(1)) \
        == sim.MAX_LEITURAS_POR_LOTE == lote_servidor.MAX_LEITURAS_POR_LOTE
    assert re.search(r'TOKEN_HEADER = "([^"]+)"', _ler("web-app/device_auth.py")).group(1) == sim.TOKEN_HEADER
    # O envio a cada 10 min do sketch são 20 épocas de 30 s.
    minutos = int(re.search(r"INTERVALO_DE_ENVIO_US = (\d+)ull \* 60ull", _ler("firmware/sketch.ino")).group(1))
    assert minutos * 60 // sim.EPOCA_S == sim.EPOCAS_POR_ENVIO_TEMPO_REAL
    # O pico da C2 sai da grade multiplicado pela mesma constante.
    assert "e.pico_total = sqrtf(m2_pico) * GRAVIDADE_MS2" in _ler("firmware/nucleo/epoca_c2.cpp")


# =====================================================================
# 2. O servidor aceita cada época, e cada lote
# =====================================================================
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_toda_epoca_passa_na_validacao_do_servidor(seed):
    for e in sim.NoiteSintetica(INICIO, 120, seed=seed):
        p = sim.payload_da_epoca(e)
        # ida e volta por JSON, como chega ao Flask
        p = json.loads(json.dumps(p))
        aceito, erro = validar_leitura(p)
        assert erro is None, f"seed {seed}, época {e.indice}: {erro}"
        _, erro = validar_captacao(p["ts"])
        assert erro is None, f"seed {seed}, época {e.indice}: {erro}"


def test_os_lotes_do_simulador_passam_no_envelope_do_servidor(noite):
    _, payloads = noite
    tamanhos = []

    def servidor(url, token, corpo):
        leituras, erro, status = lote_servidor.extrair_leituras(json.loads(json.dumps(corpo)))
        if erro:
            return status, json.dumps({"error": erro})
        tamanhos.append(len(leituras))
        resp = lote_servidor.nova_resposta()
        for i, p in enumerate(leituras):
            _, erro = validar_leitura(p)
            (resp["rejeitadas"].append({"indice": i, "erro": erro}) if erro
             else resp["aceitas"].append(i))
        return lote_servidor.status_da_resposta(resp), json.dumps(resp)

    r = sim.enviar_fila(list(payloads), "u", "t", transporte=servidor, avisar=lambda *_: None)
    assert r.interrompido == ""
    assert r.aceitas == len(payloads) and r.rejeitadas == 0
    assert max(tamanhos) == sim.MAX_LEITURAS_POR_LOTE
    assert r.lotes == math.ceil(len(payloads) / sim.MAX_LEITURAS_POR_LOTE)


# =====================================================================
# 3. O instante: início da época, passo de 30 s, nunca no futuro
# =====================================================================
def _instante(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def test_ts_e_o_inicio_da_epoca_com_passo_de_30_s(noite):
    epocas, payloads = noite
    assert payloads[0]["ts"] == "2026-11-02T02:00:00.000Z"   # 23h em -03:00
    for e, p in zip(epocas, payloads):
        assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z", p["ts"])
        assert _instante(p["ts"]) == e.inicio
    passos = {(_instante(b["ts"]) - _instante(a["ts"])).total_seconds()
              for a, b in zip(payloads, payloads[1:])}
    assert passos == {30.0}


@pytest.mark.parametrize("agora_h, esperado", [
    (1, datetime(2026, 11, 4, 23, 0)),    # de madrugada: a de ontem não terminou
    (12, datetime(2026, 11, 5, 23, 0)),
    (23, datetime(2026, 11, 5, 23, 0)),   # a de hoje acabou de começar
])
def test_a_noite_padrao_ja_terminou(agora_h, esperado):
    fuso = timezone(timedelta(hours=-3))
    agora = datetime(2026, 11, 6, agora_h, 30, tzinfo=fuso)
    inicio = sim._inicio_padrao(agora, timedelta(hours=8))
    assert inicio == esperado.replace(tzinfo=fuso)
    assert inicio + timedelta(hours=8) <= agora


# =====================================================================
# 4. O pico, o status e o vetor — o que o firmware monta
# =====================================================================
def test_pico_status_e_vetor_sao_os_do_firmware(noite):
    epocas, payloads = noite
    for e, p in zip(epocas[:60], payloads[:60]):
        m = np.linalg.norm(e.grade, axis=1)
        i = int(np.argmax(m))
        assert p["total"] == round(float(m[i]) * 9.81, 2)
        assert [p["ax"], p["ay"], p["az"]] == [round(float(v) * 9.81, 2) for v in e.grade[i]]
        assert p["status"] == ("Movimento" if abs(m[i] * 9.81 - 9.81) > 1.2 else "Repouso")
        assert (p["epoca_s"], p["amostras"], p["fs"], p["metodo"]) == (30, 960, 32.0, "pico-da-magnitude")
        # `f` na ordem canônica: recalculado aqui, pelo NOME
        X, _ = features_de_epoca(e.grade[None], fs=32.0)
        assert p["f"] == [float(X[0, NOMES_FEATURES.index(n)]) for n in FEATURES_DO_DISPOSITIVO]
        assert abs(math.sqrt(sum(c * c for c in p["g"])) - 1.0) < 1e-9


def test_a_mesma_semente_da_a_mesma_noite():
    a = [sim.payload_da_epoca(e) for e in sim.NoiteSintetica(INICIO, 20, seed=3)]
    b = [sim.payload_da_epoca(e) for e in sim.NoiteSintetica(INICIO, 20, seed=3)]
    c = [sim.payload_da_epoca(e) for e in sim.NoiteSintetica(INICIO, 20, seed=4)]
    assert a == b and a != c


# =====================================================================
# 5. O sinal separa os estados — senão a demonstração não mostra nada
# =====================================================================
def test_vigilia_tem_mais_movimento_que_sono_quieto(noite):
    epocas, payloads = noite
    i_enmo, i_pfrac = 0, 5
    acordado = [p["f"] for e, p in zip(epocas, payloads) if e.estado == sim.ACORDADO and e.evento == "movimento"]
    quieto = [p["f"] for e, p in zip(epocas, payloads) if e.estado == sim.SONO and e.evento == ""]
    assert len(acordado) >= 20 and len(quieto) >= 100
    assert np.median([f[i_pfrac] for f in quieto]) == 0.0
    assert np.median([f[i_pfrac] for f in acordado]) > 0.02
    # Medido em 06/11 com esta semente: 3,6 mg contra 0,82 mg, 4,4 vezes. O
    # limiar é 3: o que importa é a separação, não o valor do modelo de sinal.
    assert np.median([f[i_enmo] for f in acordado]) > 3 * np.median([f[i_enmo] for f in quieto])


def test_virada_aparece_no_d_angulo_derivado_pelo_servidor(noite):
    """Passa pela derivação do SERVIDOR (`features_noite.derivar_noite`)."""
    epocas, payloads = noite
    entrada = []
    for p in payloads:
        e = {"instante": _instante(p["ts"]), "g": tuple(p["g"]), "fs": p["fs"]}
        e.update(zip(FEATURES_DO_DISPOSITIVO, p["f"]))
        entrada.append(e)
    saida, g_ref = features_noite.derivar_noite(entrada)
    d = [linha["d_angulo"] for linha in saida]
    assert d[0] is None and all(x is not None for x in d[1:])   # sem lacuna
    viradas = [e.indice for e in epocas if e.evento == "virada"]
    assert viradas, "a semente do teste precisa ter ao menos uma virada"
    for k in viradas:
        assert max(d[k], d[k + 1] if k + 1 < len(d) else 0.0) > 15.0, f"virada na época {k}"
    quietas = [k for k in range(1, len(epocas))
               if epocas[k].evento == "" and epocas[k - 1].evento == "" and epocas[k].estado == sim.SONO]
    assert max(d[k] for k in quietas) < 2.0


# =====================================================================
# 6. O envio: a regra de `firmware/nucleo/lote.h`
# =====================================================================
def _aceita_tudo(registro):
    def servidor(url, token, corpo):
        n = len(corpo["leituras"])
        registro.append(n)
        return 200, json.dumps({"aceitas": list(range(n)), "rejeitadas": [], "pendentes": []})
    return servidor


def _fila(n):
    return [{"i": i} for i in range(n)]


def test_413_divide_o_lote_ate_caber():
    tamanhos = []

    def servidor(url, token, corpo):
        n = len(corpo["leituras"])
        tamanhos.append(n)
        if n > 15:
            return 413, '{"error": "grande"}'
        return 200, json.dumps({"aceitas": list(range(n)), "rejeitadas": [], "pendentes": []})

    fila = _fila(100)
    r = sim.enviar_fila(fila, "u", "t", transporte=servidor, avisar=lambda *_: None)
    assert fila == [] and r.aceitas == 100 and r.divisoes == 2
    assert tamanhos[:3] == [60, 30, 15]


def test_pendentes_voltam_no_lote_seguinte_sem_contar_duas_vezes():
    vistos = []

    def servidor(url, token, corpo):
        ids = [x["i"] for x in corpo["leituras"]]
        vistos.extend(ids)
        n = len(ids)
        if len(vistos) == n:   # 1º lote: as 10 últimas ficam pendentes
            return 200, json.dumps({"aceitas": list(range(n - 10)), "rejeitadas": [],
                                    "pendentes": list(range(n - 10, n))})
        return 200, json.dumps({"aceitas": list(range(n)), "rejeitadas": [], "pendentes": []})

    fila = _fila(60)
    r = sim.enviar_fila(fila, "u", "t", transporte=servidor, avisar=lambda *_: None)
    assert fila == [] and r.aceitas == 60
    assert vistos[60:] == list(range(50, 60))


def test_rejeitadas_saem_da_fila_e_sao_contadas():
    def servidor(url, token, corpo):
        n = len(corpo["leituras"])
        return 200, json.dumps({"aceitas": list(range(1, n)), "rejeitadas": [{"indice": 0, "erro": "ruim"}],
                                "pendentes": []})

    fila = _fila(5)
    r = sim.enviar_fila(fila, "u", "t", transporte=servidor, avisar=lambda *_: None)
    assert fila == [] and (r.aceitas, r.rejeitadas, r.motivos_de_rejeicao) == (4, 1, ["ruim"])


def test_401_para_sem_tirar_nada_da_fila():
    fila = _fila(5)
    r = sim.enviar_fila(fila, "u", "t", transporte=lambda *a: (401, "{}"), avisar=lambda *_: None)
    assert len(fila) == 5 and "TOKEN" in r.interrompido


@pytest.mark.parametrize("status, corpo", [
    (503, json.dumps({"aceitas": [], "rejeitadas": [], "pendentes": [0, 1, 2]})),
    (500, "{}"),
    (-1, "sem rede"),
    (200, "isto nao e json"),
])
def test_falha_recua_com_espera_crescente_e_desiste(status, corpo):
    esperas = []
    fila = _fila(3)
    r = sim.enviar_fila(fila, "u", "t", transporte=lambda *a: (status, corpo),
                        dormir=esperas.append, max_recuos_seguidos=3, avisar=lambda *_: None)
    assert len(fila) == 3 and r.interrompido
    assert esperas == [2, 4, 8]


def test_recuo_zera_depois_de_um_lote_confirmado():
    respostas = iter([(503, "{}"), (200, None), (503, "{}"), (200, None)])
    esperas = []

    def servidor(url, token, corpo):
        status, texto = next(respostas)
        n = len(corpo["leituras"])
        return status, texto or json.dumps({"aceitas": list(range(n)), "rejeitadas": [], "pendentes": []})

    fila = _fila(61)
    sim.enviar_fila(fila, "u", "t", transporte=servidor, dormir=esperas.append, avisar=lambda *_: None)
    assert fila == [] and esperas == [2, 2]


# =====================================================================
# 7. A linha de comando
# =====================================================================
def test_sem_token_so_roda_a_seco(monkeypatch, capsys):
    monkeypatch.delenv("DORMIO_DEVICE_TOKEN", raising=False)
    assert sim.main(["--horas", "0.1"]) == 2
    assert sim.main(["--horas", "0.1", "--seco"]) == 0
    assert '"metodo": "pico-da-magnitude"' in capsys.readouterr().out


def test_noite_no_futuro_e_recusada_antes_de_gerar(monkeypatch, capsys):
    monkeypatch.delenv("DORMIO_DEVICE_TOKEN", raising=False)
    amanha = (datetime.now().astimezone() + timedelta(days=1)).isoformat()
    assert sim.main(["--seco", "--inicio", amanha]) == 2
    assert "futuro" in capsys.readouterr().out
