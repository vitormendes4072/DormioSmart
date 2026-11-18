/**
 * A biblioteca da lista de espera (UI-14): o formato do e-mail, a sugestão de
 * domínio e a tradução das respostas do servidor para o que a tela mostra.
 */
import { afterEach, describe, expect, it, vi } from "vitest";

import { VERSAO_DA_LISTA, emailValido, inscreverNaListaDeEspera, sugerirEmail } from "./listaDeEspera";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("emailValido", () => {
  it.each(["ana@exemplo.com", "  Ana@Exemplo.COM ", "a.b+c@sub.dominio.com.br"])("aceita %s", (email) => {
    expect(emailValido(email)).toBe(true);
  });
  it.each(["", "ana", "ana@", "ana@exemplo", "a@b.c", "com espaco@exemplo.com", "dois@@exemplo.com", `${"x".repeat(250)}@exemplo.com`])(
    "recusa %s",
    (email) => {
      expect(emailValido(email)).toBe(false);
    },
  );
});

describe("sugerirEmail", () => {
  it.each([
    ["ana@gmial.com", "ana@gmail.com"],
    ["ana@hotmal.com", "ana@hotmail.com"],
    ["Ana@Outlok.com", "ana@outlook.com"],
    ["ana@yaho.com.br", "ana@yahoo.com.br"],
  ])("sugere %s → %s", (digitado, sugerido) => {
    expect(sugerirEmail(digitado)).toBe(sugerido);
  });

  it.each(["ana@gmail.com", "ana@empresa.com.br", "ana@", "sem-arroba", "ana@exemplo.com"])("não sugere para %s", (email) => {
    expect(sugerirEmail(email)).toBeNull();
  });
});

function responder(status: number, corpo: unknown = {}) {
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(corpo), { status, headers: { "Content-Type": "application/json" } }));
  vi.stubGlobal("fetch", fetch);
  return fetch;
}

const INSCRICAO = { email: " ana@exemplo.com ", nome: "  ", consentimento: true, maioridade: true, site: "" };

describe("inscreverNaListaDeEspera", () => {
  it("manda o corpo com a versão vigente, e-mail aparado e nome vazio como nulo", async () => {
    const fetch = responder(200, { status: "inscrito" });
    expect(await inscreverNaListaDeEspera(INSCRICAO)).toEqual({ tipo: "inscrito" });
    const [url, opcoes] = fetch.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/lista-de-espera");
    expect(opcoes.method).toBe("POST");
    expect(JSON.parse(String(opcoes.body))).toEqual({
      email: "ana@exemplo.com", nome: null, consentimento: true, maioridade: true, versao: VERSAO_DA_LISTA, site: "",
    });
  });

  it.each([
    [429, "lista_cheia"],
    [409, "texto_mudou"],
    [400, "invalido"],
    [503, "indisponivel"],
    [500, "indisponivel"],
  ])("traduz %i para %s", async (status, tipo) => {
    responder(status, { error: "x" });
    expect((await inscreverNaListaDeEspera(INSCRICAO)).tipo).toBe(tipo);
  });

  it("sem rede é indisponível", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("rede")));
    expect(await inscreverNaListaDeEspera(INSCRICAO)).toEqual({ tipo: "indisponivel" });
  });
});
