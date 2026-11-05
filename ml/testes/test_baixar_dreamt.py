"""Integridade da DREAMT com arquivos artificiais, sem redistribuir dados."""
import hashlib
from pathlib import Path
import subprocess
import sys

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "ferramentas/baixar_dreamt.py"
CSV_ESPERADOS = [f"data_64Hz/S{i:03d}_whole_df.csv"
                 for i in range(2, 104) if i not in (41, 60)]
METADADOS = ("Metadata.txt", "participant_info.csv", "LICENSE.txt")


@pytest.fixture
def dados(tmp_path):
    linhas = []
    for nome in [*CSV_ESPERADOS, *METADADOS]:
        p = tmp_path / nome
        p.parent.mkdir(parents=True, exist_ok=True)
        conteudo = ("conteudo artificial: " + nome + "\n").encode("utf-8")
        p.write_bytes(conteudo)
        linhas.append(f"{hashlib.sha256(conteudo).hexdigest()}  {nome}")
    (tmp_path / "SHA256SUMS.txt").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return tmp_path


def executar(pasta):
    return subprocess.run([sys.executable, str(SCRIPT), "--pasta", str(pasta)],
                          capture_output=True, text=True, encoding="utf-8")


def tirar_entrada(pasta, nome):
    p = pasta / "SHA256SUMS.txt"
    linhas = [l for l in p.read_text(encoding="utf-8").splitlines()
              if l.split()[-1] != nome]
    p.write_text("\n".join(linhas) + "\n", encoding="utf-8")


def test_103_arquivos_integros_passam(dados):
    r = executar(dados)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "conferem 103" in r.stdout


def test_arquivo_ausente_e_acusado_pelo_caminho(dados):
    (dados / CSV_ESPERADOS[0]).unlink()
    r = executar(dados)
    assert r.returncode == 1
    assert "FALTA: " + CSV_ESPERADOS[0] in r.stdout


def test_arquivo_adulterado_e_acusado_pela_soma(dados):
    (dados / CSV_ESPERADOS[0]).write_bytes(b"adulterado")
    r = executar(dados)
    assert r.returncode == 1
    assert "SOMA NÃO CONFERE: " + CSV_ESPERADOS[0] in r.stdout


def test_manifesto_ausente_reprova(dados):
    (dados / "SHA256SUMS.txt").unlink()
    r = executar(dados)
    assert r.returncode == 1
    assert "Falta" in r.stderr


def test_manifesto_vazio_nao_pode_passar_no_vazio(tmp_path):
    (tmp_path / "SHA256SUMS.txt").write_text("", encoding="utf-8")
    assert executar(tmp_path).returncode == 1


def test_manifesto_sem_um_csv_reprova_mesmo_com_arquivo_presente(dados):
    tirar_entrada(dados, CSV_ESPERADOS[0])
    assert executar(dados).returncode == 1


@pytest.mark.parametrize("nome", METADADOS)
def test_manifesto_sem_metadado_reprova(dados, nome):
    tirar_entrada(dados, nome)
    assert executar(dados).returncode == 1


def test_103_entradas_com_id_trocado_nao_substituem_conjunto_oficial(dados):
    origem = dados / CSV_ESPERADOS[0]
    destino = dados / "data_64Hz/S999_whole_df.csv"
    origem.rename(destino)
    p = dados / "SHA256SUMS.txt"
    p.write_text(p.read_text(encoding="utf-8").replace(CSV_ESPERADOS[0],
                 "data_64Hz/S999_whole_df.csv"), encoding="utf-8")
    assert executar(dados).returncode == 1


def test_linha_malformada_no_manifesto_reprova(dados):
    p = dados / "SHA256SUMS.txt"
    p.write_text(p.read_text(encoding="utf-8") + "linha-invalida\n", encoding="utf-8")
    assert executar(dados).returncode == 1


def test_entrada_duplicada_no_manifesto_reprova(dados):
    p = dados / "SHA256SUMS.txt"
    texto = p.read_text(encoding="utf-8")
    p.write_text(texto + texto.splitlines()[0] + "\n", encoding="utf-8")
    assert executar(dados).returncode == 1


def test_manifesto_oficial_pode_listar_100hz_fora_do_escopo(dados):
    p = dados / "SHA256SUMS.txt"
    p.write_text(p.read_text(encoding="utf-8") + "0" * 64 +
                 "  data_100Hz/S002_PSG_df.csv\n", encoding="utf-8")
    assert executar(dados).returncode == 0
