"""Contrato público da ML-INF e paridade do JSON com os dourados do sklearn."""
from datetime import datetime
import json
from math import exp, fsum, isfinite
from pathlib import Path
import sys

import numpy as np
import pytest
from sklearn.preprocessing import StandardScaler

from experimentos.ml_inf import probabilidade_loso
from src.features import FEATURES_DO_DISPOSITIVO


ML = Path(__file__).resolve().parents[1]


def test_loso_ajusta_scaler_sem_o_participante_de_teste(monkeypatch):
    X = np.arange(36.).reshape(6, 6)
    y = np.array([0, 1, 0, 1, 0, 1])
    ids = np.array(['a', 'a', 'b', 'b', 'c', 'c'])
    original = StandardScaler.fit
    lotes = []

    def observar(self, X, *args, **kwargs):
        lotes.append(X.copy())
        return original(self, X, *args, **kwargs)

    monkeypatch.setattr(StandardScaler, 'fit', observar)
    p = probabilidade_loso(X, y, ids, 20260910)
    assert len(lotes) == 3 and np.isfinite(p).all()
    for obtido, esperado in zip(lotes, (X[[2, 3, 4, 5]], X[[0, 1, 4, 5]], X[:4])):
        np.testing.assert_array_equal(obtido, esperado)


@pytest.fixture
def artefatos():
    modelo = json.loads((ML / 'modelos/ml-inf-cabeca-v1.json').read_text(encoding='utf-8'))
    dourado = json.loads((ML / 'testes/fixtures/ml-inf-cabeca-v1-dourado.json').read_text(encoding='utf-8'))
    return modelo, dourado


def test_modelo_publicado_tem_exatamente_a_ordem_canonica(artefatos):
    m, _ = artefatos
    assert tuple(m['features']) == FEATURES_DO_DISPOSITIVO
    assert m['classe_positiva'] == 1 and m['limiar'] == .5 and m['comparacao'] == '>'
    for chave in ('coeficientes', 'medias', 'escalas'):
        assert len(m[chave]) == 6 and all(isfinite(v) for v in m[chave])
    assert all(s > 0 for s in m['escalas']) and isfinite(m['intercepto'])
    assert m['treino']['braco'] == 'cabeca' and m['treino']['qualidade'] == 'original'


def test_probabilidades_douradas_com_apenas_biblioteca_padrao(artefatos):
    m, d = artefatos
    assert d['modelo'] == m['versao']
    proximas = []
    for c in d['casos']:
        f = c['payload']['f'] if c['origem'] == 'simulador_c2' else c['f']
        assert len(f) == 6
        logit = m['intercepto'] + fsum(w * (x - u) / s for w, x, u, s in
                                      zip(m['coeficientes'], f, m['medias'], m['escalas']))
        e = exp(-abs(logit))
        p = 1 / (1 + e) if logit >= 0 else e / (1 + e)
        assert p == pytest.approx(c['probabilidade'], rel=0, abs=1e-12)
        assert int(p > m['limiar']) == c['classe']
        if c['origem'] == 'interpolacao_sintetica':
            proximas.append(p)
    assert len(proximas) == 2
    assert .49999 < min(proximas) < .5 < max(proximas) < .50001


def test_dourado_reproduz_o_f_do_payload_real_do_simulador(artefatos, monkeypatch):
    _, d = artefatos
    monkeypatch.syspath_prepend(str(ML.parent / 'scripts'))
    from simulador_c2 import NoiteSintetica, payload_da_epoca

    casos = {c['indice']: c for c in d['casos'] if c['origem'] == 'simulador_c2'}
    assert {c['classe'] for c in casos.values()} == {0, 1}
    noite = NoiteSintetica(datetime.fromisoformat(d['inicio']), d['epocas_simulador'],
                           seed=d['seed_simulador'])
    for i, epoca in enumerate(noite):
        if i in casos:
            atual, salvo = payload_da_epoca(epoca), casos[i]['payload']
            assert atual['fs'] == salvo['fs'] == 32
            assert atual['ts'] == salvo['ts']
            np.testing.assert_allclose(atual['f'], salvo['f'], rtol=0, atol=1e-12)
