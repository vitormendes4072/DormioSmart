"""Controle do instrumento da ML-14: entradas artificiais e snapshot real."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

from ferramentas.auditar_f1 import NOME_SAIDA, PADRAO, auditar


def salvar(pasta, dados):
    p = pasta / "experimento.json"
    p.write_text(json.dumps(dados), encoding="utf-8")
    return p


def test_audita_nan_aninhado_sem_alterar_original(tmp_path):
    p = salvar(tmp_path, {"resultados": [{"vp": 0, "vn": 0, "fp": 1, "fn": 1,
                                        "f1_sono": float("nan"), "f1_vigilia": float("nan")}]})
    antes = p.read_bytes()
    r = auditar(tmp_path)
    assert r["n_divergencias"] == 2
    assert {d["f1_recalculado"] for d in r["divergencias"]} == {0.0}
    assert r["divergencias"][0]["caminho"] == "$.resultados[0].f1_sono"
    assert r["divergencias"][0]["estado_anterior"] == "NaN"
    json.dumps(r, allow_nan=False)
    assert p.read_bytes() == antes


@pytest.mark.parametrize("linha", [
    {"vp": 1, "vn": 0, "fp": 0, "fn": 0, "f1_sono": 1, "f1_vigilia": float("nan")},
    {"vp": 0, "vn": 0, "fp": 1, "fn": 1, "f1_sono": 0, "f1_vigilia": 0},
    {"vp": 1, "vn": 2, "fp": 0, "fn": 1, "f1_sono": 2/3, "f1_vigilia": 4/5},
])
def test_nao_acusa_resultado_correto_ou_ausencia_legitima(tmp_path, linha):
    salvar(tmp_path, linha)
    assert auditar(tmp_path)["n_divergencias"] == 0


def test_acusa_valor_finito_incorreto(tmp_path):
    salvar(tmp_path, {"vp": 0, "vn": 0, "fp": 1, "fn": 1, "f1_sono": 1.0})
    d = auditar(tmp_path)["divergencias"][0]
    assert d["valor_anterior"] == 1.0 and d["f1_recalculado"] == 0.0


def test_sem_contagens_e_declarado_sem_inventar_valor(tmp_path):
    salvar(tmp_path, {"media": {"f1_sono": 0.8}})
    r = auditar(tmp_path)
    assert r["n_valores_recalculaveis"] == 0
    assert r["sem_contagens"] == [{"arquivo": "experimento.json", "caminho": "$.media.f1_sono"}]


def test_contagens_invalidas_nao_produzem_relatorio_plausivel(tmp_path):
    salvar(tmp_path, {"vp": True, "vn": 0, "fp": 1, "fn": 1, "f1_sono": 1})
    with pytest.raises(ValueError, match="contagens invalidas"):
        auditar(tmp_path)


def test_cli_confere_snapshot_e_acusa_alteracao_da_fonte(tmp_path):
    salvar(tmp_path, {"vp": 0, "vn": 0, "fp": 1, "fn": 1, "f1_sono": float("nan")})
    script = Path(__file__).resolve().parents[1] / "ferramentas" / "auditar_f1.py"
    cmd = [sys.executable, str(script), "--pasta", str(tmp_path)]
    assert subprocess.run(cmd, capture_output=True).returncode == 0
    assert (tmp_path / NOME_SAIDA).is_file()
    assert subprocess.run(cmd + ["--conferir"], capture_output=True).returncode == 0
    # Controle positivo: mudar a matriz torna o snapshot obsoleto.
    salvar(tmp_path, {"vp": 1, "vn": 0, "fp": 0, "fn": 0, "f1_sono": 1})
    assert subprocess.run(cmd + ["--conferir"], capture_output=True).returncode == 1


def test_snapshot_versionado_bate_com_os_arquivos_historicos():
    gravado = json.loads((PADRAO / NOME_SAIDA).read_text(encoding="utf-8"))
    assert auditar(PADRAO) == gravado


def test_hash_e_resultado_independem_do_fim_de_linha_do_checkout(tmp_path):
    p = salvar(tmp_path, {"vp": 1, "vn": 1, "fp": 0, "fn": 0, "f1_sono": 1.0})
    p.write_bytes(p.read_bytes() + bytes([10]))
    antes = auditar(tmp_path)
    p.write_bytes(p.read_bytes().replace(bytes([10]), bytes([13, 10])))
    assert auditar(tmp_path) == antes
