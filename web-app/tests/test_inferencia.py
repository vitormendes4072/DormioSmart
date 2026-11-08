"""A inferência do ML-INF no servidor (`inferencia.py`) e a rota `GET /api/inferencia`.

Quatro blocos:

  1. **O contrato do modelo.** O JSON que não for o `ml-inf-cabeca-v2` é
     recusado inteiro, e a cópia em `web-app/modelos/` é a de `ml/modelos/`.
  2. **O dourado da v2.** As duas noites de `ml/testes/fixtures/
     ml-inf-cabeca-v2-dourado.json` (gravadas pelo `ml/` com o `predict_proba`
     do scikit-learn) atravessam o caminho real do servidor — linha do banco,
     `epoca_da_linha`, `derivar_noite`, `inferir_janela` — e precisam bater a
     1e-12 na probabilidade e exatamente na classe. Este teste lê o arquivo sem
     importar nada do `ml/`, como `test_features_noite.py` faz com o dele.
  3. **As fronteiras.** Piso de 23, lacuna de 45 s, grade de 30 s a 32 Hz,
     coluna constante.
  4. **A rota.** O `/health`, os códigos e o dono vindo do JWT.

O Supabase é mockado; a consulta é a mesma de `/api/features`, cujo RLS está em
`tests/rls/test_rls_features.py`.
"""
import copy
import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from flask import Flask

import database
import inferencia as inf
from features_noite import DO_DISPOSITIVO
from routes import init_routes

RAIZ = Path(__file__).resolve().parents[2]
MODELO_ML = RAIZ / "ml" / "modelos" / "ml-inf-cabeca-v2.json"
MODELO_V1 = RAIZ / "ml" / "modelos" / "ml-inf-cabeca-v1.json"
DOURADO = RAIZ / "ml" / "testes" / "fixtures" / "ml-inf-cabeca-v2-dourado.json"


@pytest.fixture(scope="module")
def modelo():
    return inf.carregar_modelo()


@pytest.fixture(scope="module")
def dourado():
    return json.loads(DOURADO.read_text(encoding="utf-8"))


def linha_do_payload(p):
    """Uma linha de `sleep_data` como a ingestão a grava a partir do payload."""
    return dict(zip(DO_DISPOSITIVO, p["f"]), captured_at=p["ts"],
                epoca_segundos=p["epoca_s"], g_x=p["g"][0], g_y=p["g"][1],
                g_z=p["g"][2], fs_features=float(p["fs"]))


def linhas_da_noite(dourado, nome):
    return [linha_do_payload(p) for p in dourado["noites"][nome]["payloads"]]


# --- 1. o contrato do modelo -------------------------------------------------

def test_a_copia_do_servidor_e_a_do_ml_byte_a_byte():
    """O pacote da Vercel só leva `web-app/`; a cópia não pode divergir."""
    def sha(p):
        return hashlib.sha256(p.read_bytes()).hexdigest()
    assert sha(inf.CAMINHO_MODELO) == sha(MODELO_ML)


def test_o_modelo_publicado_cumpre_o_contrato(modelo):
    assert modelo["versao"] == "ml-inf-cabeca-v2"
    assert len(modelo["coeficientes"]) == 184
    assert modelo["colunas_contexto"][88:96] == [f"{n}__+0" for n in inf.ORDEM_FEATURES]


def test_o_modelo_v1_e_recusado():
    """Escala global, seis features e sem contexto: a configuração que não transferiu."""
    with pytest.raises(inf.ModeloInvalido):
        inf.carregar_modelo(MODELO_V1)


def _adulterar(modelo, mexer):
    m = copy.deepcopy(modelo)
    mexer(m)
    return m


@pytest.mark.parametrize("descricao, mexer", [
    ("duas colunas trocadas", lambda m: m["colunas_contexto"].__setitem__(
        slice(0, 2), m["colunas_contexto"][1::-1])),
    ("features fora de ordem", lambda m: m["features"].reverse()),
    ("escala global", lambda m: m.__setitem__("medias", [0.0] * 8)),
    ("183 coeficientes", lambda m: m["coeficientes"].pop()),
    ("coeficiente NaN", lambda m: m["coeficientes"].__setitem__(5, math.nan)),
    ("piso 22", lambda m: m["normalizacao"].__setitem__("minimo_epocas_validas", 22)),
    ("ddof 0", lambda m: m["normalizacao"].__setitem__("ddof", 0)),
    ("lacuna 60 s", lambda m: m["contexto"].__setitem__("quebra_servidor_s", 60.0)),
    ("contexto ±10", lambda m: m["contexto"].__setitem__("vizinhas", 10)),
    ("empate como sono", lambda m: m.__setitem__("comparacao", ">=")),
    ("outra versao", lambda m: m.__setitem__("versao", "ml-inf-cabeca-v3")),
])
def test_modelo_adulterado_e_recusado(modelo, descricao, mexer):
    with pytest.raises(inf.ModeloInvalido):
        inf.validar_modelo(_adulterar(modelo, mexer))


def test_falha_ao_carregar_nao_levanta_e_nao_fica_em_cache(monkeypatch, tmp_path):
    monkeypatch.setattr(inf, "_cache", {})
    monkeypatch.setattr(inf, "CAMINHO_MODELO", tmp_path / "ausente.json")
    assert inf.modelo_carregado() is None
    monkeypatch.setattr(inf, "CAMINHO_MODELO", MODELO_ML)
    assert inf.modelo_carregado()["versao"] == "ml-inf-cabeca-v2"


# --- 2. o dourado da v2 ------------------------------------------------------

@pytest.mark.parametrize("nome, segmentos", [("continua", 1), ("lacuna", 2)])
def test_dourado_reproduz_o_predict_proba_do_ml(modelo, dourado, nome, segmentos):
    noite = dourado["noites"][nome]
    tol = dourado["tolerancia_absoluta"]
    assert tol == 1e-12
    r = inf.inferir_janela(linhas_da_noite(dourado, nome), modelo)
    assert r["n_segmentos"] == segmentos
    assert r["excluidas"] == {"fora_da_grade": 0, "invalidas": 0}
    assert [e["instante"] for e in r["epocas"]] == [f["instante"] for f in noite["features_servidor"]]
    for e, p, c in zip(r["epocas"], noite["probabilidades"], noite["classes"], strict=True):
        assert abs(e["prob_sono"] - p) <= tol
        assert e["classe"] == c


def test_casos_do_limiar_incluem_o_empate_como_vigilia(modelo, dourado):
    abaixo, empate, acima = dourado["limiar"]
    for caso in (abaixo, empate, acima):
        z = inf.pontuar(modelo, caso["contexto"])
        assert abs(inf._sigmoide(z) - caso["probabilidade"]) <= dourado["tolerancia_absoluta"]
        assert int(z > 0) == caso["classe"]
    assert inf.pontuar(modelo, empate["contexto"]) == 0 and empate["classe"] == 0


# --- 3. as fronteiras --------------------------------------------------------

def test_piso_de_23_epocas_validas(modelo, dourado):
    linhas = linhas_da_noite(dourado, "continua")
    assert len(inf.inferir_janela(linhas[:23], modelo)["epocas"]) == 23
    with pytest.raises(inf.AbaixoDoPiso) as e:
        inf.inferir_janela(linhas[:22], modelo)
    assert (e.value.validas, e.value.minimo) == (22, 23)


def test_janela_vazia_fica_abaixo_do_piso(modelo):
    with pytest.raises(inf.AbaixoDoPiso) as e:
        inf.inferir_janela([], modelo)
    assert e.value.validas == 0


def test_epocas_fora_da_grade_saem_antes_da_derivacao(modelo, dourado):
    """60 s ou 50 Hz descrevem outra coisa; nem entram no `g_ref`."""
    linhas = linhas_da_noite(dourado, "continua")[:100]
    intrusas = [dict(linhas[10], epoca_segundos=60, g_x=1.0, g_y=0.0, g_z=0.0,
                     captured_at="2026-11-01T23:05:15+00:00"),
                dict(linhas[20], fs_features=50.0, g_x=0.0, g_y=1.0, g_z=0.0,
                     captured_at="2026-11-01T23:10:15+00:00")]
    limpo = inf.inferir_janela(linhas, modelo)
    sujo = inf.inferir_janela(linhas + intrusas, modelo)
    assert sujo["excluidas"]["fora_da_grade"] == 2
    assert sujo["epocas"] == limpo["epocas"]


def _linhas_com_intervalos(segundos):
    inicio = datetime(2026, 11, 1, 23, tzinfo=timezone.utc)
    linhas = []
    for i, s in enumerate(segundos):
        angulo = 0.3 * math.sin(i / 3)
        linhas.append(dict(
            {n: 0.01 + 0.001 * ((i * 7 + k) % 5) for k, n in enumerate(DO_DISPOSITIVO)},
            captured_at=(inicio + timedelta(seconds=s)).isoformat(), epoca_segundos=30,
            g_x=math.sin(angulo), g_y=0.0, g_z=math.cos(angulo), fs_features=32.0))
    return linhas


@pytest.mark.parametrize("intervalo, segmentos", [(30, 1), (45, 1), (45.001, 2), (60, 2)])
def test_lacuna_acima_de_45_s_abre_segmento(modelo, intervalo, segmentos):
    instantes = [30 * i for i in range(15)]
    instantes += [instantes[-1] + intervalo + 30 * i for i in range(15)]
    r = inf.inferir_janela(_linhas_com_intervalos(instantes), modelo)
    assert r["n_segmentos"] == segmentos


def test_contexto_nao_atravessa_a_lacuna(modelo):
    """A primeira época depois da lacuna só enxerga o próprio segmento."""
    instantes = [30 * i for i in range(30)] + [30 * 29 + 3600 + 30 * i for i in range(30)]
    linhas = _linhas_com_intervalos(instantes)
    junto = inf.inferir_janela(linhas, modelo)["epocas"]
    # A normalização é da janela inteira; só o empilhamento para na lacuna.
    # A referência monta o contexto da época 30 à mão, preso ao segmento 30..59.
    X =[[inf._valor(e, n) for n in inf.ORDEM_FEATURES]
         for e in inf.derivar_noite([inf.epoca_da_linha(x) for x in linhas])[0]]
    Z = inf._zscore(X, 1, 1e-9, 1.0)
    i = 30
    contexto = [v for d in range(-11, 12) for v in Z[max(30, min(i + d, 59))]]
    assert junto[i]["prob_sono"] == inf._sigmoide(inf.pontuar(modelo, contexto))


def test_d_angulo_nulo_entra_como_zero(modelo, dourado):
    """Sem a conversão, a primeira época (e a da lacuna) viraria inválida."""
    r = inf.inferir_janela(linhas_da_noite(dourado, "lacuna"), modelo)
    assert r["excluidas"]["invalidas"] == 0 and len(r["epocas"]) == 959


def test_coluna_constante_nao_divide_por_zero(modelo):
    instantes = [30 * i for i in range(40)]
    linhas = [dict({n: 0.02 for n in DO_DISPOSITIVO}, captured_at=(
        datetime(2026, 11, 1, 23, tzinfo=timezone.utc) + timedelta(seconds=s)).isoformat(),
        epoca_segundos=30, g_x=0.0, g_y=0.0, g_z=1.0, fs_features=32.0) for s in instantes]
    r = inf.inferir_janela(linhas, modelo)
    assert all(math.isfinite(e["prob_sono"]) for e in r["epocas"])
    assert len({e["prob_sono"] for e in r["epocas"]}) == 1


# --- 4. a rota ---------------------------------------------------------------

_USUARIO = "00000000-0000-0000-0000-0000000000aa"
_DEVICE = "00000000-0000-0000-0000-0000000000d1"
_JANELA = {"device": _DEVICE, "desde": "2026-11-01T22:00:00Z", "ate": "2026-11-02T08:00:00Z"}


def _client():
    app = Flask(__name__)
    init_routes(app)
    app.testing = True
    return app.test_client()


def _get(params, linhas):
    with patch.object(database.db, "validar_token_de_usuario", return_value=_USUARIO), \
         patch.object(database.db, "get_features_do_usuario", return_value=linhas) as consulta:
        resp = _client().get("/api/inferencia", query_string=params,
                             headers={"Authorization": "Bearer jwt-de-teste"})
    return resp, consulta


def test_rota_devolve_a_noite_classificada(dourado):
    resp, consulta = _get(_JANELA, linhas_da_noite(dourado, "lacuna"))
    corpo = resp.get_json()
    assert resp.status_code == 200
    assert corpo["modelo"]["versao"] == "ml-inf-cabeca-v2"
    assert corpo["modelo"]["treino"] == {"dataset": "Wearanize+ OA", "braco": "cabeca",
                                         "n_participantes": 92}
    assert corpo["classes"] == {"0": "vigilia", "1": "sono"}
    assert corpo["normalizacao"] == "janela pedida" and corpo["aviso"]
    assert corpo["n_segmentos"] == 2 and len(corpo["epocas"]) == 959
    assert set(corpo["epocas"][0]) == {"instante", "prob_sono", "classe"}
    noite = dourado["noites"]["lacuna"]
    assert [e["classe"] for e in corpo["epocas"]] == noite["classes"]
    assert max(abs(e["prob_sono"] - p) for e, p in zip(corpo["epocas"], noite["probabilidades"])) <= 1e-12
    args = consulta.call_args[0]
    assert args[1] == _USUARIO, "o dono vem do JWT, nunca da query string"
    assert args[2] == _DEVICE


def test_abaixo_do_piso_e_422_com_as_contagens(dourado):
    resp, _ = _get(_JANELA, linhas_da_noite(dourado, "continua")[:10])
    assert resp.status_code == 422
    assert resp.get_json() == {"error": "epocas insuficientes na janela",
                               "epocas_validas": 10, "minimo": 23}


@pytest.mark.parametrize("faltando", ["device", "desde", "ate"])
def test_janela_e_obrigatoria(faltando):
    resp, consulta = _get({k: v for k, v in _JANELA.items() if k != faltando}, [])
    assert resp.status_code == 400 and faltando in resp.get_json()["error"]
    consulta.assert_not_called()


def test_janela_acima_de_24_h_e_recusada():
    resp, consulta = _get(dict(_JANELA, ate="2026-11-03T08:00:00Z"), [])
    assert resp.status_code == 400
    consulta.assert_not_called()


def test_falha_da_consulta_e_503():
    resp, _ = _get(_JANELA, None)
    assert resp.status_code == 503


def test_modelo_indisponivel_e_503_sem_consultar():
    with patch.object(inf, "modelo_carregado", return_value=None):
        resp, consulta = _get(_JANELA, [])
    assert resp.status_code == 503 and resp.get_json()["error"] == "modelo indisponivel"
    consulta.assert_not_called()


def test_sem_jwt_e_401():
    assert _client().get("/api/inferencia", query_string=_JANELA).status_code == 401


def test_health_informa_o_modelo_sem_mudar_o_codigo():
    with patch.object(database.db, "verificar_conexao", return_value=(True, None)):
        assert _client().get("/health").get_json()["modelo"] == "ml-inf-cabeca-v2"
        with patch.object(inf, "modelo_carregado", return_value=None):
            resp = _client().get("/health")
    assert resp.status_code == 200 and resp.get_json()["modelo"] == "indisponivel"
