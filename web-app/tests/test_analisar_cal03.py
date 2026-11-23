"""A análise da etapa 3 do CAL-03 (`scripts/analisar_cal03.py`) com noites sintéticas.

O que importa travar: só época parada e de orientação definida entra no piso;
a época calibrada não se mistura com a que não é; o veredito segue o critério
fixado antes dos dados, com o controle sem calibração mostrando o viés que a
noite de 10/11 mostrou; e a exportação anterior à 2.12.0 é recusada, em vez de
analisada como se não houvesse calibração.
"""
import importlib.util
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

_script = Path(__file__).resolve().parents[2] / "scripts" / "analisar_cal03.py"
_spec = importlib.util.spec_from_file_location("analisar_cal03", _script)
cal03 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cal03)

CIMA = [0.0, 0.0, 1.0]
BAIXO = [0.0, 0.0, -1.0]
DE_LADO = [1.0, 0.0, 0.0]

# O Moto E7 sem calibração (diário, 10/11 (iii) e (iv)): a norma parada e o piso
# da medida de movimento em cada posição. Calibrado, os dois somem.
SEM_CAL = {"cima": (1.004, 0.0042), "baixo": (1.020, 0.0187)}
COM_CAL = {"cima": (1.0002, 0.0004), "baixo": (1.0003, 0.0006)}


def _epoca(i, g, norma, enmo, calibrada, mag=0.002, temp=19.0):
    inicio = datetime(2026, 11, 24, 2, 0, tzinfo=timezone.utc)
    return {"instante": (inicio + timedelta(seconds=30 * i)).isoformat(), "g": g,
            "g_norma": norma, "calibrada": calibrada, "temp": temp,
            "enmo_media": enmo, "mag_din_media": mag}


def _noite(lado, calibrada, n=200, semente=1, perfil=None, movimento=20, de_lado=20, **extra):
    """Uma noite numa orientação, com épocas em movimento e de lado misturadas."""
    rng = random.Random(semente)
    perfil = perfil or (COM_CAL if calibrada else SEM_CAL)
    norma, piso = perfil[lado]
    g = CIMA if lado == "cima" else BAIXO
    epocas = [_epoca(i, g, norma + rng.gauss(0, 0.0003), max(piso + rng.gauss(0, 0.0003), 0.0), calibrada)
              for i in range(n)]
    # Em movimento o ENMO é alto, e não é piso.
    epocas += [_epoca(n + i, g, norma, 0.030, calibrada, mag=0.050) for i in range(movimento)]
    # De lado o eixo z não diz a posição.
    epocas += [_epoca(n + movimento + i, DE_LADO, 1.03, 0.030, calibrada) for i in range(de_lado)]
    dados = {"janela": {"inicio": f"2026-11-{24 + semente:02d}T02:00:00Z"},
             "celular": {"features": {"epocas": epocas}}}
    dados.update(extra)
    return dados


def _resumos(*noites):
    return [cal03.resumo_da_noite(n, f"n{i}") for i, n in enumerate(noites)]


def test_calibrada_nas_duas_orientacoes_tira_o_vies():
    r = cal03.veredito(_resumos(_noite("cima", True, semente=1), _noite("baixo", True, semente=2),
                                _noite("cima", True, semente=3), _noite("baixo", True, semente=4)))
    assert r["decisao"] == "tirou o viés"
    assert abs(r["calibradas"]["diferenca_mg"]) < 1.0


def test_sem_calibracao_o_controle_mostra_o_vies_de_10_11():
    """Controle positivo: com os números da noite de 10/11, a conta acha o viés."""
    noites = _resumos(_noite("cima", False, semente=1), _noite("baixo", False, semente=2),
                      _noite("cima", False, semente=3), _noite("baixo", False, semente=4))
    c = cal03.comparar(noites, False)
    assert c["noites_bastam"]
    assert c["diferenca_mg"] == pytest.approx(14.5, abs=0.5)
    assert cal03.veredito(noites)["decisao"] == "inconclusivo", "sem noite calibrada não há veredito"


def test_calibracao_que_nao_corrige_e_reprovada():
    """Calibrada, mas com o viés de antes: a marca não basta."""
    noites = _resumos(*(_noite(lado, True, semente=s, perfil=SEM_CAL)
                        for s, lado in enumerate(("cima", "baixo", "cima", "baixo"), start=1)))
    r = cal03.veredito(noites)
    assert r["decisao"] == "não tirou o viés" and "diferença" in r["motivo"]


def test_vies_invertido_tambem_reprova():
    """Calibração que passa do ponto: o piso de cima é que sobe. Conta o módulo."""
    invertido = {"cima": (1.0002, 0.0100), "baixo": (1.0002, 0.0)}
    noites = _resumos(*(_noite(lado, True, semente=s, perfil=invertido)
                        for s, lado in enumerate(("cima", "baixo", "cima", "baixo"), start=1)))
    r = cal03.veredito(noites)
    assert r["calibradas"]["diferenca_mg"] < -5
    assert r["decisao"] == "não tirou o viés"


def test_norma_fora_de_1_g_reprova_mesmo_com_os_pisos_iguais():
    """As duas posições com 0,99 g: o piso é 0 nas duas, e o movimento pequeno some."""
    baixa = {"cima": (0.990, 0.0), "baixo": (0.990, 0.0)}
    noites = _resumos(*(_noite(lado, True, semente=s, perfil=baixa)
                        for s, lado in enumerate(("cima", "baixo", "cima", "baixo"), start=1)))
    r = cal03.veredito(noites)
    assert r["decisao"] == "não tirou o viés" and "norma" in r["motivo"]


def test_so_a_epoca_parada_e_de_orientacao_definida_entra_no_piso():
    n = cal03.resumo_da_noite(_noite("cima", True, movimento=150, de_lado=150), "x")
    g = n["grupos"][(True, "cima")]
    assert g["paradas"] == 200
    assert g["piso_mg"] == pytest.approx(0.4, abs=0.2)


def test_epoca_sem_calibracao_nao_entra_no_grupo_calibrado():
    """Noite calibrada só em parte: cada metade vai para o seu grupo."""
    a = _noite("baixo", True, n=100)
    b = _noite("baixo", False, n=100, semente=2)
    a["celular"]["features"]["epocas"] += b["celular"]["features"]["epocas"]
    n = cal03.resumo_da_noite(a, "x")
    assert n["grupos"][(True, "baixo")]["piso_mg"] < 1.0
    assert n["grupos"][(False, "baixo")]["piso_mg"] > 15.0
    assert 0.0 < n["fracao_calibrada"] < 1.0


def test_grupo_com_poucas_paradas_nao_conta():
    noites = _resumos(_noite("cima", True, semente=1), _noite("baixo", True, n=29, semente=2),
                      _noite("cima", True, semente=3), _noite("baixo", True, semente=4))
    assert noites[1]["grupos"][(True, "baixo")]["valido"] is False
    assert cal03.veredito(noites)["decisao"] == "inconclusivo"


def test_uma_noite_por_orientacao_e_inconclusivo():
    r = cal03.veredito(_resumos(_noite("cima", True), _noite("baixo", True, semente=2)))
    assert r["decisao"] == "inconclusivo"


def test_orientacao_pelo_z_da_gravidade():
    assert cal03.orientacao([0.0, 0.3, 0.95]) == "cima"
    assert cal03.orientacao([0.0, -0.3, -0.95]) == "baixo"
    assert cal03.orientacao([0.0, 0.6, 0.8]) is None, "a 37° do eixo não é deitado"
    assert cal03.orientacao(None) is None


def test_exportacao_anterior_a_2_12_e_recusada():
    """Sem `g` e `calibrada`, a noite pareceria toda sem calibração."""
    dados = _noite("cima", True)
    for e in dados["celular"]["features"]["epocas"]:
        del e["g"], e["calibrada"]
    with pytest.raises(cal03.DadosInsuficientes, match="2.12.0"):
        cal03.resumo_da_noite(dados)


def test_arquivo_sem_celular_e_recusado():
    with pytest.raises(cal03.DadosInsuficientes):
        cal03.resumo_da_noite({"travesseiro": {"features": {"epocas": [{}]}}})


def test_orientacao_declarada_e_medida_e_a_linha_do_cartao():
    n = cal03.resumo_da_noite(_noite("baixo", True, orientacao_do_celular="baixo",
                                     linha_de_calibracao="Calibrada: z completo"), "x")
    assert n["orientacao_declarada"] == "baixo" and n["orientacao_medida"] == "baixo"
    assert n["linha_de_calibracao"] == "Calibrada: z completo"


def test_linha_de_comando(tmp_path, capsys):
    arquivos = []
    for s, lado in enumerate(("cima", "baixo", "cima", "baixo"), start=1):
        p = tmp_path / f"via02-{s}.json"
        p.write_text(json.dumps(_noite(lado, True, semente=s)), encoding="utf-8")
        arquivos.append(str(p))
    velho = tmp_path / "velho.json"
    velho.write_text(json.dumps({"celular": {"features": {"epocas": [{"instante": "x"}]}}}), encoding="utf-8")
    saida = tmp_path / "r.json"
    assert cal03.main(arquivos + [str(velho), "--json", str(saida)]) == 0
    texto = capsys.readouterr().out
    assert "Veredito: tirou o viés" in texto and "velho.json: fora da análise" in texto
    corpo = json.loads(saida.read_text(encoding="utf-8"))
    assert corpo["veredito"]["decisao"] == "tirou o viés" and len(corpo["noites"]) == 4


def test_nenhum_arquivo_analisavel_sai_com_2(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("{}", encoding="utf-8")
    assert cal03.main([str(p)]) == 2
