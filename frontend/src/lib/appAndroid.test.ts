// @vitest-environment jsdom
// APP-17: o APK novo com a marca e o download publicado na landing.
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { inflateSync } from "node:zlib";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { URL_DO_APK, VERSAO_DO_APP_ANDROID } from "./appAndroid";

const ler = (caminho: string) => readFileSync(resolve(caminho), "utf8");
const gradle = ler("android/app/build.gradle");

describe("a versão do APK", () => {
  it("é a mesma no build.gradle e no que a landing anuncia", () => {
    expect(gradle).toContain(`versionName "${VERSAO_DO_APP_ANDROID}"`);
  });

  it("subiu o versionCode acima do 1 do primeiro APK (o Android recusa instalar por cima um número igual)", () => {
    const codigo = Number(/versionCode (\d+)/.exec(gradle)?.[1]);
    expect(codigo).toBeGreaterThanOrEqual(2);
  });
});

describe("o download na landing completa", () => {
  const pagina = new DOMParser().parseFromString(ler("public/landing-prototipo.html"), "text/html");
  const secao = pagina.querySelector("#app-android");

  it("é um link para o GitHub Releases, aberto fora do iframe isolado", () => {
    const link = secao?.querySelector<HTMLAnchorElement>("a.beta-download");
    expect(link?.getAttribute("href")).toBe(URL_DO_APK);
    expect(link?.getAttribute("target")).toBe("_top");
    expect(secao?.querySelector("button.beta-download")).toBeNull();
  });

  it("anuncia a versão publicada e avisa da instalação fora da Play Store", () => {
    expect(secao?.textContent).toContain(`Versão ${VERSAO_DO_APP_ANDROID}`);
    expect(secao?.textContent).toContain("permitir a instalação desta fonte");
    expect(secao?.textContent).not.toContain("indisponível");
  });

  it("aponta para o arquivo de uma release, e não para uma página que muda", () => {
    expect(URL_DO_APK).toMatch(/^https:\/\/github\.com\/[^/]+\/[^/]+\/releases\/latest\/download\/[a-z-]+\.apk$/);
  });
});

describe("o app instalado", () => {
  it("chama-se Smart Dormio na tela inicial do celular (BRAND-05)", () => {
    expect(ler("android/app/src/main/res/values/strings.xml")).toContain('<string name="app_name">Smart Dormio</string>');
    expect(ler("capacitor.config.ts")).toContain('appName: "Smart Dormio"');
  });

  // Os ícones padrão do Capacitor, como estavam até o APK 1.0.0.
  const PADRAO_DO_CAPACITOR = new Set([
    "0166fc333074c373fbd0ce6b5defd71552166165ac778121ca9c9dff6b83f0fc",
    "1ee4cd9ff371dcb2e3938097e434f6fb8731688ed7165e61fc63693ad5b2f455",
    "27ed3603010ebc278f64f8645741ab132ff517abb5308eb9df6c8e42a48956b2",
    "32baa10d2632a4417454a579f992bd640e0a3cec79321423559b2c9940de58a9",
    "40911a00922868686854a4804b93fd6e56b503664696de03f450bff690affb6d",
    "4a82bc1e9923576275869998925ce0ae021a79aa18b24a0dd87ad6b61ca85053",
    "58e78a618778926b1f6d9472a6468de878de8530970934e94aab5ba4ba08cc00",
    "6f88083b8166cc559102f7044688de7525287632ebe09ac45d001ac8bf4b3eae",
    "72b71c3581ca3b5a23b1c168d69b9d855b3f184fa079902a01f088eb4f0607d5",
    "87cb2f2ffe992652bb4fa768c73719a37b5852ab17fbf8e170e888f7a42b0761",
    "ab93096331e7cd8ec379f73f1e9adcaaa9ee1115c9f4ff10411a811fb9700174",
    "bd24fd383253bf8d43f0a81f11c071d76d1d555114376dd647cd9fb38fa0a9da",
    "bfcc1b0fa931b14bb241372c76ab4f04374b67d02363c98d9cb12edfdacdf5f3",
    "d35dbfff175b83c13ef59cf924abfc810f7b6a158595d7417c5498ea8c7c7ed1",
    "ed346eb1e3f0280f15709393705899b3ff55c20b88f4e0308006b3c33cf5fe14",
  ]);
  const DENSIDADES = { mdpi: 1, hdpi: 1.5, xhdpi: 2, xxhdpi: 3, xxxhdpi: 4 } as const;
  const ICONES = { ic_launcher: 48, ic_launcher_round: 48, ic_launcher_foreground: 108 } as const;

  it.each(Object.entries(DENSIDADES))("tem os ícones da marca em %s, no tamanho da densidade", (densidade, fator) => {
    for (const [nome, dp] of Object.entries(ICONES)) {
      const png = readFileSync(resolve(`android/app/src/main/res/mipmap-${densidade}/${nome}.png`));
      expect(PADRAO_DO_CAPACITOR.has(createHash("sha256").update(png).digest("hex")), `${densidade}/${nome}`).toBe(false);
      // Largura e altura ficam no cabeçalho IHDR do PNG, nos bytes 16 a 23.
      expect([png.readUInt32BE(16), png.readUInt32BE(20)], `${densidade}/${nome}`).toEqual([dp * fator, dp * fator]);
    }
  });
});

// APP-18: o nome e a marca dentro do app.
describe("os textos das telas do app", () => {
  // As telas que só existem no app Android, e o texto do consentimento, que o
  // app mostra antes da primeira noite. ✏️ 22/11 (`LGPD-15`): o consentimento
  // ficava de fora porque mudá-lo é mudar a versão nos três lugares e pedir o
  // aceite de novo; o autor decidiu mudar, e ele entrou.
  const TELAS = ["src/components/CartaoDaNoite.tsx", "src/pages/Noite.tsx", "src/lib/consentimento.ts"];

  it.each(TELAS)("%s chama o produto de Smart Dormio, e não de \"o Dormio\"", (tela) => {
    const soltos = ler(tela).match(/(?<!Smart )\bDormio\b/g) ?? [];
    expect(soltos, tela).toEqual([]);
  });

  it("a notificação da noite chama o produto de Smart Dormio (UI-41 b)", () => {
    // O serviço Java ficou fora da troca do APP-18. Só os literais contam: os
    // nomes internos (`DormioNoite`, `dormio:noite`) ninguém vê.
    const servico = ler("android/app/src/main/java/app/dormiosmart/coleta/ServicoDaNoite.java");
    const literais = [...servico.matchAll(/"((?:[^"\\]|\\.)*)"/g)].map((m) => m[1]);
    expect(literais.some((texto) => texto.includes("Smart Dormio"))).toBe(true);
    expect(literais.filter((texto) => /(?<!Smart )\bDormio\b/.test(texto))).toEqual([]);
  });

  it("o canal da notificação é atualizado também em quem já tem o app (UI-41 b)", () => {
    const servico = ler("android/app/src/main/java/app/dormiosmart/coleta/ServicoDaNoite.java");
    expect(servico).not.toMatch(/getNotificationChannel\(CANAL\)\s*==\s*null/);
    expect(servico).toMatch(/createNotificationChannel\(/);
  });
});

/** Decodifica um PNG de 8 bits RGB ou RGBA, sem entrelaçamento: o que o Android usa aqui. */
function lerPng(caminho: string) {
  const png = readFileSync(resolve(caminho));
  const largura = png.readUInt32BE(16);
  const altura = png.readUInt32BE(20);
  const [profundidade, tipo, , , entrelacado] = png.subarray(24, 29);
  if (profundidade !== 8 || (tipo !== 2 && tipo !== 6) || entrelacado !== 0) {
    throw new Error(`${caminho}: PNG fora do formato esperado (profundidade ${profundidade}, tipo ${tipo})`);
  }
  const canais = tipo === 6 ? 4 : 3;
  const partes: Buffer[] = [];
  for (let i = 8; i < png.length; ) {
    const tamanho = png.readUInt32BE(i);
    if (png.toString("latin1", i + 4, i + 8) === "IDAT") partes.push(png.subarray(i + 8, i + 8 + tamanho));
    i += tamanho + 12;
  }
  const bruto = inflateSync(Buffer.concat(partes));
  const linha = largura * canais;
  const px = Buffer.alloc(linha * altura);
  for (let y = 0; y < altura; y++) {
    const filtro = bruto[y * (linha + 1)];
    for (let x = 0; x < linha; x++) {
      const v = bruto[y * (linha + 1) + 1 + x];
      const a = x >= canais ? px[y * linha + x - canais] : 0;
      const b = y > 0 ? px[(y - 1) * linha + x] : 0;
      const c = x >= canais && y > 0 ? px[(y - 1) * linha + x - canais] : 0;
      const paeth = () => {
        const p = a + b - c;
        const [pa, pb, pc] = [Math.abs(p - a), Math.abs(p - b), Math.abs(p - c)];
        return pa <= pb && pa <= pc ? a : pb <= pc ? b : c;
      };
      const previsto = [0, a, b, (a + b) >> 1, paeth()][filtro];
      px[y * linha + x] = (v + previsto) & 0xff;
    }
  }
  const rgb = (x: number, y: number) => [...px.subarray(y * linha + x * canais, y * linha + x * canais + 3)];
  return { largura, altura, rgb };
}

describe("a tela de abertura do app (Android 10 e 11)", () => {
  // O `splash.png` padrão do Capacitor, como estava até o APK 1.1.0.
  const PADRAO_DO_CAPACITOR = new Set([
    "07fa579e1c83e04ba7f9cbcbfcf41b68e15fe3638f2c44a04e58b809103e6b69",
    "08cc34ad7713fe7ed58bceaa37b2387b670c53cd60264b4bd6442db3098e75dc",
    "0c7f1212f25b7b90e9a6e1d320013e4ff3d3e03e634cbb07b7b7981cac51627f",
    "22f87e1e3bc89aa01a7dbc39c9a4db058cd0bf4ad3fe9f55712bf69eb997f4bf",
    "3db071a03b2f8ffe0dfd4170fc59842d53cd15bba5e88af59401d58efabf7827",
    "42aa26392546fcdee1b8d3ac6d4b41bfcceb41dc6a4f3a3c30c24a8a8f4db862",
    "5cf98b4451bd99b20df26f9e608a46946118be6b0ae90762f9ca1786a30c76ff",
    "60393ce8636fd263e4e1fea3fd4ab2de948c6295e898fda9b50ac4e5283be809",
    "b73049cb37fe76d6c11b87a796766bf6af0c85483b31eb6a921657b0d764a4b9",
    "c5015f4ba3628392b538386c5e210f0b94f352a3160adab934fd0311972137ca",
  ]);
  // Os mesmos tamanhos que o Capacitor gera (`scripts/gerar_splash_android.py`).
  const TAMANHOS: Record<string, [number, number]> = {
    drawable: [480, 320],
    "drawable-land-mdpi": [480, 320],
    "drawable-land-hdpi": [800, 480],
    "drawable-land-xhdpi": [1280, 720],
    "drawable-land-xxhdpi": [1600, 960],
    "drawable-land-xxxhdpi": [1920, 1280],
    "drawable-port-mdpi": [320, 480],
    "drawable-port-hdpi": [480, 800],
    "drawable-port-xhdpi": [720, 1280],
    "drawable-port-xxhdpi": [960, 1600],
    "drawable-port-xxxhdpi": [1280, 1920],
  };
  const AZUL_DA_MARCA = [0x35, 0xa2, 0xef];
  const perto = (cor: number[], alvo: number[]) => cor.every((v, i) => Math.abs(v - alvo[i]) <= 6);

  it.each(Object.entries(TAMANHOS))("%s tem a marca azul no centro, sobre branco", (pasta, [largura, altura]) => {
    const caminho = `android/app/src/main/res/${pasta}/splash.png`;
    const hash = createHash("sha256").update(readFileSync(resolve(caminho))).digest("hex");
    expect(PADRAO_DO_CAPACITOR.has(hash), `${pasta}: ainda é a imagem do Capacitor`).toBe(false);

    const img = lerPng(caminho);
    expect([img.largura, img.altura]).toEqual([largura, altura]);
    for (const [x, y] of [[0, 0], [largura - 1, 0], [0, altura - 1], [largura - 1, altura - 1]]) {
      expect(img.rgb(x, y), `${pasta}: canto (${x}, ${y})`).toEqual([255, 255, 255]);
    }

    // A faixa horizontal do meio: onde há desenho, quanto dele é o azul da marca,
    // e se a largura do desenho é 40% do lado menor.
    let esquerda = largura;
    let direita = -1;
    let azuis = 0;
    for (let y = Math.floor(altura * 0.4); y < Math.ceil(altura * 0.6); y++) {
      for (let x = 0; x < largura; x++) {
        const cor = img.rgb(x, y);
        if (cor.some((v) => v < 240)) {
          esquerda = Math.min(esquerda, x);
          direita = Math.max(direita, x);
        }
        if (perto(cor, AZUL_DA_MARCA)) azuis++;
      }
    }
    expect(azuis, `${pasta}: pixels no azul da marca`).toBeGreaterThan(0);
    const esperado = Math.min(largura, altura) * 0.4;
    expect(Math.abs(direita - esquerda + 1 - esperado), `${pasta}: largura da marca`).toBeLessThanOrEqual(esperado * 0.05);
    expect(Math.abs((esquerda + direita) / 2 - largura / 2), `${pasta}: centralizada`).toBeLessThanOrEqual(2);
  });
});

describe("a tela de abertura do app (Android 12 em diante)", () => {
  it("é branca como a do Android 10 e 11, com o ícone do app", () => {
    const estilos = ler("android/app/src/main/res/values/styles.xml");
    const abertura = /<style name="AppTheme\.NoActionBarLaunch"[^>]*>([\s\S]*?)<\/style>/.exec(estilos)?.[1] ?? "";
    // Sem a cor, o Theme.SplashScreen usa o fundo do sistema, que fica escuro
    // no modo escuro. O Capacitor troca o tema sozinho (`setTheme` na
    // BridgeActivity), sem `installSplashScreen`: o `postSplashScreenTheme`
    // não teria efeito, e por isso não está aqui.
    expect(abertura).toContain('<item name="windowSplashScreenBackground">#FFFFFF</item>');
  });
});
