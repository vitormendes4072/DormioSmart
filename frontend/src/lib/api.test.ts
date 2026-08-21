import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  ErroApi,
  buscarHistorico,
  definirCallbackDeSessaoExpirada,
  definirProvedorDeToken,
} from "./api";

function resposta(status: number, corpo: unknown, ok = status >= 200 && status < 300) {
  return {
    ok,
    status,
    json: async () => corpo,
  } as Response;
}

/** Captura as opcoes passadas ao fetch para inspecionar os cabecalhos. Ler de
 *  `mock.calls` exigiria tipar a assinatura inteira do fetch; capturar aqui e
 *  mais direto e sobrevive ao type-check. */
let opcoesCapturadas: RequestInit | undefined;

function espiaoDeFetch() {
  return vi.fn(async (_url: RequestInfo | URL, opcoes?: RequestInit) => {
    opcoesCapturadas = opcoes;
    return resposta(200, []);
  });
}

function cabecalhosCapturados(): Headers {
  return new Headers(opcoesCapturadas?.headers);
}

beforeEach(() => {
  opcoesCapturadas = undefined;
  definirProvedorDeToken(() => null);
  definirCallbackDeSessaoExpirada(() => {});
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("buscarHistorico", () => {
  it("devolve as leituras quando a API responde 200", async () => {
    const amostra = [{ created_at: "2026-08-19T03:00:00Z", movimento_total: 9.8, temp: 32, status: "Repouso" }];
    vi.stubGlobal("fetch", vi.fn(async () => resposta(200, amostra)));

    await expect(buscarHistorico()).resolves.toEqual(amostra);
  });

  it("degrada para lista vazia se o corpo nao for array", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => resposta(200, { inesperado: true })));

    await expect(buscarHistorico()).resolves.toEqual([]);
  });
});

describe("autenticacao", () => {
  it("nao envia Authorization enquanto nao ha sessao", async () => {
    vi.stubGlobal("fetch", espiaoDeFetch());

    await buscarHistorico();

    expect(cabecalhosCapturados().has("Authorization")).toBe(false);
  });

  it("injeta o Bearer quando o provedor devolve um token", async () => {
    vi.stubGlobal("fetch", espiaoDeFetch());
    definirProvedorDeToken(() => "jwt-de-teste");

    await buscarHistorico();

    expect(cabecalhosCapturados().get("Authorization")).toBe("Bearer jwt-de-teste");
  });
});

describe("tratamento de erro", () => {
  it("401 dispara o callback de sessao expirada e lanca ErroApi", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => resposta(401, { error: "nao autorizado" })));
    const aoExpirar = vi.fn();
    definirCallbackDeSessaoExpirada(aoExpirar);

    await expect(buscarHistorico()).rejects.toMatchObject({ status: 401 });
    expect(aoExpirar).toHaveBeenCalledOnce();
  });

  it("propaga a mensagem que o backend mandou em {error}", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => resposta(503, { error: "dados nao persistidos" })));

    await expect(buscarHistorico()).rejects.toThrow("dados nao persistidos");
  });

  it("cai para mensagem generica quando o corpo do erro nao e JSON", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({
      ok: false,
      status: 500,
      json: async () => {
        throw new SyntaxError("nao e JSON");
      },
    } as unknown as Response)));

    await expect(buscarHistorico()).rejects.toThrow("Erro 500");
  });

  it("falha de rede vira ErroApi com status 0, nao excecao crua", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    }));

    const erro = await buscarHistorico().catch((e: unknown) => e);
    expect(erro).toBeInstanceOf(ErroApi);
    expect((erro as ErroApi).status).toBe(0);
    expect((erro as ErroApi).naoAutorizado).toBe(false);
  });
});
