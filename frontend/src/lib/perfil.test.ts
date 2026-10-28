import type { User } from "@supabase/supabase-js";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  IDADE_MAXIMA_DO_PERFIL,
  NOME_MAXIMO_DO_PERFIL,
  atualizarPerfil,
  buscarPerfil,
  calcularAlteracao,
  descreverResultado,
  emailDaSessao,
  emailJaVale,
  formularioDoPerfil,
  idadeDoPerfil,
  lerIdade,
  nadaAFazer,
  nomeDoPerfil,
  normalizarEmail,
  normalizarNome,
  validarEmail,
  validarNome,
} from "./perfil";

// ── O QUE ESTES DUBLES PROVAM, E O QUE NAO PROVAM ────────────────────────
//
// Sao dois: `requisitarJson` (a rota de perfil) e `updateUser` (o Auth). Eles
// exercitam a ORQUESTRACAO deste modulo — qual campo vai para qual destino, a
// ordem das chamadas, a propagacao de `perfilGravado` quando a segunda falha,
// e a leitura pessimista da resposta de e-mail.
//
// Nada aqui prova nada sobre o comportamento real do Supabase nem do backend.
// Em particular, **nao prova**:
//
//   * que uma troca de e-mail de verdade exige confirmacao, nem quantos
//     e-mails ela dispara (ponto cego herdado do `UI-11`);
//   * que `data: { nome: null }` apaga de fato a chave do metadado;
//   * que o RLS impede a Ana de escrever no perfil do Bruno — isso esta em
//     `web-app/tests/rls/`, contra Postgres real, e mock nenhum provaria.
//
// Isso e ponto cego DECLARADO, no espirito do §4 de
// `docs/LICOES-APRENDIDAS.md`. A diferenca em relacao ao caso da suite de RLS
// mockada e o que esta sendo afirmado: ali o trabalho afirmava isolamento e a
// prova era um mock; aqui o que esta sob teste e a decisao deste arquivo sobre
// o que fazer com cada forma de resposta, que e codigo proprio.
//
// O que fecharia: um projeto Supabase de teste e uma troca ponta a ponta.
// Registrado no `UI-11` do backlog.

const updateUser = vi.fn();
const requisitar = vi.fn();

vi.mock("./supabase", () => ({
  obterSupabase: () => ({ auth: { updateUser } }),
  problemaDeConfiguracao: () => null,
}));

vi.mock("./api", () => ({
  requisitarJson: (...argumentos: unknown[]) => requisitar(...argumentos),
}));

function usuario(parcial: Partial<User> = {}): User {
  return {
    id: "u1",
    email: "ana@exemplo.com",
    app_metadata: {},
    aud: "authenticated",
    created_at: "2026-08-01T00:00:00Z",
    ...parcial,
  } as User;
}

const PERFIL = { nome: "Ana Maria", idade: 22, updated_at: "2026-10-17T12:00:00Z" };

/** O estado atual do formulario: perfil pela rota, e-mail pela sessao. */
const ATUAL = { nome: "Ana Maria", idade: "22", email: "ana@exemplo.com" };

beforeEach(() => {
  updateUser.mockReset();
  requisitar.mockReset();
  requisitar.mockResolvedValue(PERFIL);
  updateUser.mockResolvedValue({ data: { user: usuario() }, error: null });
});

// =====================================================================
// leitura — a fonte de verdade, e so ela
// =====================================================================

describe("buscarPerfil", () => {
  it("le da rota de perfil", async () => {
    await buscarPerfil();
    expect(requisitar).toHaveBeenCalledWith("/api/me/perfil");
  });

  it("deixa o erro subir, em vez de devolver perfil vazio", async () => {
    // Um `catch` aqui faria "nao deu para ler" parecer "nao ha nome", e a tela
    // mostraria em branco o nome de quem tem nome — degradacao silenciosa
    // (§7 das licoes). Quem decide o que mostrar e o `PerfilContext`.
    requisitar.mockRejectedValue(new Error("Sessao expirada. Entre novamente."));
    await expect(buscarPerfil()).rejects.toThrow("Sessao expirada");
  });
});

describe("leitura do que a rota devolveu", () => {
  it("nome e idade saem do perfil; e-mail sai da sessao", () => {
    expect(nomeDoPerfil(PERFIL)).toBe("Ana Maria");
    expect(idadeDoPerfil(PERFIL)).toBe(22);
    expect(emailDaSessao(usuario())).toBe("ana@exemplo.com");
  });

  it("nao quebra com perfil ausente nem com campo de outro tipo", () => {
    expect(nomeDoPerfil(null)).toBe("");
    expect(nomeDoPerfil({ nome: null, idade: null })).toBe("");
    expect(idadeDoPerfil(null)).toBeNull();
    expect(emailDaSessao(null)).toBe("");
  });

  it("idade que nao e inteiro conta como ausente, e nao como zero", () => {
    expect(idadeDoPerfil({ nome: "x", idade: 22.5 as number })).toBeNull();
    expect(idadeDoPerfil({ nome: "x", idade: "22" as unknown as number })).toBeNull();
  });

  it("formularioDoPerfil mostra idade ausente como campo vazio", () => {
    // E nao como "0" nem "null": campo de formulario e texto, e vazio e o
    // jeito de a pessoa dizer "nao informo".
    expect(formularioDoPerfil({ nome: "Ana", idade: null }, usuario())).toEqual({
      nome: "Ana",
      idade: "",
      email: "ana@exemplo.com",
    });
  });
});

// =====================================================================
// normalizacao e validacao
// =====================================================================

describe("normalizacao", () => {
  it("colapsa espaco interno do nome", () => {
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
    expect(validarNome(` ${"a".repeat(NOME_MAXIMO_DO_PERFIL)} `).ok).toBe(true);
  });
});

describe("lerIdade", () => {
  it("vazio e VALIDO e significa apagar a idade", () => {
    // Art. 18, IV ao alcance de um clique. Vazio nao e erro: e instrucao.
    expect(lerIdade("")).toEqual({ ok: true, valor: null });
    expect(lerIdade("   ")).toEqual({ ok: true, valor: null });
  });

  it("aceita inteiro escrito como inteiro", () => {
    expect(lerIdade("0")).toEqual({ ok: true, valor: 0 });
    expect(lerIdade(" 22 ")).toEqual({ ok: true, valor: 22 });
    expect(lerIdade(String(IDADE_MAXIMA_DO_PERFIL))).toEqual({
      ok: true,
      valor: IDADE_MAXIMA_DO_PERFIL,
    });
  });

  it("recusa o que o Number() aceitaria e ninguem digitou", () => {
    // "1e2" viraria 100, "0x1f" viraria 31. Gravar isso seria o §7: dado
    // plausivel e errado, sem ninguem ter pedido.
    for (const ruim of ["1e2", "0x1f", "22.5", "-3", "abc", "22 anos", "+22", "٢٢"]) {
      expect(lerIdade(ruim).ok, ruim).toBe(false);
    }
  });

  it("recusa fora da faixa, que e a da constraint do banco", () => {
    expect(lerIdade("150").ok).toBe(false);
    expect(lerIdade("999").ok).toBe(false);
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

  it("recusa espaco no meio, dois arrobas e ponto nas bordas do dominio", () => {
    expect(validarEmail("ana @exemplo.com").ok).toBe(false);
    expect(validarEmail("ana@b@exemplo.com").ok).toBe(false);
    expect(validarEmail("ana@.exemplo.com").ok).toBe(false);
    expect(validarEmail("ana@exemplo.com.").ok).toBe(false);
  });
});

// =====================================================================
// calcularAlteracao
// =====================================================================

describe("calcularAlteracao", () => {
  it("formulario igual ao atual nao altera nada", () => {
    expect(nadaAFazer(calcularAlteracao(ATUAL, { ...ATUAL }))).toBe(true);
  });

  it("diferenca so de espaco ou de caixa nao e alteracao", () => {
    const r = calcularAlteracao(ATUAL, {
      nome: " Ana   Maria ",
      idade: " 22 ",
      email: "ANA@exemplo.com",
    });
    expect(nadaAFazer(r)).toBe(true);
  });

  it("separa o que mudou do que nao mudou", () => {
    expect(calcularAlteracao(ATUAL, { ...ATUAL, nome: "Ana M. Silva" })).toEqual({
      nome: "Ana M. Silva",
    });
    expect(calcularAlteracao(ATUAL, { ...ATUAL, idade: "30" })).toEqual({ idade: 30 });
    expect(calcularAlteracao(ATUAL, { ...ATUAL, email: "nova@exemplo.com" })).toEqual({
      email: "nova@exemplo.com",
    });
  });

  it("apagar a idade E uma alteracao, com valor nulo", () => {
    // Campo AUSENTE e campo nulo sao coisas diferentes no `PATCH`: ausente e
    // "nao mexa", nulo e "apague". Sem isto nao haveria como retirar a idade.
    expect(calcularAlteracao(ATUAL, { ...ATUAL, idade: "" })).toEqual({ idade: null });
  });

  it("idade invalida conta como mexida, para a mensagem poder aparecer", () => {
    // Senao a pessoa digita "abc", o botao fica inerte e nada explica por que.
    expect(nadaAFazer(calcularAlteracao(ATUAL, { ...ATUAL, idade: "abc" }))).toBe(false);
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

// =====================================================================
// atualizarPerfil — o destino de cada campo
// =====================================================================

describe("atualizarPerfil — cada campo no seu destino", () => {
  it("sem alteracao nenhuma nao vai a rede", async () => {
    const r = await atualizarPerfil(ATUAL, { ...ATUAL });
    expect(r).toEqual({ tipo: "nada-a-fazer" });
    expect(requisitar).not.toHaveBeenCalled();
    expect(updateUser).not.toHaveBeenCalled();
  });

  it("nome e idade vao pela ROTA, e nao pelo Auth", async () => {
    // O item inteiro em um teste: antes do PERFIL-01 isto ia para
    // `updateUser({ data: { nome } })` e `profiles` ficava intocada.
    const r = await atualizarPerfil(ATUAL, { ...ATUAL, nome: "Ana M.", idade: "30" });

    expect(r).toMatchObject({ tipo: "salvo", perfilGravado: true });
    expect(requisitar).toHaveBeenCalledWith("/api/me/perfil", {
      method: "PATCH",
      body: JSON.stringify({ nome: "Ana M.", idade: 30 }),
    });
  });

  it("o PATCH manda SO o que mudou", async () => {
    await atualizarPerfil(ATUAL, { ...ATUAL, idade: "30" });
    expect(requisitar.mock.calls[0][1]).toMatchObject({ body: JSON.stringify({ idade: 30 }) });
  });

  it("apagar a idade manda idade nula, e nao omite o campo", async () => {
    await atualizarPerfil(ATUAL, { ...ATUAL, idade: "" });
    expect(requisitar.mock.calls[0][1]).toMatchObject({ body: JSON.stringify({ idade: null }) });
  });

  it("o e-mail NAO vai pela rota: continua no Auth, que e onde a credencial mora", async () => {
    await atualizarPerfil(ATUAL, { ...ATUAL, email: "nova@exemplo.com" });
    expect(requisitar).not.toHaveBeenCalled();
    expect(updateUser).toHaveBeenCalledWith({ email: "nova@exemplo.com" });
  });

  it("nenhum campo tem dois destinos — o nome nao e gravado tambem no Auth", async () => {
    // A propriedade que elimina a divergencia por desenho (PERFIL-01, Regra
    // 2). Se alguem "sincronizar de passagem" um dia, este teste cai.
    await atualizarPerfil(ATUAL, { ...ATUAL, nome: "Ana M." });
    const escritasDeNome = updateUser.mock.calls.filter(
      ([argumento]) => (argumento as { data?: { nome?: unknown } })?.data?.nome,
    );
    expect(escritasDeNome).toEqual([]);
  });
});

describe("atualizarPerfil — validacao antes da rede", () => {
  it("nome invalido nao vai a rede", async () => {
    const r = await atualizarPerfil(ATUAL, { ...ATUAL, nome: "   " });
    expect(r.tipo).toBe("invalido");
    expect(requisitar).not.toHaveBeenCalled();
  });

  it("idade invalida nao vai a rede, nem a parte valida ao lado", async () => {
    // Metade de um formulario de perfil aplicada e pior que nenhuma: a pessoa
    // nao saberia o estado.
    const r = await atualizarPerfil(ATUAL, { ...ATUAL, nome: "Ana M.", idade: "abc" });
    expect(r.tipo).toBe("invalido");
    expect(requisitar).not.toHaveBeenCalled();
    expect(updateUser).not.toHaveBeenCalled();
  });

  it("e-mail invalido nao grava o perfil que seria gravavel", async () => {
    const r = await atualizarPerfil(ATUAL, { ...ATUAL, nome: "Ana M.", email: "ana@" });
    expect(r.tipo).toBe("invalido");
    expect(requisitar).not.toHaveBeenCalled();
  });
});

describe("atualizarPerfil — ordem e desfechos parciais", () => {
  it("perfil primeiro, e-mail depois", async () => {
    const ordem: string[] = [];
    requisitar.mockImplementation(() => {
      ordem.push("perfil");
      return Promise.resolve(PERFIL);
    });
    updateUser.mockImplementation((argumento: { email?: string }) => {
      ordem.push(argumento?.email ? "email" : "residuo");
      return Promise.resolve({ data: { user: usuario() }, error: null });
    });

    await atualizarPerfil(ATUAL, { nome: "Ana M.", idade: "30", email: "nova@exemplo.com" });
    expect(ordem).toEqual(["perfil", "residuo", "email"]);
  });

  it("falha no perfil NAO tenta o e-mail", async () => {
    // Disparar confirmacao de troca de credencial depois de falhar a correcao
    // simples deixaria a pessoa com um e-mail no caminho e nada corrigido.
    requisitar.mockRejectedValue(new Error("perfil nao atualizado (fonte indisponivel)"));
    const r = await atualizarPerfil(ATUAL, { nome: "Ana M.", idade: "30", email: "nova@x.com" });

    expect(r).toMatchObject({ tipo: "erro", perfilGravado: false, residuoLimpo: false });
    expect(updateUser).not.toHaveBeenCalled();
  });

  it("falha no e-mail nao apaga o perfil que ja foi gravado", async () => {
    updateUser.mockImplementation((argumento: { email?: string }) =>
      Promise.resolve(
        argumento?.email
          ? { data: { user: null }, error: { message: "rate limit", status: 429 } }
          : { data: { user: usuario() }, error: null },
      ),
    );
    const r = await atualizarPerfil(ATUAL, { ...ATUAL, nome: "Ana M.", email: "nova@x.com" });
    expect(r).toMatchObject({ tipo: "erro", perfilGravado: true });
  });

  it("e-mail novo sem prova de troca vira pendente, nao salvo", async () => {
    const r = await atualizarPerfil(ATUAL, { ...ATUAL, email: "nova@exemplo.com" });
    expect(r).toEqual({
      tipo: "email-pendente",
      emailPendente: "nova@exemplo.com",
      perfilGravado: false,
      residuoLimpo: false,
    });
  });

  it("e-mail que o servidor ja aplicou vira salvo", async () => {
    updateUser.mockResolvedValue({
      data: { user: usuario({ email: "nova@exemplo.com" }) },
      error: null,
    });
    const r = await atualizarPerfil(ATUAL, { ...ATUAL, email: "nova@exemplo.com" });
    expect(r).toMatchObject({ tipo: "salvo", perfilGravado: false });
  });

  it("erro do Supabase chega traduzido, nao em ingles", async () => {
    updateUser.mockResolvedValue({
      data: { user: null },
      error: {
        message: "Email rate limit exceeded",
        status: 429,
        code: "over_email_send_rate_limit",
      },
    });
    const r = await atualizarPerfil(ATUAL, { ...ATUAL, email: "nova@exemplo.com" });
    expect(r).toMatchObject({ tipo: "erro" });
    if (r.tipo === "erro") expect(r.mensagem).toContain("Muitas tentativas");
  });
});

describe("atualizarPerfil — a limpeza de residuo do metadado", () => {
  it("limpa o metadado DEPOIS de gravar o perfil", async () => {
    const r = await atualizarPerfil(ATUAL, { ...ATUAL, nome: "Ana M." });
    expect(updateUser).toHaveBeenCalledWith({ data: { nome: null } });
    expect(r).toMatchObject({ perfilGravado: true, residuoLimpo: true });
  });

  it("limpa tambem quando so a idade mudou", async () => {
    // Nao depende de o nome ter mudado: assim, depois da primeira edicao de
    // qualquer tipo existe UMA copia do nome, sem condicao a explicar.
    await atualizarPerfil(ATUAL, { ...ATUAL, idade: "30" });
    expect(updateUser).toHaveBeenCalledWith({ data: { nome: null } });
  });

  it("NAO limpa quando so o e-mail mudou — nao houve escrita autoritativa", async () => {
    await atualizarPerfil(ATUAL, { ...ATUAL, email: "nova@exemplo.com" });
    expect(updateUser).toHaveBeenCalledTimes(1);
    expect(updateUser).toHaveBeenCalledWith({ email: "nova@exemplo.com" });
  });

  it("falha na limpeza NAO transforma a correcao em erro", async () => {
    // A propriedade central: o resultado afirma o que foi verificado (o perfil
    // gravou) e nao afirma o que nao foi (o residuo saiu). Anunciar falha aqui
    // seria dizer a pessoa que a correcao nao aconteceu quando aconteceu.
    updateUser.mockResolvedValue({ data: { user: null }, error: { message: "boom" } });
    const r = await atualizarPerfil(ATUAL, { ...ATUAL, nome: "Ana M." });
    expect(r).toEqual({ tipo: "salvo", perfilGravado: true, residuoLimpo: false });
  });

  it("excecao na limpeza tambem nao derruba a correcao", async () => {
    updateUser.mockRejectedValue(new Error("rede caiu"));
    const r = await atualizarPerfil(ATUAL, { ...ATUAL, nome: "Ana M." });
    expect(r).toMatchObject({ tipo: "salvo", perfilGravado: true, residuoLimpo: false });
  });
});

// =====================================================================
// descreverResultado
// =====================================================================

describe("descreverResultado", () => {
  it("o pendente diz qual e-mail ainda vale, e nao anuncia troca", () => {
    const texto = descreverResultado(
      {
        tipo: "email-pendente",
        emailPendente: "nova@exemplo.com",
        perfilGravado: false,
        residuoLimpo: false,
      },
      "ana@exemplo.com",
    );
    expect(texto).toContain("nova@exemplo.com");
    expect(texto).toContain("continua sendo ana@exemplo.com");
  });

  it("o pendente com perfil gravado diz as duas coisas", () => {
    const texto = descreverResultado(
      {
        tipo: "email-pendente",
        emailPendente: "nova@exemplo.com",
        perfilGravado: true,
        residuoLimpo: true,
      },
      "ana@exemplo.com",
    );
    expect(texto.startsWith("Nome e idade atualizados.")).toBe(true);
  });

  it("o erro depois do perfil gravado nao diz que nada foi salvo", () => {
    const texto = descreverResultado(
      {
        tipo: "erro",
        mensagem: "Muitas tentativas em pouco tempo.",
        perfilGravado: true,
        residuoLimpo: true,
      },
      "ana@exemplo.com",
    );
    expect(texto).toContain("Nome e idade foram atualizados, mas o e-mail não");
  });

  it("residuo nao limpo NAO vira aviso na tela", () => {
    // Decisao, nao esquecimento: o titular pediu correcao, e a correcao
    // aconteceu. Anunciar a limpeza de uma copia interna que nenhuma tela le
    // faria uma operacao bem-sucedida parecer parcial. O campo existe no
    // resultado para quem depura, e para o codigo nao confundir as duas.
    const texto = descreverResultado(
      { tipo: "salvo", perfilGravado: true, residuoLimpo: false },
      "ana@exemplo.com",
    );
    expect(texto).toBe("Dados atualizados.");
  });

  it("nada-a-fazer nao se parece com sucesso", () => {
    expect(descreverResultado({ tipo: "nada-a-fazer" }, "ana@exemplo.com")).toContain(
      "Nada a salvar",
    );
  });
});
