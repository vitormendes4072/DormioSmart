"""A derivação do servidor (DATA-07b (e)) e a rota `GET /api/features`.

Três blocos:

  1. **Paridade com o `ml/`.** `features_noite.py` reescreve em Python puro a
     `features_inter_epoca` do pipeline. O dourado da fronteira B
     (`ml/testes/vetor_dourado_sequencias.json`) foi gravado pelo `ml/`, e este
     teste o lê sem importar nada do `ml/` — é o percurso que o arquivo promete
     servir (ver `test_o_arquivo_de_sequencias_basta_para_o_servidor` lá).
  2. **O buraco.** A diferença deliberada em relação ao `ml/`.
  3. **A rota.** Parâmetros obrigatórios, a janela máxima, a falha de consulta
     como 503 e o dono vindo do JWT.

O Supabase é mockado; o RLS das colunas novas está em `tests/rls/test_rls_features.py`.
"""
import inspect
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from flask import Flask

import database
import features_noite as fn
from routes import init_routes

DOURADO = Path(__file__).resolve().parents[2] / "ml" / "testes" / "vetor_dourado_sequencias.json"

# Régua da paridade, entre piso e teto medidos em 30/10:
#   g_ref    piso 5,6e-16 (ordem de soma de Python puro vs numpy) -> 1e-12, a
#            régua "exato" do próprio arquivo;
#   ângulos  piso 2,4e-10 grau: o arccos é mal-condicionado perto de 0 e
#            amplifica a diferença de 1e-16 no cosseno. A régua "exato" (1e-12)
#            está ABAIXO do piso e reprovaria a implementação correta; 1e-6 grau
#            fica 4 000x acima do piso e muito abaixo de qualquer sabotagem
#            (radianos no lugar de graus, média no lugar da mediana), que move
#            graus inteiros.
TOL_G_REF = 1e-12
TOL_ANGULO_GRAUS = 1e-6


def _dourado():
    return json.loads(DOURADO.read_text(encoding="utf-8"))


# --- 1. paridade com o ml/ ---------------------------------------------------

def test_a_regua_do_arquivo_e_a_que_este_teste_respeita_para_g_ref():
    assert _dourado()["tolerancias"]["exato"] == TOL_G_REF


@pytest.mark.parametrize("seq", _dourado()["sequencias"], ids=lambda s: s["nome"])
def test_paridade_com_o_dourado_das_sequencias(seq):
    inc, dang, ref = fn.features_inter_epoca([tuple(g) for g in seq["g_por_epoca"]])
    esperado = seq["esperado"]
    assert len(inc) == len(dang) == seq["n_epocas"]
    for a, b in zip(ref, esperado["g_ref"]):
        assert abs(a - b) <= TOL_G_REF, f"g_ref diverge {abs(a - b):.2e}"
    for nome, obtido in (("inclinacao_rel", inc), ("d_angulo", dang)):
        pior = max(abs(a - b) for a, b in zip(obtido, esperado[nome]))
        assert pior <= TOL_ANGULO_GRAUS, f"{nome} diverge {pior:.2e} grau"


def test_mediana_geometrica_e_robusta_a_uma_virada():
    """Nove épocas paradas e uma virada: a referência fica com as nove. A
    média puxaria para a virada — é o sabotador `media_no_lugar_da_mediana`."""
    gs = [(0.0, 0.0, 1.0)] * 9 + [(1.0, 0.0, 0.0)]
    ref = fn.direcao_referencia(gs)
    assert fn.angulo_graus(ref, (0.0, 0.0, 1.0)) < 0.5


# --- 2. o buraco -------------------------------------------------------------

def _epoca(segundos, g, **extras):
    base = datetime(2026, 10, 30, 23, 0, tzinfo=timezone.utc)
    e = {"instante": base + timedelta(seconds=segundos), "g": g, "fs": 32.0}
    for nome in fn.DO_DISPOSITIVO:
        e[nome] = extras.get(nome, 0.01)
    return e


def test_d_angulo_e_none_na_primeira_e_depois_de_um_buraco():
    z = (0.0, 0.0, 1.0)
    girado = (math.sin(math.radians(30)), 0.0, math.cos(math.radians(30)))
    epocas = [_epoca(0, z), _epoca(30, z), _epoca(60, girado),
              _epoca(3660, girado), _epoca(3690, z)]
    saida, _ = fn.derivar_noite(epocas)
    d = [e["d_angulo"] for e in saida]
    assert d[0] is None, "a primeira nao tem anterior"
    assert d[1] == pytest.approx(0.0, abs=1e-9)
    assert d[2] == pytest.approx(30.0, abs=1e-9)
    assert d[3] is None, "uma hora sem leitura nao e uma virada em 30 s"
    assert d[4] == pytest.approx(30.0, abs=1e-9)


def test_sem_buraco_e_identico_ao_ml():
    seq = next(s for s in _dourado()["sequencias"] if s["nome"] == "deriva_lenta")
    epocas = [_epoca(30 * i, tuple(g)) for i, g in enumerate(seq["g_por_epoca"])]
    saida, ref = fn.derivar_noite(epocas)
    assert [e["d_angulo"] for e in saida][1:] == pytest.approx(
        seq["esperado"]["d_angulo"][1:], abs=TOL_ANGULO_GRAUS)
    assert ref == pytest.approx(seq["esperado"]["g_ref"], abs=TOL_G_REF)


def test_ordena_pelo_instante_e_nao_pela_chegada():
    z, x = (0.0, 0.0, 1.0), (1.0, 0.0, 0.0)
    saida, _ = fn.derivar_noite([_epoca(60, x), _epoca(0, z), _epoca(30, z)])
    assert [e["instante"][-14:-6] for e in saida] == ["23:00:00", "23:00:30", "23:01:00"]
    assert saida[2]["d_angulo"] == pytest.approx(90.0, abs=1e-9)


def test_cada_epoca_traz_as_oito_pelo_nome():
    saida, _ = fn.derivar_noite([_epoca(0, (0.0, 0.0, 1.0), zcr=0.42)])
    assert set(fn.ORDEM_FEATURES) <= set(saida[0]) and saida[0]["zcr"] == 0.42


@pytest.mark.parametrize("texto", [
    "2026-10-30T23:00:00+00:00", "2026-10-30T23:00:00Z", "2026-10-30T23:00:00.12+00:00",
    "2026-10-30T23:00:00.123456+00:00",
])
def test_instante_do_banco_aceita_o_que_o_postgrest_devolve(texto):
    assert fn.instante_do_banco(texto).tzinfo is not None


def test_linha_sem_vetor_ou_sem_captured_at_fica_de_fora():
    linha = {"captured_at": "2026-10-30T23:00:00+00:00", "fs_features": None}
    assert fn.epoca_da_linha(linha) is None
    linha = dict({n: 0.1 for n in fn.DO_DISPOSITIVO}, captured_at=None, fs_features=32.0,
                 g_x=0.0, g_y=0.0, g_z=1.0)
    assert fn.epoca_da_linha(linha) is None


# --- 3. a rota ---------------------------------------------------------------

_USUARIO = "00000000-0000-0000-0000-0000000000aa"
_DEVICE = "00000000-0000-0000-0000-0000000000d1"
_JANELA = {"device": _DEVICE, "desde": "2026-10-30T22:00:00Z", "ate": "2026-10-31T07:00:00Z"}


def _client():
    app = Flask(__name__)
    init_routes(app)
    app.testing = True
    return app.test_client()


def _linha(segundos, g=(0.0, 0.0, 1.0)):
    base = datetime(2026, 10, 30, 23, 0, tzinfo=timezone.utc)
    return dict({n: 0.01 for n in fn.DO_DISPOSITIVO},
                captured_at=(base + timedelta(seconds=segundos)).isoformat(),
                epoca_segundos=30, g_x=g[0], g_y=g[1], g_z=g[2], fs_features=32.0)


def _get(params, linhas):
    with patch.object(database.db, "validar_token_de_usuario", return_value=_USUARIO), \
         patch.object(database.db, "get_features_do_usuario", return_value=linhas) as consulta:
        resp = _client().get("/api/features", query_string=params,
                             headers={"Authorization": "Bearer jwt-de-teste"})
    return resp, consulta


def test_rota_devolve_as_oito_e_o_g_ref():
    resp, consulta = _get(_JANELA, [_linha(0), _linha(30), _linha(60)])
    corpo = resp.get_json()
    assert resp.status_code == 200
    assert corpo["ordem_features"] == list(fn.ORDEM_FEATURES)
    assert len(corpo["epocas"]) == 3 and corpo["g_ref"] == pytest.approx([0, 0, 1])
    assert corpo["epocas"][0]["d_angulo"] is None
    args = consulta.call_args[0]
    assert args[1] == _USUARIO, "o dono vem do JWT, nunca da query string"
    assert args[2] == _DEVICE


@pytest.mark.parametrize("faltando", ["device", "desde", "ate"])
def test_janela_e_obrigatoria(faltando):
    params = {k: v for k, v in _JANELA.items() if k != faltando}
    resp, consulta = _get(params, [])
    assert resp.status_code == 400 and faltando in resp.get_json()["error"]
    consulta.assert_not_called()


def test_janela_acima_de_24_h_e_recusada():
    resp, consulta = _get(dict(_JANELA, ate="2026-11-01T07:00:00Z"), [])
    assert resp.status_code == 400
    consulta.assert_not_called()


def test_instante_sem_fuso_e_recusado():
    resp, _ = _get(dict(_JANELA, desde="2026-10-30T22:00:00", ate="2026-10-31T07:00:00"), [])
    assert resp.status_code == 400


def test_falha_da_consulta_e_503_e_nao_noite_vazia():
    """Lista vazia pareceria "noite sem nenhuma época com vetor"."""
    resp, _ = _get(_JANELA, None)
    assert resp.status_code == 503


def test_sem_jwt_e_401():
    resp = _client().get("/api/features", query_string=_JANELA)
    assert resp.status_code == 401


def test_a_consulta_usa_o_cliente_do_usuario():
    """O guarda de `test_privilegio_minimo` confia no NOME do método; este
    confere que o método de fato monta o cliente com o JWT."""
    fonte = inspect.getsource(database.Database.get_features_do_usuario)
    assert "self.cliente_do_usuario(jwt)" in fonte and '.eq("user_id", usuario_id)' in fonte
