/**
 * O padrão visual das páginas públicas (UI-34, `docs/PADRAO-VISUAL.md`).
 *
 * Em 19/11 a home e a lista de espera declaravam a mesma fonte e mostravam fontes
 * diferentes: a home nunca baixou a Inter e caía na do sistema; o app baixa a Inter,
 * e a lista saía nela. Os botões do formulário saíam em peso 400, porque um reset
 * genérico vencia o do componente. Estes testes leem os arquivos de verdade e
 * reprovam se alguma dessas coisas voltar.
 */
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const landing = readFileSync(new URL("../public/landing-prototipo.html", import.meta.url), "utf8");
const lista = readFileSync(new URL("./pages/ListaDeEspera.css", import.meta.url), "utf8");
const documento = readFileSync(new URL("../../docs/PADRAO-VISUAL.md", import.meta.url), "utf8");

/** A lista de fontes, sem espaços, para comparar declarações escritas de jeitos diferentes. */
const normalizar = (familias: string) => familias.replace(/\s+/g, "").replace(/;$/, "");

function familiaDaLanding(): string {
  const body = landing.match(/body\{[^}]*?font:\s*14px\/1\.5\s*([^;}]+)/);
  expect(body, "a regra `body` da landing com `font: 14px/1.5 …` não foi achada").not.toBeNull();
  return normalizar(body![1]);
}

function familiaDaLista(): string {
  const raiz = lista.match(/\.le\s*\{[^}]*?font:\s*14px\/1\.5\s*([^;]+);/);
  expect(raiz, "a regra `.le` com `font: 14px/1.5 …` não foi achada").not.toBeNull();
  return normalizar(raiz![1]);
}

/** As declarações de uma regra, pelo seletor exato. */
function regra(css: string, seletor: string): string {
  const escapado = seletor.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const m = css.match(new RegExp(`(?:^|[}\\n])\\s*${escapado}\\s*\\{([^}]*)\\}`));
  expect(m, `regra ${seletor} não encontrada`).not.toBeNull();
  return m![1];
}

describe("a fonte é uma só nas páginas públicas", () => {
  it("a lista de espera declara exatamente a lista de fontes da home", () => {
    expect(familiaDaLista()).toBe(familiaDaLanding());
  });

  it("nenhuma das duas cita a Inter, que nenhuma delas carrega", () => {
    expect(familiaDaLanding()).not.toMatch(/Inter/i);
    expect(familiaDaLista()).not.toMatch(/Inter/i);
  });

  it("o documento do padrão traz a mesma lista de fontes", () => {
    const bloco = documento.match(/```css\s*\nfont:\s*14px\/1\.5\s*([^;]+);/);
    expect(bloco, "o bloco `css` com a fonte não foi achado no PADRAO-VISUAL.md").not.toBeNull();
    expect(normalizar(bloco![1])).toBe(familiaDaLanding());
  });
});

describe("os pesos dos componentes não são vencidos por regra genérica", () => {
  it("o reset de botão e campo não tem especificidade", () => {
    expect(lista).toMatch(/\.le\s*:where\(\s*button\s*,\s*input\s*\)\s*\{\s*font:\s*inherit;?\s*\}/);
    expect(lista).not.toMatch(/\.le\s+button\s*,\s*\.le\s+input\s*\{/);
  });

  it("o botão tem peso 800", () => {
    expect(regra(lista, ".le-btn")).toMatch(/font-weight:\s*800/);
  });

  it.each([".le-toggle", ".le-campo label"])("%s tem peso 400 declarado", (seletor) => {
    expect(regra(lista, seletor)).toMatch(/font-weight:\s*400/);
  });
});

describe("a escala segue a da home", () => {
  it("o título principal tem o tamanho e o espaçamento da home", () => {
    const home = regra(landing, ".lp-hero h1");
    const pagina = regra(lista, ".le-hero h1");
    for (const propriedade of ["font-size", "letter-spacing", "line-height"]) {
      const valor = (css: string) => css.match(new RegExp(`${propriedade}:\\s*([^;]+)`))?.[1].replace(/\s+/g, "");
      expect(valor(pagina), propriedade).toBe(valor(home));
    }
  });

  it("nenhum texto da lista fica abaixo do mínimo de 11 px", () => {
    const pequenos = [...lista.matchAll(/font-size:\s*([\d.]+)px/g)].map((m) => Number(m[1])).filter((n) => n < 11);
    expect(pequenos).toEqual([]);
  });

  it("o rótulo flutuante não encolhe abaixo de 11 px", () => {
    const escala = Number(lista.match(/translateY\(-9px\)\s*scale\(([\d.]+)\)/)?.[1]);
    const tamanho = Number(regra(lista, ".le-campo label").match(/font-size:\s*([\d.]+)px/)?.[1]);
    expect(escala * tamanho).toBeGreaterThanOrEqual(11);
  });
});

describe("os textos pequenos da home (UI-35)", () => {
  // Medido em 21/11 no navegador, a 1280 e a 390 px: estes textos da home saíam com 7 a 10 px,
  // abaixo do mínimo de 11 px do padrão (seção 3). A correção é um bloco de estilo próprio, o
  // último da página e com `#screen-landing` na frente, para vencer as regras anteriores,
  // inclusive as das larguras menores. O celular desenhado (`#sd-phone`) fica de fora: é
  // ilustração na escala do aparelho.
  const estilos = [...landing.matchAll(/<style([^>]*)>([\s\S]*?)<\/style>/g)];
  const ultimo = estilos.at(-1)!;
  const bloco = ultimo[2];

  /** O tamanho declarado para um seletor dentro do bloco, ou `null` se ele não aparece. */
  function tamanho(seletor: string): number | null {
    for (const m of bloco.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
      const seletores = m[1].replace(/@media[^{]*\{/, "");
      if (!seletores.includes(seletor)) continue;
      const fs = m[2].match(/font-size:\s*([\d.]+)px/);
      if (fs) return Number(fs[1]);
    }
    return null;
  }

  it("o bloco do UI-35 é o último estilo da página", () => {
    expect(ultimo[1]).toMatch(/id="ui-35-textos-minimos"/);
  });

  it("nenhum tamanho do bloco fica abaixo de 11 px", () => {
    const pequenos = [...bloco.matchAll(/font-size:\s*([\d.]+)px/g)].map((m) => Number(m[1])).filter((n) => n < 11);
    expect(pequenos).toEqual([]);
  });

  it("todas as regras do bloco começam por #screen-landing", () => {
    const seletores = [...bloco.replace(/\/\*[\s\S]*?\*\//g, "").matchAll(/([^{}]+)\{[^{}]*\}/g)]
      .flatMap((m) => m[1].replace(/@media[^{]*\{/, "").split(/,(?![^(]*\))/))
      .map((s) => s.trim())
      .filter(Boolean);
    expect(seletores.length).toBeGreaterThan(0);
    expect(seletores.filter((s) => !s.startsWith("#screen-landing"))).toEqual([]);
  });

  it.each([
    [".lp-kicker", 11],
    [".lp-overline", 11],
    [".lp-spec-row span", 12],
    [".lp-spec-note", 12],
    [".lp-footer", 11.5],
    [".lp-limit-box p", 11.5],
    [".lp-proofbar small", 11],
    [".lp-proof-icon", 11],
    [".lp-flow-number", 11],
    [".beta-panel-label", 11],
    [".lp-demo-chip", 11],
    [".lp-play-symbol", 11],
    [".lp-sim-chart-head b", 11],
    [".lp-state", 11],
    [".lp-sim-disclaimer>span", 11],
    [".lp-final-cta p", 11],
    [".sd-quicknav-heading>span", 11],
    [".sd-quicknav-num", 11],
    [".sdx-switch", 11],
    [".sdx-leader-num", 11],
    [".sdx-leader-name", 11],
    [".sdx-fact-number", 11],
    [".sdx-fact small", 11],
    [".sdm-eyebrow", 11],
    [".sdm-badge", 11],
    [".sdm-segments button", 11],
    [".sdm-visual-toolbar button", 11],
    [".public-btn", 11],
  ])("%s tem %s px no bloco", (seletor, px) => {
    expect(tamanho(seletor)).toBe(px);
  });

  it("o botão do cabeçalho só é tocado na largura em que encolhia (até 650 px)", () => {
    expect(bloco).toMatch(/@media\(max-width:650px\)\{#screen-landing \.public-actions \.public-btn\{font-size:11px\}\}/);
  });
});

describe("o ícone da aba (favicon)", () => {
  const indice = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  const icones = (html: string) => [...html.matchAll(/<link[^>]*rel="icon"[^>]*>/g)].map((m) => m[0].match(/href="([^"]+)"/)?.[1]);

  it.each([["o app e a lista de espera (index.html)", () => indice], ["a landing", () => landing]])(
    "%s declara o .ico e o PNG de 32 px",
    (_, html) => {
      expect(icones(html())).toEqual(expect.arrayContaining(["/favicon.ico", "/favicon-32.png"]));
    },
  );

  it("os arquivos declarados existem em public/", () => {
    for (const caminho of new Set([...icones(indice), ...icones(landing)])) {
      expect(() => readFileSync(new URL(`../public${caminho}`, import.meta.url)), String(caminho)).not.toThrow();
    }
  });
});

describe("os ícones do app instalado (manifest)", () => {
  const manifesto = JSON.parse(readFileSync(new URL("../public/manifest.json", import.meta.url), "utf8")) as {
    icons: { src: string; purpose?: string }[];
  };

  it("todo ícone do manifest existe em public/", () => {
    for (const { src } of manifesto.icons) {
      expect(() => readFileSync(new URL(`../public${src}`, import.meta.url)), src).not.toThrow();
    }
  });

  it("o recortável do Android (maskable) é um arquivo próprio, com margem, e não o mesmo do `any`", () => {
    const recortaveis = manifesto.icons.filter((i) => i.purpose === "maskable").map((i) => i.src);
    const comuns = manifesto.icons.filter((i) => i.purpose !== "maskable").map((i) => i.src);
    expect(recortaveis.length).toBeGreaterThan(0);
    expect(recortaveis.filter((src) => comuns.includes(src))).toEqual([]);
  });
});

describe("a grafia do nome (BRAND-05)", () => {
  // O nome é "Smart Dormio", em duas palavras (docs/marca/README.md). Os ids internos da landing
  // (`smartdormio-landing-…`) e o nome do arquivo baixado pelo simulador não são texto para o usuário.
  const visivel = (html: string) => html
    .replace(/<script[\s\S]*?<\/script>|<style[\s\S]*?<\/style>/g, "")
    .replace(/\bid="[^"]*"/g, "");
  const indice = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  const manifesto = readFileSync(new URL("../public/manifest.json", import.meta.url), "utf8");

  it.each([["a landing", () => visivel(landing)], ["o index.html", () => visivel(indice)], ["o manifest", () => manifesto]])(
    "%s não escreve o nome junto",
    (_, texto) => {
      expect(texto()).not.toMatch(/SmartDormio/i);
    },
  );
});
