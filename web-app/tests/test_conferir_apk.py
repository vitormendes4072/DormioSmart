import importlib.util
import re
from pathlib import Path
from subprocess import CompletedProcess
from zipfile import ZipFile

import pytest


_script = Path(__file__).resolve().parents[2] / "scripts" / "conferir_apk.py"
_spec = importlib.util.spec_from_file_location("conferir_apk", _script)
_conferidor = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_conferidor)

ENDERECO_FICTICIO = b"https://" + b"projeto-ficticio" + b".supabase.co"

# A versão do projeto, lida como o script lê. Fixar "1.1.5" aqui quebrava o
# teste a cada versão nova do app (R21), sem nenhum defeito no script.
VERSAO_ATUAL = re.search(
    r"""\bVERSAO_DO_APP_ANDROID\s*=\s*["']([0-9.]+)["']""",
    _conferidor.APP_ANDROID.read_text(encoding="utf-8"),
)[1]
VERSAO_DIVERGENTE = "0.0.1"


@pytest.mark.parametrize(
    ("asset", "conteudo", "versao", "saida_supabase", "saida_versao", "codigo"),
    [
        ("assets/public/assets/app.js", ENDERECO_FICTICIO, VERSAO_ATUAL, "encontrado", "confere", 0),
        ("assets/public/assets/app.js", b"", VERSAO_ATUAL, "ausente", "confere", 1),
        ("assets/public/assets/app.js", ENDERECO_FICTICIO, VERSAO_DIVERGENTE, "encontrado", "diverge", 1),
        ("assets/public/assets/outro/app.js", ENDERECO_FICTICIO, VERSAO_ATUAL, "ausente", "confere", 1),
        ("assets/public/assets/app.js", ENDERECO_FICTICIO + b".example", VERSAO_ATUAL, "ausente", "confere", 1),
    ],
)
def test_confere_apk(tmp_path, monkeypatch, capsys, asset, conteudo, versao, saida_supabase, saida_versao, codigo):
    apk = tmp_path / "app.apk"
    with ZipFile(apk, "w") as zip_apk:
        zip_apk.writestr("assets/public/versao-do-app.json", f'{{"versao":"{versao}"}}')
        zip_apk.writestr(asset, b'const config = "' + conteudo + b'";')

    def rodar(args, *, capture_output, check):
        assert args == ["aapt2", "dump", "badging", str(apk)]
        assert capture_output and check
        badging = f"package: name='app.exemplo' versionCode='7' versionName='{versao}'\n"
        return CompletedProcess(args, 0, badging.encode())

    monkeypatch.setattr(_conferidor.subprocess, "run", rodar)

    assert _conferidor.main([str(apk)]) == codigo
    saida = capsys.readouterr().out
    assert f"Supabase: endereço {saida_supabase}" in saida
    assert f"versionName do APK {saida_versao}" in saida
    assert ENDERECO_FICTICIO.decode() not in saida
