import type { User } from "@supabase/supabase-js";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  NOME_MAXIMO_DO_PERFIL,
  atualizarPerfil,
  calcularAlteracao,
  descreverResultado,
  emailDaSessao,
  emailJaVale,
  nadaAFazer,
  nomeDaSessao,
  normalizarEmail,
  normalizarNome,
  validarEmail,
  validarNome,
} from "./perfil";

// ── O QUE ESTE DUBLE PROVA, E O QUE NAO PROVA ────────────────────────────
//
// `updateUser` e substituido para exercitar a ORQUESTRACAO deste modulo: a
// ordem das duas chamadas, a propagacao de `nomeAlterado` quando a segunda
// falha, e a leitura pessimista da resposta. Nada aqui prova nada sobre o
// comportamento real do Supabase — em particular, **nao prova** que uma troca
// de e-mail de verdade exige confirmacao, nem quantos e-mails ela dispara.
//
// Isso e ponto cego declarado, no espirito do §4 de `docs/LICOES-APRENDIDAS.md`
// (a suite de RLS contra Supabase mockado nao exercitava policy nenhuma). A
// diferenca e o que esta sendo afirmado: ali o trabalho afirmava isolamento e
// a prova era um mock; aqui o que esta sob teste e a decisao deste arquivo
// sobre o que fazer com cada forma de resposta, que e codigo proprio.
//
// O que fecharia o cego: um projeto Supabase de teste e uma troca de e-mail
// ponta a ponta. Registrado no `UI-11` do backlog como verificacao pendente.

const updateUser = vi.fn();

vi.mock("./supabase", () => ({
  obterSupabase: () => ({ auth: { updateUser } }),
  problemaDeConfiguracao: () => null,
}));

function usuario(parcial: Partial<User> = {}): User {
  return {
    id: "u1",
    email: "ana@exemplo.com",
    user_metadata: { nome: "Ana Maria" },
    app_metadata: {},
    aud: "authenticated",
    created_at: "2026-08-01T00:00:00Z",
    ...parcial,
  } as User;
}

const ATUAL = { nome: "Ana Maria", email: "ana@exemplo.com" };

beforeEach(() => {
  updateUser.mockReset();
});

describe("nomeDaSessao / emailDaSessao", () => {
  it("le o nome de onde o app de fato o le: o metadado do Auth", () => {
    // E nao de `profiles.nome`, que e copia de signup e ninguem le.
    expect(nomeDaSessao(usuario())).toBe("Ana Maria");
  });

  it("nao quebra com sessao ausente nem com metadado de outro tipo", () => {
    expect(nomeDaSessao(null)).toBe("");
    expect(nomeDaSessao(usuario({ user_metadata: {} }))).toBe("");
    expect(nomeDaSessao(usuario({ user_metadata: { nome: 42 } }))).toBe("");
    expect(emailDaSessao(null)).toBe("");
  });
});

describe("normalizacao", () => {
  it("colapsa espaco interno do nome", () => {
    // "Ana  Maria" e "Ana Maria" sao o mesmo nome para quem digitou; sem isto
    // o formulario detectaria mudanca onde nao houve.
    expect(normalizarNome("  Ana   Maria  ")).toBe("Ana Maria");
  });

  it("baixa a caixa do e-mail", () => {
    expect(normalizarEmail(" Ana@Exemplo.COM ")).toBe("ana@exemplo.com");
  });
});

describe("validarNome", () => {
  it("recusa vazio e so-espaco", () => {
    expect(validarNome("").ok).toBe(false);
    expect(validarNome("    ").ok).toBe(false);
  });

  it("aceita no teto e recusa um acima", () => {
    expect(validarNome("a".repeat(NOME_MAXIMO_DO_PERFIL)).ok).toBe(true);
    expect(validarNome("a".repeat(NOME_MAXIMO_DO_PERFIL + 1)).ok).toBe(false);
  });

  it("mede o nome DEPOIS de normalizar", () => {
    // Senao espaco nas pontas contaria para o teto.
    expect(validarNome(` ${"a".repeat(NOME_MAXIMO_DO_PERFIL)} `).ok).toBe(true);
  });
});

describe("validarEmail", () => {
  it("aceita endereco comum", () => {
    expect(validarEmail("ana.silva+tcc@exemplo.com.br").ok).toBe(true);
  });

  it("recusa os erros de digitacao obvios", () => {
    for (const ruim of ["", "ana", "ana@", "@exemplo.com", "ana.com", "ana@exemplo"]) {
      expect(validarEmail(ruim).ok, ruim).toBe(false);
    }
  });

  it("recusa espaco no meio", () => {
    expect(validarEmail("ana @exemplo.com").ok).toBe(false);
  });

  it("recusa ponto encostado nas bordas do dominio", () => {
    expect(validarEmail("ana@.exemplo.com").ok).toBe(false);
    expect(validarEmail("ana@exemplo.com.").ok).toBe(false);
  });

  it("recusa dois arrobas", () => {
    expect(validarEmail("ana@b@exemplo.com").ok).toBe(false);
  });
});

describe("calcularAlteracao", () => {
  it("formulario igual ao atual nao altera nada", () => {
    expect(nadaAFazer(calcularAlteracao(ATUAL, { ...ATUAL }))).toBe(true);
  });

  it("diferenca so de espaco ou de caixa nao e alteracao", () => {
    // Importa porque mandar o e-mail atual como novo dispararia um pedido de
    // confirmacao para trocar um endereco pelo mesmo endereco.
    const r = calcularAlteracao(ATUAL, { nome: " Ana   Maria ", email: "ANA@exemplo.com" });
    expect(nadaAFazer(r)).toBe(true);
  });

  it("separa o que mudou do que nao mudou", () => {
    expect(calcularAlteracao(ATUAL, { nome: "Ana M. Silva", email: ATUAL.email })).toEqual({
      nome: "Ana M. Silva",
    });
    expect(calcularAlteracao(ATUAL, { nome: ATUAL.nome, email: "nova@exemplo.com" })).toEqual({
      email: "nova@exemplo.com",
    });
  });

  it("devolve o valor normalizado, nao o digitado", () => {
    expect(calcularAlteracao(ATUAL, { nome: "  Ana  M.  ", email: " NOVA@Exemplo.com " })).toEqual({
      nome: "Ana M.",
      email: "nova@exemplo.com",
    });
  });
});

describe("emailJaVale — pessimista por omissao", () => {
  it("so aceita quando o usuario devolvido TRAZ o endereco novo", () => {
    expect(emailJaVale(usuario({ email: "nova@exemplo.com" }), "nova@exemplo.com")).toBe(true);
  });

  it("resposta sem usuario, sem email, ou com o antigo, conta como pendente", () => {
    expect(emailJaVale(null, "nova@exemplo.com")).toBe(false);
    expect(emailJaVale(undefined, "nova@exemplo.com")).toBe(false);
    expect(emailJaVale(usuario({ email: undefined }), "nova@exemplo.com")).toBe(false);
    expect(emailJaVale(usuario(), "nova@exemplo.com")).toBe(false);
  });

  it("compara normalizado, para nao dizer pendente por causa de caixa", () => {
    expect(emailJaVale(usuario({ email: "Nova@Exemplo.com" }), "nova@exemplo.com")).toBe(true);
  });
});

describe("atualizarPerfil", () => {
  it("sem alteracao nenhuma nao vai a rede", async () => {
    const r = await atualizarPerfil(ATUAL, { ...ATUAL });
    expect(r).toEqual({ tipo: "nada-a-fazer" });
    expect(updateUser).not.toHaveBeenCalled();
  });

  it("nome invalido nao vai a rede", async () => {
    const r = await atualizarPerfil(ATUAL, { nome: "   ", email: ATUAL.email });
    expect(r.tipo).toBe("invalido");
    expect(updateUser).not.toHaveBeenCalled();
  });

  it("e-mail invalido nao vai a rede, mesmo com o nome valido ao lado", async () => {
    // O nome seria gravavel; nao gravamos nada, porque metade de um formulario
    // de perfil aplicada e pior que nenhuma — a pessoa nao saberia o estado.
    const r = await atualizarPerfil(ATUAL, { nome: "Ana M.", email: "ana@" });
    expect(r.tipo).toBe("invalido");
    expect(updateUser).not.toHaveBeenCalled();
  });

  it("so o nome: uma chamada, com o metadado", async () => {
    updateUser.mockResolvedValue({ data: { user: usuario() }, error: null });
    const r = await atualizarPerfil(ATUAL, { nome: "Ana M. Silva", email: ATUAL.email });
    expect(r).toEqual({ tipo: "salvo", nomeAlterado: true });
    expect(updateUser).toHaveBeenCalledTimes(1);
    expect(updateUser).toHaveBeenCalledWith({ data: { nome: "Ana M. Silva" } });
  });

  it("e-mail novo sem prova de troca vira pendente, nao salvo", async () => {
    // O Supabase devolve o usuario com o e-mail ANTIGO e manda link. Dizer
    // "salvo" aqui seria o §6: confirmacao antes da verificacao.
    updateUser.mockResolvedValue({ data: { user: usuario() }, error: null });
    const r = await atualizarPerfil(ATUAL, { nome: ATUAL.nome, email: "nova@exemplo.com" });
    expect(r).toEqual({
      tipo: "email-pendente",
      emailPendente: "nova@exemplo.com",
      nomeAlterado: false,
    });
  });

  it("e-mail que o servidor ja aplicou vira salvo", async () => {
    updateUser.mockResolvedValue({
      data: { user: usuario({ email: "nova@exemplo.com" }) },
      error: null,
    });
    const r = await atualizarPerfil(ATUAL, { nome: ATUAL.nome, email: "nova@exemplo.com" });
    expect(r).toEqual({ tipo: "salvo", nomeAlterado: false });
  });

  it("nome vem antes do e-mail, e as duas chamadas sao separadas", async () => {
    const vistas: unknown[] = [];
    updateUser.mockImplementation((arg: unknown) => {
      vistas.push(arg);
      return Promise.resolve({ data: { user: usuario() }, error: null });
    });
    await atualizarPerfil(ATUAL, { nome: "Ana M.", email: "nova@exemplo.com" });
    expect(vistas).toEqual([{ data: { nome: "Ana M." } }, { email: "nova@exemplo.com" }]);
  });

  it("falha no e-mail nao apaga o nome que já foi gravado", async () => {
    // O desfecho que justifica as duas chamadas separadas: uma chamada unica
    // devolveria erro para a operacao inteira e a tela diria que nada foi
    // salvo, com o nome já alterado no servidor.
    updateUser
      .mockResolvedValueOnce({ data: { user: usuario() }, error: null })
      .mockResolvedValueOnce({
        data: { user: null },
        error: { message: "rate limit", status: 429, code: "over_email_send_rate_limit" },
      });
    const r = await atualizarPerfil(ATUAL, { nome: "Ana M.", email: "nova@exemplo.com" });
    expect(r.tipo).toBe("erro");
    expect(r).toMatchObject({ nomeAlterado: true });
  });

  it("falha no nome nao tenta o e-mail", async () => {
    updateUser.mockResolvedValue({
      data: { user: null },
      error: { message: "boom", status: 500 },
    });
    const r = await atualizarPerfil(ATUAL, { nome: "Ana M.", email: "nova@exemplo.com" });
    expect(r).toMatchObject({ tipo: "erro", nomeAlterado: false });
    expect(updateUser).toHaveBeenCalledTimes(1);
  });

  it("erro do Supabase chega traduzido, nao em ingles", async () => {
    updateUser.mockResolvedValue({
      data: { user: null },
      error: { message: "Email rate limit exceeded", status: 429, code: "over_email_send_rate_limit" },
    });
    const r = await atualizarPerfil(ATUAL, { nome: ATUAL.nome, email: "nova@exemplo.com" });
    expect(r).toMatchObject({ tipo: "erro" });
    if (r.tipo === "erro") expect(r.mensagem).toContain("Muitas tentativas");
  });
});

describe("descreverResultado", () => {
  it("o pendente diz qual e-mail ainda vale, e nao anuncia troca", () => {
    const texto = descreverResultado(
      { tipo: "email-pendente", emailPendente: "nova@exemplo.com", nomeAlterado: false },
      "ana@exemplo.com",
    );
    expect(texto).toContain("nova@exemplo.com");
    expect(texto).toContain("continua sendo ana@exemplo.com");
  });

  it("o pendente com nome alterado diz as duas coisas", () => {
    const texto = descreverResultado(
      { tipo: "email-pendente", emailPendente: "nova@exemplo.com", nomeAlterado: true },
      "ana@exemplo.com",
    );
    expect(texto.startsWith("Nome atualizado.")).toBe(true);
  });

  it("o erro depois do nome gravado nao diz que nada foi salvo", () => {
    const texto = descreverResultado(
      { tipo: "erro", mensagem: "Muitas tentativas em pouco tempo.", nomeAlterado: true },
      "ana@exemplo.com",
    );
    expect(texto).toContain("O nome foi atualizado, mas o e-mail não");
  });

  it("nada-a-fazer nao se parece com sucesso", () => {
    expect(descreverResultado({ tipo: "nada-a-fazer" }, "ana@exemplo.com")).toContain(
      "Nada a salvar",
    );
  });
});
