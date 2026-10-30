"""O vetor de características na ingestão — `f`, `g` e `fs` (DATA-07b, contrato §2.6).

Três promessas, cada uma com o seu bloco:

  1. **Ausente continua sendo o caso normal.** Dispositivo antigo em campo é
     dispositivo válido: nenhuma regra nova pode recusar um payload sem `f`.
  2. **Presente, vale a "Validação prevista" do §2.6 inteira**, e qualquer
     falha recusa a leitura com 400.
  3. **O que passa chega à gravação com o NOME de cada feature**, nos dois
     caminhos (`/api/data` e `/api/data/lote`). A ordem de `f` vira nome uma
     vez, em `colunas_de_features`, e é aí que um vetor trocado seria pego.

O Supabase é sempre mockado; a gravação de verdade, com a migração 010, é
conferida em `tests/rls/test_rls_features.py`.
"""
from unittest.mock import patch

import pytest
from flask import Flask

import database
from device_auth import TOKEN_HEADER
from routes import init_routes
from validacao import COLUNAS_DE_FEATURES, colunas_de_features, validar_leitura

_DEVICE = {"id": "dev-uuid-1", "user_id": "user-uuid-1", "revoked_at": None}
_AUTH = {TOKEN_HEADER: "token-de-teste"}

_BASE = {"ax": 0.10, "ay": 0.20, "az": 9.80, "t": 32.0, "total": 9.80,
         "status": "Repouso", "epoca_s": 30, "metodo": "pico-da-magnitude",
         "amostras": 960}
_F = [0.000123, 0.0021, 0.0876, 0.0244, 0.4171, 0.0125]
_G = [0.6, 0.0, 0.8]
_COM_F = dict(_BASE, f=_F, g=_G, fs=32)


def _client():
    app = Flask(__name__)
    init_routes(app)
    app.testing = True
    return app.test_client()


# --- 1. ausente é o caso normal ---------------------------------------------

def test_sem_f_continua_valido():
    content, erro = validar_leitura(dict(_BASE))
    assert erro is None and content is not None


def test_amostra_instantanea_sem_f_continua_valida():
    """O ESP32 de hoje: sem época, sem método, sem `f`."""
    leitura = {"ax": 0.1, "ay": 0.2, "az": 9.8, "total": 9.8, "status": "Repouso"}
    assert validar_leitura(leitura)[1] is None


def test_com_f_valido_passa():
    assert validar_leitura(dict(_COM_F))[1] is None


# --- 2. presente, a validação do §2.6 inteira -------------------------------

@pytest.mark.parametrize("faltando", ["f", "g", "fs"])
def test_os_tres_vem_juntos(faltando):
    leitura = dict(_COM_F)
    del leitura[faltando]
    content, erro = validar_leitura(leitura)
    # A mensagem inteira, e não só o nome do campo: "g" e "fs" aparecem em
    # quase toda recusa, e conferir a substring deixaria passar a ausência da
    # regra (a recusa viria depois, por outro motivo).
    assert content is None and erro == f"campos f, g e fs vem juntos: falta {faltando}"


def test_f_exige_epoca():
    leitura = {k: v for k, v in _COM_F.items() if k not in ("epoca_s", "metodo", "amostras")}
    assert validar_leitura(leitura) == (None, "campo f exige epoca_s")


@pytest.mark.parametrize("f", [_F[:5], _F + [0.1], "0,1,2,3,4,5", {"enmo_media": 0.1}])
def test_f_com_forma_errada(f):
    content, erro = validar_leitura(dict(_COM_F, f=f))
    assert content is None and "lista de 6" in erro


@pytest.mark.parametrize("g", [[0.6, 0.8], [0.6, 0.0, 0.8, 0.0], "0.6,0,0.8"])
def test_g_com_forma_errada(g):
    content, erro = validar_leitura(dict(_COM_F, g=g))
    assert content is None and "lista de 3" in erro


@pytest.mark.parametrize("indice,valor,nome", [
    (0, 1.5, "enmo_media"),       # faixa 0 a 1
    (0, -0.001, "enmo_media"),    # ENMO é retificado: nunca negativo
    (2, 16.5, "enmo_max"),        # faixa 0 a 16
    (3, 2.3, "mag_din_media"),    # faixa 0 a 2
    (4, 1.01, "zcr"),
    (5, -0.1, "p_frac"),
])
def test_cada_feature_tem_a_sua_faixa(indice, valor, nome):
    f = list(_F)
    f[indice] = valor
    content, erro = validar_leitura(dict(_COM_F, f=f))
    assert content is None and f"f.{nome}" in erro


@pytest.mark.parametrize("valor", [float("nan"), float("inf"), True, "0.1", None])
def test_feature_nao_numerica_e_recusada(valor):
    f = list(_F)
    f[1] = valor
    content, erro = validar_leitura(dict(_COM_F, f=f))
    assert content is None and "f.enmo_desvio" in erro


def test_enmo_max_admite_ate_16_g():
    """Não é descuido do contrato: é um máximo, e o fundo de escala é ±8 g."""
    f = list(_F)
    f[2] = 12.9
    assert validar_leitura(dict(_COM_F, f=f))[1] is None


def test_g_tem_de_ser_unitario():
    content, erro = validar_leitura(dict(_COM_F, g=[0.6, 0.0, 0.9]))
    assert content is None and "unitario" in erro


def test_g_dentro_da_tolerancia_de_coerencia_passa():
    # ‖g‖ = 1,0005: dentro de 1 ± 1e-3, que é o que a quantização tolera.
    assert validar_leitura(dict(_COM_F, g=[0.6003, 0.0, 0.8004]))[1] is None


def test_componente_de_g_fora_de_menos_um_a_um():
    content, erro = validar_leitura(dict(_COM_F, g=[1.2, 0.0, 0.0]))
    assert content is None and "g.x" in erro


@pytest.mark.parametrize("fs", [0, -32, 250, float("nan"), "32", True])
def test_fs_fora_da_faixa(fs):
    content, erro = validar_leitura(dict(_COM_F, fs=fs))
    assert content is None and "fs" in erro


# --- 3. o que passa chega à gravação com nome -------------------------------

def test_colunas_tem_nome_de_feature_e_nao_posicao():
    colunas = colunas_de_features(dict(_COM_F))
    assert colunas["enmo_media"] == _F[0]
    assert colunas["p_frac"] == _F[5]
    assert (colunas["g_x"], colunas["g_y"], colunas["g_z"]) == tuple(_G)
    assert colunas["fs_features"] == 32.0
    assert set(colunas) == set(COLUNAS_DE_FEATURES) and len(COLUNAS_DE_FEATURES) == 10


def test_sem_f_as_dez_colunas_vao_nulas():
    """A restrição "tudo ou nada" da migração 010 exige exatamente isso."""
    assert colunas_de_features(dict(_BASE)) == {c: None for c in COLUNAS_DE_FEATURES}


def test_api_data_grava_as_features_pelo_token():
    with patch.object(database.db, "get_device_by_token_hash", return_value=_DEVICE), \
         patch.object(database.db, "registrar_leitura", return_value=True) as gravar:
        resp = _client().post("/api/data", json=_COM_F, headers=_AUTH)
    assert resp.status_code == 201
    payload = gravar.call_args[0][1]
    assert payload["mag_din_media"] == _F[3] and payload["zcr"] == _F[4]
    assert payload["g_z"] == _G[2] and payload["fs_features"] == 32.0
    assert "user_id" not in payload, "o dono nunca vem do Python (SEC-06)"


def test_api_data_recusa_f_invalido_sem_gravar():
    with patch.object(database.db, "get_device_by_token_hash", return_value=_DEVICE), \
         patch.object(database.db, "registrar_leitura") as gravar:
        resp = _client().post("/api/data", json=dict(_COM_F, g=[1.0, 1.0, 0.0]), headers=_AUTH)
    assert resp.status_code == 400
    gravar.assert_not_called()


def test_lote_grava_features_e_rejeita_so_a_invalida():
    lote = {"leituras": [_COM_F, dict(_COM_F, fs=0), dict(_BASE)]}
    with patch.object(database.db, "get_device_by_token_hash", return_value=_DEVICE), \
         patch.object(database.db, "registrar_leitura", return_value=True) as gravar:
        resp = _client().post("/api/data/lote", json=lote, headers=_AUTH)
    corpo = resp.get_json()
    assert resp.status_code == 200
    assert corpo["aceitas"] == [0, 2] and [r["indice"] for r in corpo["rejeitadas"]] == [1]
    gravados = [c[0][1] for c in gravar.call_args_list]
    assert gravados[0]["enmo_max"] == _F[2]
    assert gravados[1]["enmo_max"] is None, "a leitura sem f grava as colunas nulas"
