"""Confere a configuração do login e a versão nativa de um APK de release."""

import argparse
import re
import subprocess
from pathlib import Path
from zipfile import BadZipFile, ZipFile


APP_ANDROID = Path(__file__).resolve().parents[1] / "frontend/src/lib/appAndroid.ts"
ASSET_JS = re.compile(r"assets/public/assets/[^/]+\.js")
SUPABASE = re.compile(rb"https://[a-z0-9-]+\.supabase\.co(?=[/'\"`?#:\s]|$)")
VERSAO_BADGING = re.compile(rb"^package: .*?\bversionName='([^']+)'", re.MULTILINE)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apk", type=Path)
    parser.add_argument("--aapt2", default="aapt2", help="executável do Android SDK Build-Tools")
    parser.add_argument("--versao-esperada", help="sobrescreve a versão do projeto para conferir releases antigas")
    args = parser.parse_args(argv)

    try:
        with ZipFile(args.apk) as apk:
            encontrou_supabase = any(
                SUPABASE.search(apk.read(arquivo))
                for arquivo in apk.infolist()
                if ASSET_JS.fullmatch(arquivo.filename)
            )
    except (BadZipFile, OSError, RuntimeError):
        print("Falha: não foi possível ler o APK como ZIP.")
        return 1

    if encontrou_supabase:
        print("Supabase: endereço encontrado no JavaScript do APK.")
    else:
        print("Supabase: endereço ausente no JavaScript do APK.")

    esperada = args.versao_esperada
    if esperada is None:
        match = re.search(r"""\bVERSAO_DO_APP_ANDROID\s*=\s*["']([0-9.]+)["']""", APP_ANDROID.read_text(encoding="utf-8"))
        if not match:
            print("Falha: VERSAO_DO_APP_ANDROID não encontrada.")
            return 1
        esperada = match[1]

    try:
        badging = subprocess.run(
            [args.aapt2, "dump", "badging", str(args.apk.resolve())],
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        print("Falha: aapt2 não conseguiu ler o manifesto do APK. Confira o Android SDK Build-Tools.")
        return 1

    versao = VERSAO_BADGING.search(badging.stdout)
    if versao is None or versao[1] != esperada.encode("utf-8"):
        print("Versão: versionName do APK diverge da versão esperada ou está ausente.")
        return 1

    print("Versão: versionName do APK confere.")
    return int(not encontrou_supabase)


if __name__ == "__main__":
    raise SystemExit(main())
