import importlib.util
from pathlib import Path
from subprocess import CompletedProcess

import pytest


_script = Path(__file__).resolve().parents[2] / "scripts" / "conferir_docs_versionados.py"
_spec = importlib.util.spec_from_file_location("conferir_docs_versionados", _script)
_conferidor = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_conferidor)


def test_check_ignore_com_erro_fatal_reprova_e_preserva_diagnostico(monkeypatch, tmp_path):
    def rodar(args, **kwargs):
        return CompletedProcess(args, 128, b"", b"fatal: indice ilegivel\n")

    monkeypatch.setattr(_conferidor.subprocess, "run", rodar)
    with pytest.raises(RuntimeError, match=r"git check-ignore.*128.*fatal: indice ilegivel"):
        _conferidor.ignorados(tmp_path, ["docs/local.md"])


def test_check_ignore_sem_correspondencia_retorna_vazio(monkeypatch, tmp_path):
    def rodar(args, **kwargs):
        return CompletedProcess(args, 1, b"", b"")

    monkeypatch.setattr(_conferidor.subprocess, "run", rodar)
    assert _conferidor.ignorados(tmp_path, ["docs/local.md"]) == set()
