import type { AuthError } from "@supabase/supabase-js";
import { describe, expect, it } from "vitest";

import { MINIMO_DA_SENHA, traduzirErroDeAuth } from "./autenticacao";

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

// ── SEC-08: a tela nao diz quem tem cadastro ─────────────────────────────
//
// Estes dois testes substituem dois que exigiam a frase
// "Já existe uma conta com este e-mail." — e afirmam o oposto dela. Havia
// dois porque ha dois caminhos de traducao, por `code` e por `message`, e
// fechar um deles so deixaria o outro vazando.
//
// O que eles cobrem e o que NAO cobrem: eles provam que a FRASE nao nomeia o
// fato. Nao provam ausencia de enumeracao — com confirmacao de e-mail
// desligada o desfecho dos dois cadastros difere (sessao, redirecionamento,
// estado da tela), e isso e invisivel a um teste de unidade de string. A
// decisao que fecharia o canal estrutural esta no `SEC-08` do backlog.
describe("conta existente — a mensagem nao nomeia o fato (SEC-08)", () => {
  /** Qualquer redacao que CONFIRME a existencia da conta ao visitante. */
  const NOMEIA_O_FATO = /já existe|existe uma conta|já está cadastrad|já registrad|em uso/i;

  it("pelo codigo: user_already_exists nao confirma que a conta existe", () => {
    const m = traduzirErroDeAuth(erro({ code: "user_already_exists" }));
    expect(m).not.toMatch(NOMEIA_O_FATO);
    // E condicional, no modelo do `recuperarSenha`: serve igual a quem ja tem
    // conta e a quem errou outra coisa, entao nao distingue os dois.
    expect(m).toMatch(/\bSe você já tem/);
  });

  it("pelo texto: 'User already registered' tambem nao confirma", () => {
    // O caminho por texto existe porque o `code` nem sempre vem. Ele vazava
    // pela mesma frase, e tinha de ser fechado junto.
    const m = traduzirErroDeAuth(erro({ message: "User already registered" }));
    expect(m).not.toMatch(NOMEIA_O_FATO);
    expect(m).toMatch(/\bSe você já tem/);
  });
});
