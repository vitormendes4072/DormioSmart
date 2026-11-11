import { afterEach, describe, expect, it, vi } from "vitest";

import { ErroDeIngestao, enviarLeitura, enviarLote, mensagemDeFalha } from "./coleta";
import { agregar, montarPayload } from "./acelerometro";
import { GRAVIDADE } from "../types/sleep";

const PAYLOAD = montarPayload(agregar([{ ax: 0, ay: 0, az: GRAVIDADE }], 30, Date.now())!);
const DISPOSITIVO = "aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa";
const JWT = "jwt-de-teste";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

/** Captura o `init` do fetch para inspecionar o que foi enviado. */
function capturando(status: number) {
  const visto: { init?: RequestInit } = {};
  vi.stubGlobal("fetch", (_u: string, init: RequestInit) => {
    visto.init = init;
    return Promise.resolve({ status } as Response);
  });
  return visto;
}

describe("autenticacao por sessao (APP-08)", () => {
  it("manda o JWT no Authorization, e NENHUM token de dispositivo", async () => {
    // A razao de o token ter sumido: ele dava direito de ESCRITA e vivia no
    // navegador, onde nao ha equivalente ao Keystore. Agora nao ha o que um
    // XSS exfiltrar.
    const visto = capturando(201);
    await enviarLeitura(PAYLOAD, DISPOSITIVO, JWT);

    const headers = visto.init?.headers as Record<string, string>;
    expect(headers["Authorization"]).toBe(`Bearer ${JWT}`);
    expect(headers).not.toHaveProperty("X-Device-Token");
  });

  it("informa qual dispositivo esta enviando", async () => {
    const visto = capturando(201);
    await enviarLeitura(PAYLOAD, DISPOSITIVO, JWT);
    expect(JSON.parse(visto.init?.body as string).device_id).toBe(DISPOSITIVO);
  });

  it("nao manda user_id — o dono sai do JWT, no servidor", async () => {
    // Se o cliente mandasse, seria um campo que alguem poderia forjar. O
    // backend ignora, mas nem enviar e mais claro.
    const visto = capturando(201);
    await enviarLeitura(PAYLOAD, DISPOSITIVO, JWT);
    expect(JSON.parse(visto.init?.body as string)).not.toHaveProperty("user_id");
  });

  it("preserva os campos da leitura", async () => {
    const visto = capturando(201);
    await enviarLeitura(PAYLOAD, DISPOSITIVO, JWT);
    const corpo = JSON.parse(visto.init?.body as string);
    for (const campo of ["ax", "ay", "az", "total", "status", "ts", "epoca_s", "metodo"]) {
      expect(corpo).toHaveProperty(campo);
    }
  });

  it("sem sessao, falha antes de tocar a rede", async () => {
    let chamou = false;
    vi.stubGlobal("fetch", () => {
      chamou = true;
      return Promise.resolve({ status: 201 } as Response);
    });
    await expect(enviarLeitura(PAYLOAD, DISPOSITIVO, null)).rejects.toMatchObject({
      status: 401,
    });
    expect(chamou).toBe(false);
  });
});

describe("enviarLeitura", () => {
  it("aceita apenas 201 — 200 nao e gravacao confirmada", async () => {
    capturando(200);
    await expect(enviarLeitura(PAYLOAD, DISPOSITIVO, JWT)).rejects.toBeInstanceOf(
      ErroDeIngestao,
    );
  });

  it("carrega o status na excecao", async () => {
    capturando(404);
    await expect(enviarLeitura(PAYLOAD, DISPOSITIVO, JWT)).rejects.toMatchObject({
      status: 404,
    });
  });

  it("falha de rede vira status 0, e nao excecao crua", async () => {
    vi.stubGlobal("fetch", () => Promise.reject(new TypeError("offline")));
    await expect(enviarLeitura(PAYLOAD, DISPOSITIVO, JWT)).rejects.toMatchObject({
      status: 0,
    });
  });
});

describe("mensagemDeFalha", () => {
  it("401 fala de sessao, que e o que de fato expirou agora", () => {
    // Antes falava de token; com autenticacao por sessao, 401 significa
    // outra coisa e mandaria o usuario para o lugar errado.
    expect(mensagemDeFalha(401).toLowerCase()).toContain("sess");
  });

  it("404 explica o caso real: o dispositivo sumiu do outro lado", () => {
    expect(mensagemDeFalha(404).toLowerCase()).toContain("dispositivo");
  });

  it("distingue recusa, indisponibilidade e rede", () => {
    expect(mensagemDeFalha(400)).not.toBe(mensagemDeFalha(503));
    expect(mensagemDeFalha(0).toLowerCase()).toContain("conexao");
  });
});

describe("endereco do backend no app (APP-02)", () => {
  it("a leitura vai ao VITE_API_BASE quando o build o define", async () => {
    vi.stubEnv("VITE_API_BASE", "https://exemplo.test");
    let url = "";
    vi.stubGlobal("fetch", (u: string) => {
      url = u;
      return Promise.resolve({ status: 201 } as Response);
    });
    await enviarLeitura(PAYLOAD, DISPOSITIVO, JWT);
    expect(url).toBe("https://exemplo.test/api/data");
  });
});

describe("enviarLote (APP-02, etapa 3)", () => {
  function respondendo(status: number, corpo: unknown) {
    const visto: { url?: string; init?: RequestInit } = {};
    vi.stubGlobal("fetch", (u: string, init: RequestInit) => {
      visto.url = u;
      visto.init = init;
      return Promise.resolve({ status, json: async () => corpo } as Response);
    });
    return visto;
  }

  it("manda o device_id no envelope, as leituras como vieram e o JWT", async () => {
    const visto = respondendo(200, { aceitas: [0, 1], rejeitadas: [], pendentes: [] });
    const r = await enviarLote([{ a: 1 }, { a: 2 }], DISPOSITIVO, JWT);
    expect(visto.url).toBe("/api/data/lote");
    const corpo = JSON.parse(visto.init?.body as string);
    expect(corpo).toEqual({ device_id: DISPOSITIVO, leituras: [{ a: 1 }, { a: 2 }] });
    expect((visto.init?.headers as Record<string, string>).Authorization).toBe(`Bearer ${JWT}`);
    expect(r.aceitas).toEqual([0, 1]);
  });

  it("503 traz as listas: nada gravado, tudo pendente", async () => {
    respondendo(503, { aceitas: [], rejeitadas: [], pendentes: [0, 1] });
    expect((await enviarLote([{}, {}], DISPOSITIVO, JWT)).pendentes).toEqual([0, 1]);
  });

  it("503 sem corpo legivel vira tudo pendente, e nao erro", async () => {
    respondendo(503, null);
    expect((await enviarLote([{}, {}, {}], DISPOSITIVO, JWT)).pendentes).toEqual([0, 1, 2]);
  });

  it("401, 404 e 413 viram erro com o status, sem marcar nada", async () => {
    for (const status of [401, 404, 413]) {
      respondendo(status, { error: "x" });
      await expect(enviarLote([{}], DISPOSITIVO, JWT)).rejects.toMatchObject({ status });
    }
  });

  it("sem sessao, falha antes de tocar a rede", async () => {
    vi.stubGlobal("fetch", () => {
      throw new Error("nao devia chamar");
    });
    await expect(enviarLote([{}], DISPOSITIVO, null)).rejects.toMatchObject({ status: 401 });
  });
});
