"""Contrato do exportador e paridade das noites C2, com casos de fronteira."""

from datetime import datetime, timedelta
from math import exp, fsum, isfinite
from statistics import mean, stdev
from types import SimpleNamespace

import numpy as np
import pytest

from experimentos import ml_inf_v2 as v2
from src.epocas import segmentos_epocas
from src.features import NOMES_FEATURES, features_inter_epoca


@pytest.fixture(scope='module')
def artefatos():
    return (v2.ler_json(v2.ML / f'modelos/{v2.VERSAO}.json'),
            v2.ler_json(v2.ML / f'testes/fixtures/{v2.VERSAO}-dourado.json'))


def test_contrato_publicado(artefatos):
    m, dourado = artefatos
    assert m['versao'] == dourado['modelo'] == 'ml-inf-cabeca-v2'
    assert m['configuracao'] == 'item9_ctx11'
    assert tuple(m['features']) == tuple(NOMES_FEATURES)
    esperado = [f'{nome}__{d:+d}' for d in range(-11, 12) for nome in NOMES_FEATURES]
    assert m['colunas_contexto'] == esperado == v2.colunas_contexto()
    assert len(m['coeficientes']) == 184
    assert all(map(isfinite, [m['intercepto'], *m['coeficientes']]))
    assert not {'medias', 'escalas'} & m.keys()
    assert m['limiar'] == 0.5 and m['comparacao'] == '>' and m['classe_empate'] == 0
    assert m['normalizacao']['minimo_epocas_validas'] == 23
    assert m['normalizacao']['ddof'] == 1
    assert m['contexto']['vizinhas'] == 11
    assert m['contexto']['quebra_servidor_s'] == 45


def test_coeficientes_exportados_pontuam_a_matriz_empilhada():
    rng = np.random.default_rng(42)
    X = rng.normal(size=(60, 8))
    y = (X[:, 3] - X[:, 0] > 0).astype(int)
    ids = np.repeat(['a', 'b'], 30)
    d = dict(X=X, y=y, id=ids, gravacao=ids, indice_epoca=np.tile(np.arange(30), 2))
    Xc, _ = v2.preparar_historico(d)
    clf = v2.ajustar(Xc, y, 20260910)
    atribuicao = dict.fromkeys(('colecao', 'colecao_primaria', 'artigo', 'licenca_do_pacote'), 'teste')
    m = v2.exportar(clf, SimpleNamespace(hash='teste'), 'teste', d, 'teste', atribuicao)
    nomeadas = dict(zip(v2.colunas_contexto(), Xc.T, strict=True))
    logit = sum(w * nomeadas[n] for n, w in zip(m['colunas_contexto'], m['coeficientes'], strict=True))
    logit += m['intercepto']
    np.testing.assert_allclose(1 / (1 + np.exp(-logit)), clf.predict_proba(Xc)[:, 1], rtol=0, atol=1e-12)
    np.testing.assert_array_equal(logit > 0, clf.predict(Xc))


def test_normalizacao_por_gravacao_e_contexto_por_segmento():
    # Duas gravações da mesma pessoa, uma lacuna na primeira e colunas constantes.
    x = np.arange(8, dtype=float)
    X = np.column_stack((x, np.ones((8, 7))))
    g = np.repeat(['r1', 'r2'], 4)
    d = dict(X=X, y=np.zeros(8), id=np.repeat('p', 8), gravacao=g,
             indice_epoca=np.array([0, 1, 3, 4, 0, 1, 2, 3]))
    Xc, cobertura = v2.preparar_historico(d)
    esperado = np.tile(np.array([-1.5, -0.5, 0.5, 1.5]) / np.sqrt(5 / 3), 2)
    np.testing.assert_allclose(Xc[:, 88], esperado, rtol=0, atol=1e-12)
    assert not Xc[:, 89:96].any()
    np.testing.assert_array_equal(Xc[[1, 2, 3], [96, 80, 96]], esperado[[1, 2, 3]])
    assert cobertura['abaixo_do_piso'] == 2
    d['X'][0, 0] = np.inf
    with pytest.raises(ValueError, match='histórica.*inválida'):
        v2.preparar_historico(d)


def payloads_com_instantes(segundos):
    inicio = datetime.fromisoformat('2026-11-01T23:00:00+00:00')
    return [dict(ts=(inicio + timedelta(seconds=s)).isoformat(), fs=32,
                 f=[0.1] * 6, g=[0, 0, 1] if i == 0 else [0, 1, 0])
            for i, s in enumerate(segundos)]


def test_piso_conta_so_epocas_com_oito_features_finitas():
    servidor, _ = v2.importar_fronteira()
    payloads = payloads_com_instantes(range(0, 23 * 30, 30))
    linhas, _, segmentos, Xc = v2.preparar_noite(payloads, servidor)
    assert linhas[0]['d_angulo'] is None and len(linhas) == 23
    assert len(set(segmentos)) == 1 and np.isfinite(Xc).all()
    for invalido in (None, '0.1', np.inf, np.nan, True):
        payloads[11]['f'][0] = invalido
        with pytest.raises(ValueError, match='22 épocas válidas; mínimo 23'):
            v2.preparar_noite(payloads, servidor)


@pytest.mark.parametrize('intervalo, indice, quebra_servidor, quebra_ml', [
    (30, 1, False, False),
    (45, 2, False, True),
    (45.001, 1, True, False),
    (60, 2, True, True),
])
def test_lacuna_servidor_e_indice_original(intervalo, indice, quebra_servidor, quebra_ml):
    servidor, _ = v2.importar_fronteira()
    entrada = payloads_com_instantes([0, *(intervalo + 30 * i for i in range(24))])
    linhas, _, seg, Xc = v2.preparar_noite(entrada, servidor)
    originais = np.r_[0, np.arange(indice, indice + 24)]
    seg_ml = segmentos_epocas(np.zeros(25), np.zeros(25), originais)
    _, d_ml = features_inter_epoca(np.asarray([p['g'] for p in entrada]))
    assert bool(seg[1]) is quebra_servidor
    assert bool(seg_ml[1]) is quebra_ml
    assert d_ml[0] == 0 and linhas[0]['d_angulo'] is None
    assert d_ml[1] == pytest.approx(90)
    if quebra_servidor:
        assert linhas[1]['d_angulo'] is None
        assert Xc[1, 95] == 0.0
        np.testing.assert_array_equal(Xc[1, :8], Xc[1, 88:96])
    else:
        assert linhas[1]['d_angulo'] == pytest.approx(d_ml[1])


def verificar_probabilidades(m, linhas, probabilidades, classes, tolerancia):
    for x, esperado, classe in zip(linhas, probabilidades, classes, strict=True):
        z = m['intercepto'] + fsum(w * v for w, v in zip(m['coeficientes'], x, strict=True))
        e = exp(-abs(z))
        p = 1 / (1 + e) if z >= 0 else e / (1 + e)
        assert abs(p - esperado) <= tolerancia
        assert int(z > 0) == classe


def matriz_referencia(linhas, segmentos, nomes_colunas):
    X = [[0.0 if e[k] is None else e[k] for k in NOMES_FEATURES] for e in linhas]
    medias = [mean(v) for v in zip(*X)]
    desvios = [stdev(v) for v in zip(*X)]
    Z = [[(x - mu) / (s if s >= 1e-9 else 1) for x, mu, s in zip(row, medias, desvios)]
         for row in X]
    grupos = {}
    for i, s in enumerate(segmentos):
        grupos.setdefault(s, []).append(i)
    colunas = [(NOMES_FEATURES.index(nome), int(d))
               for nome, d in (c.split('__') for c in nomes_colunas)]
    return [[Z[max(grupos[s][0], min(i + d, grupos[s][-1]))][k] for k, d in colunas]
            for i, s in enumerate(segmentos)]


def test_referencia_angular_da_noite_pode_diferir_da_referencia_por_trecho():
    servidor, _ = v2.importar_fronteira()
    entrada = payloads_com_instantes([*(i * 30 for i in range(24)), 25 * 30, 26 * 30])
    for p in entrada[:24]:
        p['g'] = [0, 0, 1]
    linhas, _, seg, _ = v2.preparar_noite(entrada, servidor)
    incl_trecho, _ = features_inter_epoca(np.asarray([p['g'] for p in entrada[24:]]))
    assert seg[23] != seg[24]
    assert incl_trecho[0] == pytest.approx(0)
    assert linhas[24]['inclinacao_rel'] == pytest.approx(90, abs=1e-6, rel=0)


def test_dourado_reproduz_duas_noites_e_empate(artefatos):
    m, dourado = artefatos
    servidor, simulador = v2.importar_fronteira()
    tol = dourado['tolerancia_absoluta']
    assert tol == 1e-12
    original = [simulador.payload_da_epoca(e) for e in simulador.NoiteSintetica(
        datetime.fromisoformat(dourado['inicio']), 960, seed=dourado['seed_simulador'])]
    for nome, entrada in [('continua', original), ('lacuna', original[:480] + original[481:])]:
        noite = dourado['noites'][nome]
        for atual, salvo in zip(entrada, noite['payloads'], strict=True):
            assert atual['ts'] == salvo['ts'] and atual['fs'] == salvo['fs'] == 32
            for k in ('f', 'g'):
                np.testing.assert_allclose(atual[k], salvo[k], atol=1e-12, rtol=0)
        linhas, ref, seg, Xc = v2.preparar_noite(noite['payloads'], servidor)
        np.testing.assert_array_equal(seg, noite['segmentos'])
        np.testing.assert_allclose(ref, noite['g_ref'], rtol=0, atol=1e-12)
        inc, d = features_inter_epoca(np.asarray([p['g'] for p in noite['payloads']]))
        for i, (a, b) in enumerate(zip(linhas, noite['features_servidor'], strict=True)):
            assert a['instante'] == b['instante']
            assert inc[i] == pytest.approx(a['inclinacao_rel'], abs=1e-6, rel=0)
            for k in NOMES_FEATURES:
                if b[k] is None:
                    assert a[k] is None and i in (0, 480)
                else:
                    tol_feature = 1e-6 if k in ('inclinacao_rel', 'd_angulo') else 1e-12
                    assert a[k] == pytest.approx(b[k], abs=tol_feature, rel=0)
            if a['d_angulo'] is not None:
                assert a['d_angulo'] == pytest.approx(d[i], abs=1e-6, rel=0)
        if nome == 'lacuna':
            assert linhas[480]['d_angulo'] is None and d[480] > 1e-6
            assert seg[480] != seg[479]
        referencia = matriz_referencia(linhas, seg, m['colunas_contexto'])
        np.testing.assert_allclose(Xc, referencia, atol=1e-12, rtol=0)
        verificar_probabilidades(m, referencia, noite['probabilidades'], noite['classes'], tol)
    abaixo, empate, acima = dourado['limiar']
    assert abaixo['probabilidade'] < empate['probabilidade'] == 0.5 < acima['probabilidade']
    assert [c['classe'] for c in dourado['limiar']] == [0, 0, 1]
    for c in dourado['limiar']:
        verificar_probabilidades(m, [c['contexto']], [c['probabilidade']], [c['classe']], tol)
