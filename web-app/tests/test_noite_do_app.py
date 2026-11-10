"""Uma noite gravada pelo app Android, do aparelho ao modelo (APP-02, etapa 3).

`tests/fixtures/noite_do_app_emulador.jsonl` é o arquivo da noite exatamente
como o `ServicoDaNoite` o gravou no emulador (Pixel 6, Android 37): uma linha
por época, montada pelo núcleo do firmware (`coletor_celular.h`) a partir do
acelerômetro virtual. Nada foi editado depois.

O que este teste prova, sem login e sem banco:

  1. cada linha passa pela validação REAL da ingestão (a mesma do `POST
     /api/data` e do lote), com o vetor `f`/`g`/`fs`;
  2. a noite entra pelo `POST /api/data/lote` no caminho por sessão, que é o
     do app, em lotes de 60, tudo aceito;
  3. as linhas, convertidas como a ingestão as grava, passam pela
     `/api/inferencia` e saem classificadas.

O que ele NÃO prova: que a classificação está certa. O acelerômetro do
emulador é constante (o aparelho virtual "parado na mesa"), então a noite é
plana. É uma prova de formato e de caminho, não de acurácia — essa é do
`VAL-02`, com uma noite de verdade.
"""
import json
import math
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

import database
import dispositivos
import inferencia
import lote
from routes import init_routes
from validacao import validar_leitura

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "noite_do_app_emulador.jsonl"


@pytest.fixture(scope="module")
def noite():
    linhas = [l for l in FIXTURE.read_text(encoding="utf-8").splitlines() if l.strip()]
    return [json.loads(l) for l in linhas]


def test_a_fixture_e_uma_noite_de_verdade_do_emulador(noite):
    # 15 min de noite: ~30 épocas de 30 s, consecutivas.
    assert len(noite) >= inferencia._NORMALIZACAO["minimo_epocas_validas"]
    for p in noite:
        assert p["epoca_s"] == 30 and p["fs"] == 32 and p["amostras"] == 960
        assert len(p["f"]) == 6 and len(p["g"]) == 3


@pytest.mark.parametrize("indice", range(3))
def test_cada_epoca_passa_pela_validacao_real(noite, indice):
    # Três amostras explícitas no relatório; a varredura completa vem abaixo.
    conteudo, erro = validar_leitura(dict(noite[indice]))
    assert erro is None, erro


def test_todas_as_epocas_passam_pela_validacao_real(noite):
    erros = [(i, validar_leitura(dict(p))[1]) for i, p in enumerate(noite)]
    assert [e for e in erros if e[1]] == []


def _client():
    app = Flask(__name__)
    init_routes(app)
    app.testing = True
    return app.test_client()


@pytest.fixture(scope="module")
def gravadas(noite):
    """A noite pelo `POST /api/data/lote` da sessão, em lotes de 60.

    Devolve o que a rota entregou à gravação — a linha de `sleep_data`, já com
    as colunas nomeadas do vetor —, e as respostas de cada lote.
    """
    gravadas, respostas = [], []
    with patch.object(database.db, "validar_token_de_usuario", return_value="user-ana"),          patch.object(database.db, "cliente_do_usuario", return_value=MagicMock()),          patch.object(dispositivos, "buscar_do_dono", return_value={"id": "dev-celular"}),          patch.object(database.db, "registrar_leitura_da_sessao",
                      side_effect=lambda jwt, d, leitura, cliente=None: gravadas.append(leitura) or len(gravadas)):
        for ini in range(0, len(noite), lote.MAX_LEITURAS_POR_LOTE):
            parte = noite[ini:ini + lote.MAX_LEITURAS_POR_LOTE]
            resp = _client().post("/api/data/lote",
                                  json={"device_id": "dev-celular", "leituras": parte},
                                  headers={"Authorization": "Bearer jwt-da-ana"})
            respostas.append((resp.status_code, resp.get_json(), len(parte)))
    return gravadas, respostas


def test_a_noite_entra_pelo_lote_da_sessao_em_lotes_de_60(noite, gravadas):
    linhas, respostas = gravadas
    for status, corpo, n in respostas:
        assert status == 200
        assert corpo["aceitas"] == list(range(n))
        assert corpo["rejeitadas"] == [] and corpo["pendentes"] == []
    assert len(linhas) == len(noite)
    # O vetor chega ao banco, coluna por coluna, com o nome de cada feature.
    nomes = ("enmo_media", "enmo_desvio", "enmo_max", "mag_din_media", "zcr", "p_frac")
    for linha, p in zip(linhas, noite):
        assert [linha[n] for n in nomes] == pytest.approx(p["f"], abs=0, rel=0)
        assert (linha["g_x"], linha["g_y"], linha["g_z"]) == pytest.approx(tuple(p["g"]), abs=0, rel=0)
        assert linha["fs_features"] == 32 and linha["epoca_segundos"] == 30


def test_a_noite_gravada_passa_pela_inferencia(gravadas):
    """As linhas EXATAS que a rota gravou, pelo modelo do ML-INF."""
    linhas, _ = gravadas
    modelo = inferencia.carregar_modelo()
    r = inferencia.inferir_janela(linhas, modelo)
    assert len(r["epocas"]) == len(linhas)
    assert r["excluidas"] == {"fora_da_grade": 0, "invalidas": 0}
    assert r["n_segmentos"] == 1
    assert all(math.isfinite(e["prob_sono"]) and e["classe"] in (0, 1) for e in r["epocas"])
