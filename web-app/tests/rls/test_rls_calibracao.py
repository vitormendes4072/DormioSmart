"""`g_norma` e `calibrada` no banco (CAL-03, migração 018).

As duas funções de gravação passam a guardar a norma da gravidade média e a marca
de calibração, e a restrição `sleep_data_calibracao_valida` tem a MESMA régua do
Flask (`validacao._validar_calibracao`): mais estreita que ele, uma leitura
aceita pelo backend falharia na gravação e o celular reenviaria para sempre.
"""
import json

import pytest

import validacao
from test_rls_validacao_no_banco import CHECK, _base, _gravar, _recusa, _unica


def _ler(sessao, leitura_id):
    return sessao.executar(
        "select g_norma, calibrada from public.sleep_data where id = %s", (leitura_id,))[0]


def test_a_sessao_grava_gn_e_a_marca(como, cenario):
    with como(cenario["ana"]) as ana:
        i = _gravar(ana, cenario["device_ana"], _base(g_norma=1.0193, calibrada=True))
        assert _ler(ana, i) == (1.0193, True)
        i = _gravar(ana, cenario["device_ana"], _base(g_norma=1.0, calibrada=False))
        assert _ler(ana, i) == (1.0, False)


def test_o_token_grava_gn_e_a_marca(como, cenario):
    with como(cenario["ana"], papel="dormio_ingestao") as ingestao:
        i = ingestao.executar(
            "select public.registrar_leitura(%s, %s::jsonb)",
            ("hash-ana-1", json.dumps(_unica(_base(g_norma=0.9987, calibrada=True)))),
        )[0][0]
        assert i is not None
        # A ingestão não lê `sleep_data`, e cada sessão volta atrás no fim:
        # a leitura é conferida na MESMA transação, como dono do banco.
        ingestao.cursor.execute("set local role postgres")
        assert _ler(ingestao, i) == (0.9987, True)


def test_sem_os_dois_continua_valido_e_fica_nulo(como, cenario):
    """O app antigo e o travesseiro não mandam: a leitura grava com as colunas nulas."""
    with como(cenario["ana"]) as ana:
        i = _gravar(ana, cenario["device_ana"], _base())
        assert _ler(ana, i) == (None, None)


@pytest.mark.parametrize("gn", [0.0, validacao.GN_MAXIMA_G])
def test_a_borda_do_flask_passa(como, cenario, gn):
    with como(cenario["ana"]) as ana:
        assert _gravar(ana, cenario["device_ana"], _base(g_norma=gn, calibrada=True)) is not None


# NaN em texto, como a auditoria mandou: JSON não tem NaN, e o banco converte "NaN".
@pytest.mark.parametrize("gn", [-0.001, validacao.GN_MAXIMA_G + 0.001, "NaN"])
def test_um_passo_alem_da_borda_e_recusado(como, cenario, gn):
    with como(cenario["ana"]) as ana:
        _recusa(ana, cenario["device_ana"], _base(g_norma=gn))


@pytest.mark.parametrize("extra", [{"g_norma": 1.0}, {"calibrada": True}])
def test_sem_o_vetor_e_recusado(como, cenario, extra):
    """O Flask recusa `gn`/`cal` sem `f`; o banco, as colunas sem o vetor."""
    sem_vetor = {"movimento_total": 9.8, "status": "Repouso", **extra}
    with como(cenario["ana"]) as ana:
        erro = _recusa(ana, cenario["device_ana"], sem_vetor)
        assert erro.pgcode == CHECK
