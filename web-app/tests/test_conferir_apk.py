import importlib.util
from pathlib import Path
from subprocess import CompletedProcess
from zipfile import ZipFile

import pytest


_script = Path(__file__).resolve().parents[2] / "scripts" / "conferir_apk.py"
_spec = importlib.util.spec_from_file_location("conferir_apk", _script)
_conferidor = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_conferidor)

ENDERECO_FICTICIO = b"https://" + b"projeto-ficticio" + b".supabase.co"


@pytest.mark.parametrize(
    ("asset", "conteudo", "versao", "saida_supabase", "saida_versao", "codigo"),
    [
        ("assets/public/assets/app.js", ENDERECO_FICTICIO, "1.1.5", "encontrado", "confere", 0),
        ("assets/public/assets/app.js", b"", "1.1.5", "ausente", "confere", 1),
        ("assets/public/assets/app.js", ENDERECO_FICTICIO, "1.1.4", "encontrado", "diverge", 1),
        ("assets/public/assets/outro/app.js", ENDERECO_FICTICIO, "1.1.5", "ausente", "confere", 1),
        ("assets/public/assets/app.js", ENDERECO_FICTICIO + b".example", "1.1.5", "ausente", "confere", 1),
    ],
)
def test_confere_apk(tmp_path, monkeypatch, capsys, asset, conteudo, versao, saida_supabase, saida_versao, codigo):
    apk = tmp_path / "app.apk"
    with ZipFile(apk, "w") as zip_apk:
        zip_apk.writestr("assets/public/versao-do-app.json", '{"versao":"1.1.5"}')
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
