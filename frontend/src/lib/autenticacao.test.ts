import type { AuthError } from "@supabase/supabase-js";
import { describe, expect, it } from "vitest";

import { MINIMO_DA_SENHA, pareceContaExistente, traduzirErroDeAuth } from "./autenticacao";

/** Erro no formato do supabase-js. `code` e o campo estavel; `message` muda. */
function erro(opcoes: { code?: string; message?: string; status?: number }): AuthError {
  return {
    name: "AuthApiError",
    message: opcoes.message ?? "",
    status: opcoes.status ?? 400,
    code: opcoes.code,
  } as unknown as AuthError;
}

describe("traduzirErroDeAuth — pelo codigo", () => {
  it.each([
    ["invalid_credentials", "E-mail ou senha incorretos."],
    ["email_not_confirmed", "Confirme seu e-mail"],
    ["user_already_exists", "Já existe uma conta"],
    ["validation_failed", "E-mail inválido."],
    ["over_email_send_rate_limit", "Muitas tentativas"],
  ])("%s vira mensagem util", (codigo, trecho) => {
    expect(traduzirErroDeAuth(erro({ code: codigo }))).toContain(trecho);
  });

  it("cita o minimo real do app na senha fraca", () => {
    expect(traduzirErroDeAuth(erro({ code: "weak_password" }))).toContain(
      String(MINIMO_DA_SENHA),
    );
  });
});

describe("traduzirErroDeAuth — pelo texto, quando nao vem codigo", () => {
  it.each([
    ["Invalid login credentials", "E-mail ou senha incorretos."],
    ["Email not confirmed", "Confirme seu e-mail"],
    ["User already registered", "Já existe uma conta"],
    ["Password should be at least 6 characters", "pelo menos"],
    ["Unable to validate email address: invalid format", "E-mail inválido."],
  ])("%s", (mensagem, trecho) => {
    expect(traduzirErroDeAuth(erro({ message: mensagem }))).toContain(trecho);
  });
});

describe("nada em ingles chega ao usuario", () => {
  it("erro desconhecido vira mensagem generica, sem repassar o texto cru", () => {
    const original = "PostgrestException: relation does not exist";
    const traduzido = traduzirErroDeAuth(erro({ message: original }));
    expect(traduzido).not.toContain("PostgrestException");
    expect(traduzido).not.toContain("relation");
    expect(traduzido).toContain("Não foi possível");
  });

  it("erro nulo ainda produz uma frase, nao 'undefined'", () => {
    expect(traduzirErroDeAuth(null)).toMatch(/\S/);
    expect(traduzirErroDeAuth(undefined)).not.toContain("undefined");
  });

  it("falha de rede e distinguida de credencial errada", () => {
    const rede = traduzirErroDeAuth(erro({ status: 0, message: "Failed to fetch" }));
    expect(rede).toMatch(/servidor|serviço/);
    expect(rede).not.toContain("senha");
  });

  it("falha de rede nao culpa a conexao do usuario", () => {
    // `Failed to fetch` cobre tanto a rede do usuario quanto o servico fora do
    // ar, e o navegador nao diz qual dos dois foi. Afirmar "verifique sua
    // internet" acerta so metade das vezes — e a metade errada manda a pessoa
    // depurar algo que esta funcionando.
    const rede = traduzirErroDeAuth(erro({ status: 0, message: "Failed to fetch" }));
    expect(rede).not.toMatch(/sua internet|sua conexão|sua rede/i);
  });
});

describe("as mensagens dizem o que fazer", () => {
  it("e-mail nao confirmado manda olhar o spam", () => {
    // O e-mail de confirmacao caindo em spam e o motivo mais comum de
    // "criei a conta e nao consigo entrar".
    expect(traduzirErroDeAuth(erro({ code: "email_not_confirmed" }))).toContain("spam");
  });

  it("limite de tentativas pede espera, sem sugerir que a senha esta errada", () => {
    const m = traduzirErroDeAuth(erro({ code: "over_email_send_rate_limit" }));
    expect(m).toContain("Aguarde");
    expect(m).not.toContain("incorret");
  });
});

describe("pareceContaExistente — protecao contra enumeracao", () => {
  it("identities vazio indica e-mail ja cadastrado", () => {
    // Com protecao contra enumeracao, o Supabase responde SUCESSO para
    // e-mail existente, mas sem identidades. A UI usa isto apenas para
    // registro interno — a tela mostra a mesma mensagem nos dois casos.
    expect(pareceContaExistente({ user: { identities: [] } })).toBe(true);
  });

  it("identities preenchido indica conta nova", () => {
    expect(pareceContaExistente({ user: { identities: [{ id: "x" }] } })).toBe(false);
  });

  it("nao quebra quando o campo nao vem", () => {
    expect(pareceContaExistente({ user: null })).toBe(false);
    expect(pareceContaExistente({ user: {} })).toBe(false);
    expect(pareceContaExistente({ user: { identities: null } })).toBe(false);
  });
});
