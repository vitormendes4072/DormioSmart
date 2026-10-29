import { describe, expect, it } from "vitest";

import { ErroApi } from "./api";
import {
  FRASE_DE_CONFIRMACAO,
  type ReciboDeExclusao,
  confirmacaoValida,
  descreverRecibo,
  excluirMinhaConta,
  interpretarRecibo,
} from "./conta";

function recibo(parcial: Partial<ReciboDeExclusao> = {}): ReciboDeExclusao {
  return {
    leituras_apagadas: 812,
    dispositivos_apagados: 2,
    perfil_apagado: true,
    conta_de_acesso_removida: true,
    ...parcial,
  };
}

describe("confirmacaoValida", () => {
  it("aceita a frase exata", () => {
    expect(confirmacaoValida("APAGAR MINHA CONTA")).toBe(true);
  });

  // A tolerância é o inimigo aqui: cada variação aceita aproxima a barreira
  // de um clique, e a barreira é a única coisa entre um engano e a perda
  // definitiva do histórico.
  it.each([
    ["minúsculas", "apagar minha conta"],
    ["caixa mista", "Apagar Minha Conta"],
    ["espaço à direita", "APAGAR MINHA CONTA "],
    ["espaço à esquerda", " APAGAR MINHA CONTA"],
    ["sem acento no lugar certo", "APAGAR MINHA CONTA."],
    ["vazio", ""],
    ["parcial", "APAGAR"],
  ])("recusa %s", (_, texto) => {
    expect(confirmacaoValida(texto)).toBe(false);
  });
});

describe("interpretarRecibo", () => {
  it("chama de completa quando a conta de acesso saiu", () => {
    const r = interpretarRecibo(recibo({ conta_de_acesso_removida: true }));
    expect(r.tipo).toBe("completa");
  });

  it("chama de PARCIAL quando a conta de acesso permaneceu", () => {
    const r = interpretarRecibo(
      recibo({ conta_de_acesso_removida: false, aviso: "o e-mail continua lá" }),
    );
    expect(r.tipo).toBe("parcial");
    if (r.tipo === "parcial") expect(r.aviso).toBe("o e-mail continua lá");
  });

  it("usa um aviso próprio quando o backend não mandou um", () => {
    const r = interpretarRecibo(recibo({ conta_de_acesso_removida: false }));
    expect(r.tipo).toBe("parcial");
    if (r.tipo === "parcial") {
      expect(r.aviso).toMatch(/cadastro de acesso/i);
      expect(r.aviso).toMatch(/ainda existe/i);
    }
  });

  // O ponto do item: não inventar sucesso. Um campo ausente NÃO é um `true`
  // implícito — seria afirmar que um dado pessoal saiu sem nada confirmando.
  it.each([
    ["ausente", undefined],
    ["nulo", null],
    ["string 'true'", "true"],
    ["zero", 0],
  ])("trata conta_de_acesso_removida %s como PARCIAL, nunca completa", (_, valor) => {
    const r = interpretarRecibo(
      recibo({ conta_de_acesso_removida: valor as unknown as boolean }),
    );
    expect(r.tipo).toBe("parcial");
  });
});

describe("descreverRecibo", () => {
  it("descreve o que saiu, com números", () => {
    expect(descreverRecibo(recibo())).toBe("812 leituras, 2 dispositivos e o perfil");
  });

  it("concorda no singular", () => {
    expect(
      descreverRecibo(recibo({ leituras_apagadas: 1, dispositivos_apagados: 1 })),
    ).toBe("1 leitura, 1 dispositivo e o perfil");
  });

  it("omite o perfil quando ele não foi apagado", () => {
    const texto = descreverRecibo(recibo({ perfil_apagado: false }));
    expect(texto).toBe("812 leituras e 2 dispositivos");
  });

  it("não quebra com uma conta que nunca captou nada", () => {
    const texto = descreverRecibo(
      recibo({ leituras_apagadas: 0, dispositivos_apagados: 0, perfil_apagado: true }),
    );
    expect(texto).toBe("0 leituras, 0 dispositivos e o perfil");
  });
});

describe("excluirMinhaConta", () => {
  it("nem chega a chamar a rede se a frase estiver errada", async () => {
    let chamou = false;
    const originalFetch = globalThis.fetch;
    globalThis.fetch = (() => {
      chamou = true;
      return Promise.reject(new Error("não deveria ter sido chamado"));
    }) as typeof fetch;

    try {
      await expect(excluirMinhaConta("apagar minha conta")).rejects.toBeInstanceOf(ErroApi);
      expect(chamou).toBe(false);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("manda DELETE em /api/me com a frase no corpo", async () => {
    const originalFetch = globalThis.fetch;
    let caminho = "";
    let opcoes: RequestInit = {};

    globalThis.fetch = ((c: string, o: RequestInit) => {
      caminho = c;
      opcoes = o;
      return Promise.resolve(
        new Response(JSON.stringify(recibo()), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    }) as unknown as typeof fetch;

    try {
      const r = await excluirMinhaConta(FRASE_DE_CONFIRMACAO);
      expect(caminho).toBe("/api/me");
      expect(opcoes.method).toBe("DELETE");
      expect(JSON.parse(String(opcoes.body))).toEqual({ confirmacao: FRASE_DE_CONFIRMACAO });
      expect(r.tipo).toBe("completa");
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("devolve PARCIAL quando o backend reporta que o e-mail ficou", async () => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = (() =>
      Promise.resolve(
        new Response(
          JSON.stringify(recibo({ conta_de_acesso_removida: false, aviso: "ficou o e-mail" })),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )) as unknown as typeof fetch;

    try {
      const r = await excluirMinhaConta(FRASE_DE_CONFIRMACAO);
      expect(r.tipo).toBe("parcial");
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("propaga 503 como ErroApi, sem fingir que apagou", async () => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = (() =>
      Promise.resolve(
        new Response(JSON.stringify({ error: "fonte de dados indisponivel" }), {
          status: 503,
          headers: { "Content-Type": "application/json" },
        }),
      )) as unknown as typeof fetch;

    try {
      await expect(excluirMinhaConta(FRASE_DE_CONFIRMACAO)).rejects.toMatchObject({
        status: 503,
      });
    } finally {
      globalThis.fetch = originalFetch;
    }
  });
});
