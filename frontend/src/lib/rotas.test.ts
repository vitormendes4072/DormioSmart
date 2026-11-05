import { describe, expect, it } from "vitest";

import {
  DESTINO_PADRAO_APOS_LOGIN,
  decidirDestino,
  destinoSeguro,
  ehRetornoDeRecuperacao,
} from "./rotas";

describe("enquanto a sessao carrega, ninguem e redirecionado", () => {
  it("espera mesmo sem sessao — este e o bug do 'recarreguei e fui deslogado'", () => {
    // Ao recarregar, o Supabase leva alguns ms para restaurar a sessao. Um
    // guarda que lesse "sem sessao" nesse instante chutaria o usuario logado
    // para o login.
    expect(
      decidirDestino({ carregando: true, temSessao: false, ehRotaDeVisitante: false }),
    ).toBe("aguardar");
  });

  it("espera tambem em rota de visitante", () => {
    expect(
      decidirDestino({ carregando: true, temSessao: false, ehRotaDeVisitante: true }),
    ).toBe("aguardar");
  });

  it("carregando vence a informacao de sessao, qualquer que seja", () => {
    for (const temSessao of [true, false]) {
      for (const ehRotaDeVisitante of [true, false]) {
        expect(decidirDestino({ carregando: true, temSessao, ehRotaDeVisitante })).toBe(
          "aguardar",
        );
      }
    }
  });
});

describe("rota protegida", () => {
  it("libera quem tem sessao", () => {
    expect(
      decidirDestino({ carregando: false, temSessao: true, ehRotaDeVisitante: false }),
    ).toBe("liberar");
  });

  it("manda para o login quem nao tem", () => {
    expect(
      decidirDestino({ carregando: false, temSessao: false, ehRotaDeVisitante: false }),
    ).toBe("ir-para-login");
  });
});

describe("rota de visitante", () => {
  it("libera quem nao tem sessao", () => {
    expect(
      decidirDestino({ carregando: false, temSessao: false, ehRotaDeVisitante: true }),
    ).toBe("liberar");
  });

  it("tira do login quem ja entrou", () => {
    expect(
      decidirDestino({ carregando: false, temSessao: true, ehRotaDeVisitante: true }),
    ).toBe("ir-para-dashboard");
  });
});

describe("nunca ha decisao ambigua", () => {
  it("toda combinacao produz exatamente um destino conhecido", () => {
    const destinos = new Set<string>();
    for (const carregando of [true, false]) {
      for (const temSessao of [true, false]) {
        for (const ehRotaDeVisitante of [true, false]) {
          destinos.add(decidirDestino({ carregando, temSessao, ehRotaDeVisitante }));
        }
      }
    }
    expect([...destinos].sort()).toEqual([
      "aguardar",
      "ir-para-dashboard",
      "ir-para-login",
      "liberar",
    ]);
  });
});

describe("ehRetornoDeRecuperacao", () => {
  it("reconhece o formato antigo, no fragmento da URL", () => {
    expect(
      ehRetornoDeRecuperacao({ hash: "#access_token=abc&type=recovery", search: "" }),
    ).toBe(true);
  });

  it("reconhece o formato em query string", () => {
    expect(ehRetornoDeRecuperacao({ hash: "", search: "?type=recovery" })).toBe(true);
  });

  it("reconhece o fluxo PKCE, que so traz o code", () => {
    expect(ehRetornoDeRecuperacao({ hash: "", search: "?code=abc123" })).toBe(true);
  });

  it("nao confunde outros tipos de link de e-mail", () => {
    expect(ehRetornoDeRecuperacao({ hash: "#type=signup", search: "" })).toBe(false);
  });

  it("URL limpa nao e retorno de e-mail", () => {
    expect(ehRetornoDeRecuperacao({ hash: "", search: "" })).toBe(false);
    expect(ehRetornoDeRecuperacao({})).toBe(false);
  });
});

describe("destinoSeguro — só caminho interno (SEC-16)", () => {
  it.each(["/dashboard", "/configuracoes?aba=conta", "/coletar#topo", "/"])("aceita %s", (c) => {
    expect(destinoSeguro(c)).toBe(c);
  });

  it.each([
    ["//evil.example", "protocolo implícito"],
    ["/\\evil.example", "barra invertida (GHSA-wrjc-x8rr-h8h6)"],
    ["https://evil.example", "URL absoluta"],
    ["javascript:alert(1)", "esquema javascript"],
    ["dashboard", "sem a barra inicial"],
    ["", "vazio"],
    ["/\t/evil.example", "tab que o navegador descartaria"],
    ["/\n/evil.example", "quebra de linha"],
  ])("recusa %s (%s)", (c) => {
    expect(destinoSeguro(c)).toBe(DESTINO_PADRAO_APOS_LOGIN);
  });

  it.each([undefined, null, 42, { de: "/x" }])("recusa o que não é texto: %s", (c) => {
    expect(destinoSeguro(c)).toBe(DESTINO_PADRAO_APOS_LOGIN);
  });
});

