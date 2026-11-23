// APP-19: a versão publicada, a comparação e o que o app manda ao servidor.
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";

import { VERSAO_DO_APP_ANDROID } from "./appAndroid";
import {
  CAMINHO_DA_VERSAO_PUBLICADA,
  buscarVersaoPublicada,
  compararVersoes,
  versaoParaAtualizar,
  versaoValida,
} from "./atualizacaoDoApp";
import { prepararDispositivoDoCelular } from "./coleta";

afterEach(() => {
  vi.unstubAllGlobals();
});

const resposta = (corpo: unknown, ok = true) =>
  Promise.resolve({ ok, json: () => Promise.resolve(corpo) } as Response);

describe("o arquivo da versão publicada", () => {
  it("anuncia a mesma versão do APK que a landing e o build.gradle", () => {
    const publicado = JSON.parse(readFileSync(resolve("public", CAMINHO_DA_VERSAO_PUBLICADA.slice(1)), "utf8"));
    expect(publicado).toEqual({ versao: VERSAO_DO_APP_ANDROID });
  });
});

describe("a comparação", () => {
  it("compara número a número, e não como texto", () => {
    expect(compararVersoes("1.1.10", "1.1.9")).toBeGreaterThan(0);
    expect(compararVersoes("1.2.0", "1.10.0")).toBeLessThan(0);
    expect(compararVersoes("2.0.0", "1.99.99")).toBeGreaterThan(0);
    expect(compararVersoes("1.1.4", "1.1.4")).toBe(0);
  });

  it("só anuncia versão MAIS NOVA que a instalada", () => {
    expect(versaoParaAtualizar("1.1.3", "1.1.4")).toBe("1.1.4");
    expect(versaoParaAtualizar("1.1.4", "1.1.4")).toBeNull();
    expect(versaoParaAtualizar("1.1.5", "1.1.4")).toBeNull();
    expect(versaoParaAtualizar("1.1.3", null)).toBeNull();
  });

  it("recusa o que não é MAJOR.MINOR.PATCH", () => {
    for (const v of ["1.1", "1.1.4-beta", "v1.1.4", "", 114, null]) expect(versaoValida(v)).toBe(false);
    expect(versaoValida("1.1.4")).toBe(true);
  });
});

describe("a busca da versão publicada", () => {
  it("lê o arquivo sem cache e devolve a versão", async () => {
    const buscar = vi.fn(() => resposta({ versao: "1.1.4" }));
    expect(await buscarVersaoPublicada(buscar as unknown as typeof fetch)).toBe("1.1.4");
    const [url, init] = buscar.mock.calls[0] as unknown as [string, RequestInit];
    expect(url.endsWith(CAMINHO_DA_VERSAO_PUBLICADA)).toBe(true);
    expect(init.cache).toBe("no-store");
  });

  it.each([
    ["sem internet", () => Promise.reject(new TypeError("offline"))],
    ["404", () => resposta({}, false)],
    ["versão estranha", () => resposta({ versao: "1.1.4-beta" })],
    ["corpo vazio", () => resposta(null)],
  ])("com %s, responde null e não lança", async (_nome, buscar) => {
    expect(await buscarVersaoPublicada(buscar as unknown as typeof fetch)).toBeNull();
  });
});

describe("o que o app manda ao servidor (APP-19)", () => {
  function capturando() {
    const visto: { init?: RequestInit } = {};
    vi.stubGlobal("fetch", (_u: string, init: RequestInit) => {
      visto.init = init;
      return Promise.resolve(
        new Response(JSON.stringify({ id: "d", nome: "Celular", tipo: "celular" }), { status: 200 }),
      );
    });
    return visto;
  }

  it("com a versão, manda versao_app no corpo", async () => {
    const visto = capturando();
    await prepararDispositivoDoCelular("1.1.4");
    expect(JSON.parse(String(visto.init?.body))).toEqual({ versao_app: "1.1.4" });
  });

  it("sem a versão (o site), não manda corpo", async () => {
    const visto = capturando();
    await prepararDispositivoDoCelular();
    expect(visto.init?.body).toBeUndefined();
  });
});
