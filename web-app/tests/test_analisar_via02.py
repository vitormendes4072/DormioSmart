"""A análise do VIA-02 (`scripts/analisar_via02.py`) com noites sintéticas.

O que importa travar: o pareamento por sobreposição aguenta a defasagem de
0 a 29 s entre as grades dos dois aparelhos; um atraso de relógio de 1 ou 2
registros é medido e corrigido; trecho sem registro não vira discordância; e o
veredito segue o critério fixado no protocolo, antes dos dados.
"""
import importlib.util
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

_script = Path(__file__).resolve().parents[2] / "scripts" / "analisar_via02.py"
_spec = importlib.util.spec_from_file_location("analisar_via02", _script)
via02 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(via02)

INICIO = datetime(2026, 11, 24, 2, 0, tzinfo=timezone.utc)
EPOCA_S = 30
SOBREPOSICAO_S = 15


def _padrao(n, fracao=0.15, semente=3):
    """Quais épocas têm movimento, em rajadas, como numa noite."""
    rng = random.Random(semente)
    saida, ativo = [], False
    for _ in range(n):
        if rng.random() < (0.35 if ativo else fracao / 4):
            ativo = not ativo
        saida.append(ativo)
    return saida


def _serie(movimento, deslocamento_s=0.0, faltando=(), semente=1):
    """`features` e `historico` de um aparelho: uma época a cada 30 s.

    O instante é o FIM da época (como o `captured_at`); `deslocamento_s` move a
    grade do aparelho; `faltando` são índices que o aparelho não registrou.
    """
    rng = random.Random(semente)
    epocas, historico = [], []
    for i, mexeu in enumerate(movimento):
        if i in faltando:
            continue
        fim = INICIO + timedelta(seconds=(i + 1) * EPOCA_S + deslocamento_s)
        intensidade = (2.5 if mexeu else 0.05) * (1 + rng.random() * 0.2)
        texto = fim.isoformat()
        epocas.append({"instante": texto, "mag_din_media": intensidade / 100, "enmo_media": intensidade / 200})
        historico.append({"captured_at": texto, "created_at": texto, "status": "Movimento" if mexeu else "Repouso",
                          "movimento_total": 9.81 + intensidade})
    return {"features": {"epocas": epocas}, "historico": historico}


def _noite(trav, cel, **extra):
    return {"protocolo": "VIA-02", "travesseiro": trav, "celular": cel, **extra}


N = 600  # 5 h


def test_series_iguais_com_grades_defasadas_concordam_inteiras():
    mov = _padrao(N)
    for deslocamento in (0, 5, 15, 29):
        r = via02.analisar_noite(_noite(_serie(mov), _serie(mov, deslocamento_s=deslocamento, semente=2)))
        assert r["pares"] == N, deslocamento
        assert r["kappa"] == pytest.approx(1.0), deslocamento
        assert r["travesseiro_viu_do_celular"] == pytest.approx(1.0)
        # Defasagem de grade não é atraso de relógio: no empate (15 s), o par é
        # o registro do celular que termina depois, e o atraso medido fica 0.
        # (Com 29 s, o vizinho de 29 s de sobreposição é o anterior: 29 s de
        # grade e −1 s mais um registro de atraso são indistinguíveis.)
        if deslocamento <= SOBREPOSICAO_S:
            assert r["atraso_em_registros"] == 0, deslocamento


def test_buraco_no_celular_nao_pareia_com_registro_distante():
    mov = _padrao(N)
    buraco = set(range(300, 360))
    r = via02.analisar_noite(_noite(_serie(mov), _serie(mov, faltando=buraco, semente=2)))
    assert r["pares"] == N - len(buraco)
    assert r["cobertura_celular"] == pytest.approx((N - len(buraco)) / N, abs=0.01)


def test_viu_e_medido_na_direcao_certa():
    # O travesseiro perde movimento; o celular vê tudo o que o travesseiro viu.
    mov = _padrao(N)
    r = via02.analisar_noite(_noite(_serie(_perde(mov, 0.3)), _serie(mov, semente=2)))
    assert r["travesseiro_viu_do_celular"] < 0.85
    assert r["celular_viu_do_travesseiro"] == pytest.approx(1.0)


def test_series_independentes_quase_nao_concordam():
    r = via02.analisar_noite(_noite(_serie(_padrao(N, semente=3)), _serie(_padrao(N, semente=99), semente=2)))
    assert abs(r["kappa"]) < 0.15


def test_atraso_de_relogio_de_dois_registros_e_medido_e_corrigido():
    mov = _padrao(N)
    r = via02.analisar_noite(_noite(_serie(mov), _serie(mov, deslocamento_s=60 + 7, semente=2)))
    assert r["atraso_em_registros"] == 2
    assert r["kappa"] == pytest.approx(1.0)


def test_atraso_de_um_registro_tambem_e_corrigido():
    mov = _padrao(N)
    r = via02.analisar_noite(_noite(_serie(mov), _serie(mov, deslocamento_s=-30, semente=2)))
    assert r["atraso_em_registros"] == -1
    assert r["kappa"] == pytest.approx(1.0)


def test_trecho_sem_registro_nao_vira_discordancia():
    mov = _padrao(N)
    buraco = set(range(100, 220))
    r = via02.analisar_noite(_noite(_serie(mov, faltando=buraco), _serie(mov, semente=2)))
    assert r["pares"] == N - len(buraco)
    assert r["kappa"] == pytest.approx(1.0)
    assert r["cobertura_travesseiro"] == pytest.approx((N - len(buraco)) / N, abs=0.01)


def _perde(mov, fracao, semente=5):
    """O travesseiro deixa de ver `fracao` dos registros com movimento do celular."""
    rng = random.Random(semente)
    return [m and rng.random() >= fracao for m in mov]


def test_veredito_capta_quando_ve_quase_tudo():
    noites = []
    for s in range(5):
        mov = _padrao(N, semente=10 + s)
        noites.append(_noite(_serie(_perde(mov, 0.05, s)), _serie(mov, deslocamento_s=11, semente=2)))
    r = via02.analisar(noites)
    assert r["veredito"]["capta"] is True
    assert r["veredito"]["viu"] > 0.9


def test_veredito_nao_capta_quando_perde_metade():
    noites = []
    for s in range(5):
        mov = _padrao(N, semente=10 + s)
        noites.append(_noite(_serie(_perde(mov, 0.5, s)), _serie(mov, deslocamento_s=11, semente=2)))
    r = via02.analisar(noites)
    assert r["veredito"]["capta"] is False


def test_com_pouco_movimento_o_intervalo_segura_o_veredito():
    # 80% vistos, mas em ~15 registros com movimento nas 5 noites: o limite
    # inferior do intervalo fica longe dos 70%, e o veredito não pode ser "capta".
    noites = []
    for s in range(5):
        mov = _padrao(N, fracao=0.004, semente=10 + s)
        noites.append(_noite(_serie(_perde(mov, 0.15, s)), _serie(mov, deslocamento_s=11, semente=2)))
    r = via02.analisar(noites, reamostras=500)
    assert r["veredito"]["viu"] >= via02.VIU_MINIMO
    assert r["veredito"]["ic95"][0] <= via02.LIMITE_INFERIOR
    assert r["veredito"]["capta"] is False


def test_series_independentes_nao_captam():
    noites = [_noite(_serie(_padrao(N, semente=20 + s)), _serie(_padrao(N, semente=70 + s), semente=2))
              for s in range(5)]
    assert via02.analisar(noites, reamostras=500)["veredito"]["capta"] is False


def test_poucas_noites_nao_dao_veredito():
    mov = _padrao(N)
    r = via02.analisar([_noite(_serie(mov), _serie(mov, semente=2))])
    assert r["veredito"]["capta"] is None
    assert "noites" in r["veredito"]["motivo"]


def test_noite_curta_fica_fora_do_veredito():
    curta = _padrao(60)
    r = via02.analisar_noite(_noite(_serie(curta), _serie(curta, semente=2)))
    assert r["entra_no_veredito"] is False


def test_limiar_candidato_do_celular_iguala_as_fracoes():
    mov = _padrao(N)
    r = via02.analisar_noite(_noite(_serie(mov), _serie(mov, semente=2)))
    limiar = r["limiar_do_celular_que_iguala"]
    intensidades = [h["movimento_total"] - 9.81 for h in _serie(mov, semente=2)["historico"]]
    fracao_cel = sum(1 for x in intensidades if x > limiar) / len(intensidades)
    assert fracao_cel == pytest.approx(r["fracao_movimento_travesseiro"], abs=0.01)


def test_modelo_nos_dois_quando_veio():
    mov = _padrao(N)
    trav, cel = _serie(mov), _serie(mov, deslocamento_s=8, semente=2)
    trav["inferencia"] = {"epocas": [{"instante": e["instante"], "classe": 0 if m else 1}
                                     for e, m in zip(trav["features"]["epocas"], mov)]}
    cel["inferencia"] = {"epocas": [{"instante": e["instante"], "classe": 0 if m else 1}
                                    for e, m in zip(cel["features"]["epocas"], mov)]}
    r = via02.analisar_noite(_noite(trav, cel))
    assert r["modelo"]["concordancia"] == pytest.approx(1.0)


def test_cli_sem_pares_sai_com_2(tmp_path, capsys):
    arquivo = tmp_path / "via02.json"
    arquivo.write_text(json.dumps(_noite(_serie([]), _serie([]))), encoding="utf-8")
    assert via02.main([str(arquivo)]) == 2
