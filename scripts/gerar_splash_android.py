"""Gera a tela de abertura do app Android com a marca (APP-18).

O Android 10 e 11 mostram, ao abrir o app, o `splash.png` inteiro como fundo da
janela (`AppTheme.NoActionBarLaunch`, em `res/values/styles.xml`). Até o
`APP-18` era a imagem padrão do Capacitor. Este script refaz os 11 arquivos com
a marca empilhada azul (`docs/marca/logos/smart-dormio-empilhado-azul.png`)
centralizada sobre branco, nas orientações e densidades que o Android procura.

A largura da marca é 40% do lado menor da imagem, a mesma em retrato e em
paisagem. O Android 12 em diante não usa estes arquivos: mostra o ícone do app
sobre `windowSplashScreenBackground`, que o `styles.xml` declara branco para as
duas aberturas ficarem iguais.

Reproduzível: rodar de novo se a marca mudar.

    python scripts/gerar_splash_android.py

O `frontend/src/lib/appAndroid.test.ts` confere tamanhos, fundo e marca.
"""

from pathlib import Path

from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
LOGO = RAIZ / "docs" / "marca" / "logos" / "smart-dormio-empilhado-azul.png"
RES = RAIZ / "frontend" / "android" / "app" / "src" / "main" / "res"

# Pasta -> (largura, altura). Os tamanhos são os que o Capacitor gera, para que
# nenhuma densidade deixe de existir ou mude de proporção.
TAMANHOS = {
    "drawable": (480, 320),
    "drawable-land-mdpi": (480, 320),
    "drawable-land-hdpi": (800, 480),
    "drawable-land-xhdpi": (1280, 720),
    "drawable-land-xxhdpi": (1600, 960),
    "drawable-land-xxxhdpi": (1920, 1280),
    "drawable-port-mdpi": (320, 480),
    "drawable-port-hdpi": (480, 800),
    "drawable-port-xhdpi": (720, 1280),
    "drawable-port-xxhdpi": (960, 1600),
    "drawable-port-xxxhdpi": (1280, 1920),
}

FRACAO_DO_LADO_MENOR = 0.40
BRANCO = (255, 255, 255)


def marca_recortada() -> Image.Image:
    """A marca sem a margem transparente do arquivo, para medir só o desenho."""
    logo = Image.open(LOGO).convert("RGBA")
    return logo.crop(logo.getbbox())


def gerar(largura: int, altura: int, marca: Image.Image) -> Image.Image:
    alvo = round(min(largura, altura) * FRACAO_DO_LADO_MENOR)
    escala = alvo / marca.width
    reduzida = marca.resize((alvo, round(marca.height * escala)), Image.Resampling.LANCZOS)
    tela = Image.new("RGBA", (largura, altura), BRANCO + (255,))
    pos = ((largura - reduzida.width) // 2, (altura - reduzida.height) // 2)
    tela.alpha_composite(reduzida, pos)
    return tela.convert("RGB")


def main() -> None:
    marca = marca_recortada()
    for pasta, (largura, altura) in TAMANHOS.items():
        destino = RES / pasta / "splash.png"
        gerar(largura, altura, marca).save(destino, optimize=True)
        print(f"{destino.relative_to(RAIZ)}  {largura}x{altura}")


if __name__ == "__main__":
    main()
