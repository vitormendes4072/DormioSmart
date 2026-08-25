import { afterEach, describe, expect, it, vi } from "vitest";

import { registrarServiceWorker } from "./instalacao";

afterEach(() => vi.unstubAllGlobals());

/** Navegador falso: registra o que foi pedido e permite falhar sob demanda. */
function navegador(opcoes: { falha?: boolean; suporta?: boolean } = {}) {
  const { falha = false, suporta = true } = opcoes;
  const registros: string[] = [];
  const ouvintes: Record<string, () => void> = {};

  vi.stubGlobal("navigator", suporta
    ? {
        serviceWorker: {
          register: (caminho: string) => {
            registros.push(caminho);
            return falha ? Promise.reject(new Error("bloqueado")) : Promise.resolve({});
          },
        },
      }
    : {});
  vi.stubGlobal("window", {
    addEventListener: (evento: string, fn: () => void) => {
      ouvintes[evento] = fn;
    },
  });

  return { registros, carregar: () => ouvintes["load"]?.() };
}

describe("registrarServiceWorker", () => {
  it("nao registra em desenvolvimento", () => {
    // Service worker ativo em dev e a forma mais rapida de depurar codigo que
    // ja foi corrigido.
    const n = navegador();
    registrarServiceWorker(true);
    n.carregar();
    expect(n.registros).toEqual([]);
  });

  it("registra em producao, e so depois do load", () => {
    // Registrar durante o carregamento disputa banda com o proprio app.
    const n = navegador();
    registrarServiceWorker(false);
    expect(n.registros).toEqual([]);
    n.carregar();
    expect(n.registros).toEqual(["/sw.js"]);
  });

  it("nao quebra quando o navegador nao suporta", () => {
    const n = navegador({ suporta: false });
    expect(() => registrarServiceWorker(false)).not.toThrow();
    expect(n.registros).toEqual([]);
  });

  it("engole a falha de registro", async () => {
    // Navegacao privada ou politica corporativa bloqueiam. O app funciona
    // igual — so nao oferece instalacao.
    const n = navegador({ falha: true });
    registrarServiceWorker(false);
    expect(() => n.carregar()).not.toThrow();
    await Promise.resolve();
  });
});

describe("manifest e service worker (arquivos servidos)", () => {
  it("o manifest declara o minimo que o Chrome exige para instalar", async () => {
    const { readFileSync } = await import("node:fs");
    const m = JSON.parse(
      readFileSync(new URL("../../public/manifest.json", import.meta.url), "utf-8"),
    );

    expect(m.name).toBeTruthy();
    expect(m.short_name).toBeTruthy();
    expect(m.start_url).toBeTruthy();
    expect(m.display).toBe("standalone");

    const tamanhos = m.icons.map((i: { sizes: string }) => i.sizes);
    expect(tamanhos).toContain("192x192");
    expect(tamanhos).toContain("512x512");
    // Android recorta o icone em formas variadas; sem um `maskable`, o
    // sistema aplica a propria moldura por cima e o desenho fica torto.
    expect(m.icons.some((i: { purpose?: string }) => i.purpose === "maskable")).toBe(true);
  });

  it("o service worker tem manipulador de fetch e nao usa cache", async () => {
    const { readFileSync } = await import("node:fs");
    const sw = readFileSync(new URL("../../public/sw.js", import.meta.url), "utf-8");

    // Sem `fetch`, o Chrome nao oferece a instalacao.
    expect(sw).toContain('addEventListener("fetch"');
    // Cache aqui serviria codigo velho para sempre. Se alguem adicionar, que
    // seja uma decisao consciente e nao um acidente.
    expect(sw).not.toContain("caches.open");
    expect(sw).not.toContain("cache.put");
  });

  it("o index.html liga o manifest e o icone do iOS", async () => {
    const { readFileSync } = await import("node:fs");
    const html = readFileSync(new URL("../../index.html", import.meta.url), "utf-8");

    expect(html).toContain('rel="manifest"');
    // O iOS ignora o manifest para instalacao; sem esta meta, o icone vira
    // uma captura da tela.
    expect(html).toContain("apple-touch-icon");
    expect(html).toContain("apple-mobile-web-app-capable");
  });
});
