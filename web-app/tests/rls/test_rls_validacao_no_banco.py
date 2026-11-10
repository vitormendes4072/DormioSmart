"""A validação da leitura e do pareamento também dentro do banco (SEC-18, migração 016).

── O QUE ESTÁ SOB TESTE ─────────────────────────────────────────────────────

Até a 016, as regras de `web-app/validacao.py` viviam só no Flask, e quem tinha conta chamava
`registrar_leitura_da_sessao` direto — a chave anon e o endereço são públicos — e gravava `NaN`,
captura em 2099 ou época −5 na própria conta (auditoria de 10/11, AUD-02). Estes testes fazem a
MESMA chamada direta, como a usuária logada, e exigem a recusa.

── A PARIDADE COM O FLASK, QUE É O QUE MAIS IMPORTA ─────────────────────────

Uma regra do banco MAIS ESTREITA que a do Flask faria uma leitura aceita pelo backend falhar na
gravação: 503, e o dispositivo reenviando para sempre. Por isso as bordas vêm das constantes da
própria `validacao.py`: cada borda tem de passar no banco, e um passo além dela tem de ser recusado.
Se alguém mudar uma faixa num lado só, um destes testes cai.
"""
import json
import math
import uuid

import pytest

import validacao

CHECK = "23514"  # check_violation
INSTANTE = "2026-11-10T03:00:00+00:00"


def _base(**mudancas):
    """Uma leitura válida, com os nomes de coluna que a função lê."""
    leitura = {
        "accel_x": 0.1, "accel_y": 0.2, "accel_z": 9.8, "movimento_total": 9.8,
        "gyro_x": 0.0, "gyro_y": 0.0, "gyro_z": 0.0, "temp": 25.0,
        "status": "Repouso", "captured_at": INSTANTE, "epoca_segundos": 30,
        "metodo_agregacao": "pico-da-magnitude", "amostras": 960,
        "enmo_media": 0.001, "enmo_desvio": 0.001, "enmo_max": 0.01, "mag_din_media": 0.002,
        "zcr": 0.1, "p_frac": 0.0, "g_x": 0.0, "g_y": 0.0, "g_z": 1.0, "fs_features": 32.0,
    }
    leitura.update(mudancas)
    return leitura


_SEQ = iter(range(1, 10_000_000))


def _unica(leitura):
    """Instante próprio por leitura: o `on conflict` da 011 não pode mascarar a gravação."""
    if leitura.get("captured_at") == INSTANTE:
        leitura = dict(leitura, captured_at=f"2026-11-10T03:00:00.{next(_SEQ):06d}+00:00")
    return leitura


def _gravar(sessao, device, leitura):
    return sessao.executar(
        "select public.registrar_leitura_da_sessao(%s, %s::jsonb)",
        (device, json.dumps(_unica(leitura), allow_nan=True)),
    )[0][0]


def _recusa(sessao, device, leitura):
    erro = sessao.negado(
        "select public.registrar_leitura_da_sessao(%s, %s::jsonb)",
        (device, json.dumps(_unica(leitura), allow_nan=True)),
    )
    assert erro.pgcode == CHECK, f"recusado pelo motivo errado: {erro.pgcode} {erro}"
    return erro


# --- as bordas, tiradas da validacao.py -------------------------------------

_PAYLOAD_PARA_COLUNA = {"ax": "accel_x", "ay": "accel_y", "az": "accel_z", "total": "movimento_total",
                        "gx": "gyro_x", "gy": "gyro_y", "gz": "gyro_z", "t": "temp"}

BORDAS = (
    [(_PAYLOAD_PARA_COLUNA[c], lo, hi)
     for c, (lo, hi) in {**validacao.CAMPOS_NUMERICOS, **validacao.CAMPOS_OPCIONAIS}.items()]
    + [(nome, lo, hi) for nome, lo, hi in validacao.FEATURES_DO_DISPOSITIVO]
)


def _passo(valor):
    return max(1e-6, abs(valor) * 1e-6)


@pytest.mark.parametrize("coluna,minimo,maximo", BORDAS, ids=[b[0] for b in BORDAS])
def test_a_borda_do_flask_passa_no_banco(como, cenario, coluna, minimo, maximo):
    with como(cenario["ana"]) as ana:
        assert _gravar(ana, cenario["device_ana"], _base(**{coluna: minimo})) is not None
        assert _gravar(ana, cenario["device_ana"], _base(**{coluna: maximo})) is not None


@pytest.mark.parametrize("coluna,minimo,maximo", BORDAS, ids=[b[0] for b in BORDAS])
def test_um_passo_alem_da_borda_e_recusado(como, cenario, coluna, minimo, maximo):
    with como(cenario["ana"]) as ana:
        _recusa(ana, cenario["device_ana"], _base(**{coluna: minimo - _passo(minimo)}))
        _recusa(ana, cenario["device_ana"], _base(**{coluna: maximo + _passo(maximo)}))


def test_a_epoca_e_a_taxa_tem_as_bordas_do_flask(como, cenario):
    d = cenario["device_ana"]
    with como(cenario["ana"]) as ana:
        for epoca in (validacao.EPOCA_MINIMA, validacao.EPOCA_MAXIMA):
            assert _gravar(ana, d, _base(epoca_segundos=epoca)) is not None
        for epoca in (validacao.EPOCA_MINIMA - 1, validacao.EPOCA_MAXIMA + 1):
            _recusa(ana, d, _base(epoca_segundos=epoca))
        assert _gravar(ana, d, _base(fs_features=validacao.FS_MAXIMA)) is not None
        _recusa(ana, d, _base(fs_features=validacao.FS_MAXIMA + 0.001))
        _recusa(ana, d, _base(fs_features=0.0))  # o Flask exige fs > 0
        _recusa(ana, d, _base(amostras=0))


def test_estado_e_metodo_so_os_do_flask(como, cenario):
    d = cenario["device_ana"]
    with como(cenario["ana"]) as ana:
        for estado in validacao.STATUS_VALIDOS:
            assert _gravar(ana, d, _base(status=estado)) is not None
        _recusa(ana, d, _base(status="<script>"))
        _recusa(ana, d, _base(status="Dormindo"))
        for metodo in validacao.METODOS_DE_AGREGACAO:
            assert _gravar(ana, d, _base(metodo_agregacao=metodo)) is not None
        _recusa(ana, d, _base(metodo_agregacao="inventado"))


def test_a_gravidade_tem_de_ser_unitaria(como, cenario):
    d = cenario["device_ana"]
    tol = validacao.TOLERANCIA_NORMA_G
    with como(cenario["ana"]) as ana:
        r = 1 / math.sqrt(2)
        assert _gravar(ana, d, _base(g_x=r, g_y=0.0, g_z=r)) is not None
        # Dentro da tolerância da norma, e com cada componente em [-1, 1], como no Flask.
        assert _gravar(ana, d, _base(g_x=0.0, g_y=0.0, g_z=1 - tol * 0.9)) is not None
        _recusa(ana, d, _base(g_x=0.0, g_y=0.0, g_z=1 + tol * 0.9))  # componente acima de 1
        _recusa(ana, d, _base(g_x=0.0, g_y=0.0, g_z=0.5))
        _recusa(ana, d, _base(g_x=0.6, g_y=0.6, g_z=0.6))


# --- a chamada direta da auditoria ------------------------------------------

@pytest.mark.parametrize("mudanca", [
    # Em texto, como a auditoria mandou: JSON nao tem NaN, e o banco converte "NaN".
    {"movimento_total": "NaN"},
    {"accel_x": "Infinity"},
    {"accel_y": 1e300},
    {"temp": -9999.0},
    {"epoca_segundos": -5},
    {"amostras": -1},
], ids=["nan", "infinito", "1e300", "temp", "epoca", "amostras"])
def test_a_leitura_da_auditoria_e_recusada(como, cenario, mudanca):
    with como(cenario["ana"]) as ana:
        _recusa(ana, cenario["device_ana"], _base(**mudanca))


def test_captura_no_futuro_e_recusada_e_a_folga_do_flask_passa(como, cenario):
    d = cenario["device_ana"]
    with como(cenario["ana"]) as ana:
        _recusa(ana, d, _base(captured_at="2099-01-01T00:00:00+00:00"))
        dentro = ana.executar("select (now() + interval '4 minutes')::text")[0][0]
        assert _gravar(ana, d, _base(captured_at=dentro)) is not None


def test_o_caminho_do_token_tambem_recusa(como, cenario):
    with como(cenario["ana"], papel="dormio_ingestao") as ingestao:
        erro = ingestao.negado(
            "select public.registrar_leitura(%s, %s::jsonb)",
            ("hash-ana-1", json.dumps(_base(status="Dormindo"))),
        )
        assert erro.pgcode == CHECK
        erro = ingestao.negado(
            "select public.registrar_leitura(%s, %s::jsonb)",
            ("hash-ana-1", json.dumps(_base(captured_at="2099-01-01T00:00:00+00:00"))),
        )
        assert erro.pgcode == CHECK


def test_leitura_antiga_sem_vetor_continua_valida(como, cenario):
    """O ESP32 sem giroscópio e a leitura sem `f` mandam nulos, e nulo passa."""
    with como(cenario["ana"]) as ana:
        assert _gravar(ana, cenario["device_ana"], {"movimento_total": 9.8, "status": "Repouso"}) is not None


# --- dispositivos -----------------------------------------------------------

def _hash():
    return uuid.uuid4().hex * 2  # 64 hexadecimais


def test_pareamento_recusa_hash_fora_do_formato(como, cenario):
    with como(cenario["ana"]) as ana:
        for ruim in ("abc", "A1" * 32, "g" * 64, "a1" * 33):
            erro = ana.negado("select id from public.parear_dispositivo('x', 'celular', %s)", (ruim,))
            assert erro.pgcode == CHECK, ruim
        assert ana.executar("select id from public.parear_dispositivo('ok', 'celular', %s)", (_hash(),))


def test_pareamento_recusa_nome_acima_de_60(como, cenario):
    with como(cenario["ana"]) as ana:
        assert ana.executar("select id from public.parear_dispositivo(%s, 'celular', %s)",
                            ("n" * 60, _hash()))
        erro = ana.negado("select id from public.parear_dispositivo(%s, 'celular', %s)",
                          ("n" * 61, _hash()))
        assert erro.pgcode == CHECK


def test_o_titular_nao_renomeia_para_mais_de_60(como, cenario):
    with como(cenario["ana"]) as ana:
        erro = ana.negado("update public.devices set nome = %s where id = %s",
                          ("n" * 61, cenario["device_ana"]))
        assert erro.pgcode == CHECK


def test_o_teto_e_de_10_dispositivos_ativos(como, cenario):
    with como(cenario["ana"]) as ana:
        ativos = ana.executar(
            "select count(*) from public.devices where user_id = %s and revoked_at is null",
            (cenario["ana"],))[0][0]
        for i in range(10 - ativos):
            assert ana.executar("select id from public.parear_dispositivo(%s, 'celular', %s)",
                                (f"d{i}", _hash()))
        erro = ana.negado("select id from public.parear_dispositivo('o 11', 'celular', %s)", (_hash(),))
        assert erro.pgcode == CHECK


def test_revogado_libera_a_vaga(como, cenario):
    with como(cenario["ana"]) as ana:
        ativos = ana.executar(
            "select count(*) from public.devices where user_id = %s and revoked_at is null",
            (cenario["ana"],))[0][0]
        ids = [ana.executar("select id from public.parear_dispositivo(%s, 'celular', %s)",
                            (f"d{i}", _hash()))[0][0] for i in range(10 - ativos)]
        ana.executar("update public.devices set revoked_at = now() where id = %s", (ids[0],))
        assert ana.executar("select id from public.parear_dispositivo('na vaga', 'celular', %s)", (_hash(),))


def test_o_titular_nao_desfaz_a_revogacao(como, cenario):
    with como(cenario["ana"]) as ana:
        novo = ana.executar("select id from public.parear_dispositivo('rev', 'celular', %s)",
                            (_hash(),))[0][0]
        ana.executar("update public.devices set revoked_at = now() where id = %s", (novo,))
        erro = ana.negado("update public.devices set revoked_at = null where id = %s", (novo,))
        assert erro.pgcode == CHECK


def test_o_dono_do_banco_ainda_desfaz_para_manutencao(como, cenario):
    with como(cenario["ana"]) as ana:
        novo = ana.executar("select id from public.parear_dispositivo('rev', 'celular', %s)",
                            (_hash(),))[0][0]
        ana.executar("update public.devices set revoked_at = now() where id = %s", (novo,))
        ana.cursor.execute("set local role postgres")
        assert ana.contar_afetadas("update public.devices set revoked_at = null where id = %s", (novo,)) == 1


# --- a noite real continua passando -----------------------------------------

def test_a_noite_do_emulador_passa_inteira_pelo_banco(como, cenario):
    """As linhas da fixture do app, convertidas como a ingestão grava, todas aceitas."""
    from pathlib import Path

    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "noite_do_app_emulador.jsonl"
    noite = [json.loads(l) for l in fixture.read_text(encoding="utf-8").splitlines() if l.strip()]
    with como(cenario["ana"]) as ana:
        for p in noite:
            conteudo, erro = validacao.validar_leitura(dict(p))
            assert erro is None
            linha = {
                "accel_x": p["ax"], "accel_y": p["ay"], "accel_z": p["az"],
                "movimento_total": p["total"], "temp": p.get("t"), "status": p["status"],
                "captured_at": p["ts"], "epoca_segundos": p["epoca_s"],
                "metodo_agregacao": p["metodo"], "amostras": p["amostras"],
                **validacao.colunas_de_features(conteudo),
            }
            assert _gravar(ana, cenario["device_ana"], linha) is not None
