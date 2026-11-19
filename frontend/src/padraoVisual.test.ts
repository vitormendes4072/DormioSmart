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
