import { afterEach, describe, expect, it, vi } from "vitest";

import {
  CHAVE_DO_TOKEN,
  ErroDeIngestao,
  enviarLeitura,
  esquecerToken,
  guardarToken,
  lerTokenGuardado,
  mensagemDeFalha,
} from "./coleta";
import { agregar, montarPayload } from "./acelerometro";
import { GRAVIDADE } from "../types/sleep";

const PAYLOAD = montarPayload(agregar([{ ax: 0, ay: 0, az: GRAVIDADE }], 30, Date.now())!);

/** sessionStorage falso: o ambiente de teste e Node, sem DOM. */
function comArmazenamento(): Record<string, string> {
  const dados: Record<string, string> = {};
  vi.stubGlobal("sessionStorage", {
    getItem: (k: string) => dados[k] ?? null,
    setItem: (k: string, v: string) => {
      dados[k] = v;
    },
    removeItem: (k: string) => {
      delete dados[k];
    },
  });
  return dados;
}

afterEach(() => vi.unstubAllGlobals());

describe("guarda do token", () => {
  it("grava, le e esquece", () => {
    comArmazenamento();
    expect(lerTokenGuardado()).toBeNull();
    guardarToken("abc123");
    expect(lerTokenGuardado()).toBe("abc123");
    esquecerToken();
    expect(lerTokenGuardado()).toBeNull();
  });

  it("usa sessionStorage, e nao localStorage", () => {
    // O token da direito de ESCRITA na conta. Em navegador nao ha equivalente
    // ao Keystore; o que da para fazer e encurtar a janela de exposicao.
    const dados = comArmazenamento();
    guardarToken("abc123");
    expect(dados[CHAVE_DO_TOKEN]).toBe("abc123");
  });

  it("nao quebra quando o armazenamento esta bloqueado", () => {
    // Navegacao privada, cookies bloqueados. A coleta ainda funciona: o
    // usuario cola o token de novo a cada sessao.
    vi.stubGlobal("sessionStorage", {
      getItem: () => {
        throw new Error("bloqueado");
      },
      setItem: () => {
        throw new Error("bloqueado");
      },
      removeItem: () => {
        throw new Error("bloqueado");
      },
    });
    expect(lerTokenGuardado()).toBeNull();
    expect(() => guardarToken("x")).not.toThrow();
    expect(() => esquecerToken()).not.toThrow();
  });
});

describe("mensagemDeFalha", () => {
  it("401 fala de token, e nao de sessao", () => {
    // A ingestao e o outro caminho de autenticacao. Dizer "sessao expirada"
    // mandaria o usuario para o lugar errado.
    expect(mensagemDeFalha(401)).toContain("Token");
    expect(mensagemDeFalha(401).toLowerCase()).not.toContain("sess");
  });

  it("distingue recusa do servidor de indisponibilidade e de rede", () => {
    expect(mensagemDeFalha(400)).not.toBe(mensagemDeFalha(503));
    expect(mensagemDeFalha(0)).toContain("conexao");
  });
});

describe("enviarLeitura", () => {
  it("manda o token no header proprio, nao como Bearer", () => {
    let visto: RequestInit | undefined;
    vi.stubGlobal("fetch", (_u: string, init: RequestInit) => {
      visto = init;
      return Promise.resolve({ status: 201 } as Response);
    });

    return enviarLeitura(PAYLOAD, "tok").then(() => {
      const headers = visto?.headers as Record<string, string>;
      expect(headers["X-Device-Token"]).toBe("tok");
      expect(headers).not.toHaveProperty("Authorization");
    });
  });

  it("aceita apenas 201 — 200 nao e gravacao confirmada", async () => {
    vi.stubGlobal("fetch", () => Promise.resolve({ status: 200 } as Response));
    await expect(enviarLeitura(PAYLOAD, "tok")).rejects.toBeInstanceOf(ErroDeIngestao);
  });

  it("carrega o status na excecao", async () => {
    vi.stubGlobal("fetch", () => Promise.resolve({ status: 401 } as Response));
    await expect(enviarLeitura(PAYLOAD, "tok")).rejects.toMatchObject({ status: 401 });
  });

  it("falha de rede vira status 0, e nao excecao crua", async () => {
    vi.stubGlobal("fetch", () => Promise.reject(new TypeError("offline")));
    await expect(enviarLeitura(PAYLOAD, "tok")).rejects.toMatchObject({ status: 0 });
  });
});
