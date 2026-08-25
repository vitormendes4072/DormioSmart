import { afterEach, describe, expect, it, vi } from "vitest";

import { ErroDeIngestao, enviarLeitura, mensagemDeFalha } from "./coleta";
import { agregar, montarPayload } from "./acelerometro";
import { GRAVIDADE } from "../types/sleep";

const PAYLOAD = montarPayload(agregar([{ ax: 0, ay: 0, az: GRAVIDADE }], 30, Date.now())!);
const DISPOSITIVO = "aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa";
const JWT = "jwt-de-teste";

afterEach(() => vi.unstubAllGlobals());

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
