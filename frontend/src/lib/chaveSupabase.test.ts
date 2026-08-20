import { describe, expect, it } from "vitest";

import { verificarChaveAnon } from "./chaveSupabase";

/** Monta um JWT de mentira com o papel pedido — so o payload importa aqui. */
function jwtComPapel(papel: string): string {
  const base64url = (o: unknown) =>
    btoa(JSON.stringify(o)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  return [
    base64url({ alg: "HS256", typ: "JWT" }),
    base64url({ iss: "supabase", role: papel, exp: 2000000000 }),
    "assinatura-irrelevante",
  ].join(".");
}

describe("a service_role NUNCA pode passar", () => {
  it("recusa a service_role no formato JWT e marca como perigosa", () => {
    const r = verificarChaveAnon(jwtComPapel("service_role"));
    expect(r.valida).toBe(false);
    expect(r).toMatchObject({ perigosa: true });
  });

  it("manda rotacionar a chave, nao apenas trocar", () => {
    // Se a service_role chegou a ir para um bundle, ela esta comprometida —
    // trocar pela anon sem rotacionar deixa a antiga valendo.
    const r = verificarChaveAnon(jwtComPapel("service_role"));
    expect(r.valida).toBe(false);
    if (!r.valida) expect(r.motivo.toUpperCase()).toContain("ROTACIONE");
  });

  it("recusa a chave secreta no formato novo (sb_secret_)", () => {
    const r = verificarChaveAnon("sb_secret_abc123");
    expect(r).toMatchObject({ valida: false, perigosa: true });
  });

  it("recusa qualquer papel que nao seja anon", () => {
    for (const papel of ["authenticated", "supabase_admin", "postgres"]) {
      expect(verificarChaveAnon(jwtComPapel(papel))).toMatchObject({
        valida: false,
        perigosa: true,
      });
    }
  });
});

describe("chaves legitimas passam", () => {
  it("aceita a anon no formato JWT", () => {
    expect(verificarChaveAnon(jwtComPapel("anon"))).toEqual({ valida: true });
  });

  it("aceita a publicavel no formato novo", () => {
    expect(verificarChaveAnon("sb_publishable_abc123")).toEqual({ valida: true });
  });
});

describe("ausencia e valor invalido", () => {
  it.each([undefined, "", "   "])("orienta a preencher o .env quando vazio (%s)", (v) => {
    const r = verificarChaveAnon(v);
    expect(r.valida).toBe(false);
    if (!r.valida) {
      expect(r.perigosa).toBe(false);
      expect(r.motivo).toContain(".env");
    }
  });

  it("nao trata valor irreconhecivel como perigoso", () => {
    // Perigoso e reservado para "isto vaza o banco". Um valor sem sentido e
    // erro de configuracao, e a distincao muda o tom do aviso ao usuario.
    const r = verificarChaveAnon("isto-nao-e-uma-chave");
    expect(r).toMatchObject({ valida: false, perigosa: false });
  });

  it("nao quebra com JWT de payload corrompido", () => {
    const r = verificarChaveAnon("cabecalho.@@@nao-e-base64@@@.assinatura");
    expect(r.valida).toBe(false);
  });
});

describe("a mensagem ajuda a corrigir", () => {
  it("diz qual variavel esta errada", () => {
    const r = verificarChaveAnon(jwtComPapel("service_role"));
    if (!r.valida) expect(r.motivo).toContain("VITE_SUPABASE_ANON_KEY");
  });

  it("nao ecoa a chave recebida na mensagem", () => {
    // A mensagem vai para o console do navegador; repetir o segredo nela so
    // ampliaria o vazamento que estamos tentando evitar.
    const chave = jwtComPapel("service_role");
    const r = verificarChaveAnon(chave);
    if (!r.valida) expect(r.motivo).not.toContain(chave);
  });
});
