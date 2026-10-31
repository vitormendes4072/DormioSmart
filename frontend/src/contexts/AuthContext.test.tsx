// @vitest-environment jsdom
/**
 * AUTH-07: a primeira chamada à API depois do login leva o token.
 *
 * O defeito que estes testes travam: o `AuthProvider` registrava o provedor de
 * token num `useEffect`, e no React os efeitos dos filhos rodam antes dos do
 * pai. O `PerfilProvider` -- filho, que busca o perfil no instante em que a
 * sessão aparece -- mandava `GET /api/me/perfil` sem `Authorization`, recebia
 * 401, e o callback de sessão expirada derrubava a sessão recém-criada. Na
 * produção (31/10) era o login que voltava para /login.
 *
 * Os provedores são os REAIS; só o cliente do Supabase e o `fetch` são falsos.
 * Um teste com um componente de mentira no lugar do `PerfilProvider` não
 * pegaria a regressão se alguém mudasse quando o perfil é buscado.
 */
import { act, render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

type AoMudar = (evento: string, sessao: unknown) => void;
let aoMudar: AoMudar | null = null;

vi.mock("../lib/supabase", () => ({
  problemaDeConfiguracao: () => null,
  obterSupabase: () => ({
    auth: {
      getSession: () => Promise.resolve({ data: { session: null } }),
      onAuthStateChange: (callback: AoMudar) => {
        aoMudar = callback;
        return { data: { subscription: { unsubscribe() {} } } };
      },
      signOut: () => Promise.resolve({}),
    },
  }),
}));

import { requisitarJson } from "../lib/api";
import { AuthProvider } from "./AuthContext";
import { PerfilProvider } from "./PerfilContext";

type Chamada = { url: string; authorization: string | null };
let chamadas: Chamada[] = [];
let statusDaResposta = 200;

function perfil() {
  return { nome: "Ana", idade: null, updated_at: null, perfil_criado_agora: false };
}

beforeEach(() => {
  chamadas = [];
  statusDaResposta = 200;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: RequestInfo | URL, opcoes?: RequestInit) => {
      chamadas.push({
        url: String(url),
        authorization: new Headers(opcoes?.headers).get("Authorization"),
      });
      return new Response(JSON.stringify(perfil()), {
        status: statusDaResposta,
        headers: { "Content-Type": "application/json" },
      });
    }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
  aoMudar = null;
});

function sessao(token: string) {
  return { access_token: token, user: { id: "usuario-1" } };
}

async function montar() {
  render(
    <AuthProvider>
      <PerfilProvider>
        <span />
      </PerfilProvider>
    </AuthProvider>,
  );
  await act(async () => {}); // getSession: ninguem logado
}

async function evento(nome: string, s: unknown) {
  await act(async () => {
    aoMudar?.(nome, s);
  });
  await act(async () => {});
}

describe("AuthProvider liga o token antes dos efeitos dos filhos (AUTH-07)", () => {
  it("a busca do perfil logo depois do login leva o JWT", async () => {
    await montar();
    await evento("SIGNED_IN", sessao("jwt-do-login"));

    const perfilBuscado = chamadas.find((c) => c.url === "/api/me/perfil");
    expect(perfilBuscado, "o PerfilProvider busca o perfil quando a sessao aparece").toBeDefined();
    expect(perfilBuscado?.authorization).toBe("Bearer jwt-do-login");
  });

  it("nenhuma chamada sai sem token enquanto ha sessao", async () => {
    await montar();
    await evento("SIGNED_IN", sessao("jwt-do-login"));
    expect(chamadas.length).toBeGreaterThan(0);
    expect(chamadas.every((c) => c.authorization === "Bearer jwt-do-login")).toBe(true);
  });

  it("depois da renovacao, a chamada seguinte leva o token NOVO", async () => {
    await montar();
    await evento("SIGNED_IN", sessao("jwt-velho"));
    await evento("TOKEN_REFRESHED", sessao("jwt-novo"));
    chamadas = [];
    await act(async () => {
      await requisitarJson("/api/sleep-history");
    });
    expect(chamadas[0]?.authorization).toBe("Bearer jwt-novo");
  });

  it("401 de verdade ainda derruba a sessao (o AUTH-04 continua valendo)", async () => {
    await montar();
    await evento("SIGNED_IN", sessao("jwt-revogado"));
    statusDaResposta = 401;
    chamadas = [];
    await act(async () => {
      await requisitarJson("/api/sleep-history").catch(() => {});
    });
    await act(async () => {});
    // Sem sessao, o provedor devolve null: a proxima chamada sai sem token.
    statusDaResposta = 200;
    await act(async () => {
      await requisitarJson("/api/sleep-history");
    });
    expect(chamadas.at(-1)?.authorization).toBeNull();
  });
});
