import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  ErroApi,
  buscarHistorico,
  buscarHistoricoCompleto,
  definirCallbackDeSessaoExpirada,
  definirProvedorDeToken,
  urlDaApi,
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
  vi.unstubAllEnvs();
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

describe("urlDaApi (APP-02)", () => {
  it("no site fica relativo: sem VITE_API_BASE o caminho passa intacto", () => {
    expect(urlDaApi("/api/devices", "")).toBe("/api/devices");
  });

  it("no app prefixa o backend, sem barra dobrada", () => {
    expect(urlDaApi("/api/data", "https://exemplo.test/")).toBe("https://exemplo.test/api/data");
    expect(urlDaApi("/api/data", "https://exemplo.test")).toBe("https://exemplo.test/api/data");
  });

  it("a requisicao autenticada usa o endereco do build", async () => {
    vi.stubEnv("VITE_API_BASE", "https://exemplo.test");
    const espiao = espiaoDeFetch();
    vi.stubGlobal("fetch", espiao);
    await buscarHistorico();
    expect(espiao.mock.calls[0][0]).toBe("https://exemplo.test/api/sleep-history");
  });

  it("sem a variavel, a requisicao continua relativa", async () => {
    vi.stubEnv("VITE_API_BASE", "");
    const espiao = espiaoDeFetch();
    vi.stubGlobal("fetch", espiao);
    await buscarHistorico();
    expect(espiao.mock.calls[0][0]).toBe("/api/sleep-history");
  });
});

describe("exportação paginada", () => {
  it("envia o cursor da última leitura ao pedir a segunda página", async () => {
    const ultima = { id: "ultima", created_at: "2026-11-01T00:00:00+00:00" };
    const pagina = Array.from({ length: 1999 }, () => ({ id: "anterior", created_at: "2026-11-02T00:00:00Z" }));
    const fetchSimulado = vi.fn()
      .mockResolvedValueOnce(resposta(200, [...pagina, ultima]))
      .mockResolvedValueOnce(resposta(200, []));
    vi.stubGlobal("fetch", fetchSimulado);

    expect(await buscarHistoricoCompleto()).toHaveLength(2000);
    expect(fetchSimulado).toHaveBeenCalledTimes(2);
    const url = new URL(fetchSimulado.mock.calls[1][0], "https://exemplo.test");
    expect(url.searchParams.get("cursor_tempo")).toBe(ultima.created_at);
    expect(url.searchParams.get("cursor_id")).toBe(ultima.id);
  });

  it("não retorna dados parciais se a segunda página falha", async () => {
    const linha = { id: "00000000-0000-0000-0000-000000000001", created_at: "2026-11-01T00:00:00Z" };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(resposta(200, Array(2000).fill(linha)))
      .mockResolvedValueOnce(resposta(503, { error: "indisponível" })));
    await expect(buscarHistoricoCompleto()).rejects.toThrow("indisponível");
  });
});
