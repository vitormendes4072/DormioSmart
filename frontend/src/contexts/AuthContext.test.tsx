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
import { startTransition, Suspense } from "react";
import { act, cleanup, render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

type AoMudar = (evento: string, sessao: unknown) => void;
let aoMudar: AoMudar | null = null;
// `vi.mock` sobe para o topo do arquivo; o espião precisa subir junto.
const { signOut } = vi.hoisted(() => ({ signOut: vi.fn(() => Promise.resolve({})) }));

vi.mock("../lib/supabase", () => ({
  problemaDeConfiguracao: () => null,
  obterSupabase: () => ({
    auth: {
      getSession: () => Promise.resolve({ data: { session: null } }),
      onAuthStateChange: (callback: AoMudar) => {
        aoMudar = callback;
        return { data: { subscription: { unsubscribe() {} } } };
      },
      signOut,
    },
  }),
}));

import { requisitarJson } from "../lib/api";
import { AuthProvider, useAuth } from "./AuthContext";
import { PerfilProvider, usePerfil } from "./PerfilContext";

type Chamada = { url: string; authorization: string | null };
let chamadas: Chamada[] = [];
let statusDaResposta = 200;

function perfil() {
  return { nome: "Ana", idade: null, updated_at: null, perfil_criado_agora: false };
}

beforeEach(() => {
  signOut.mockClear();
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
  cleanup();
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

  it("401 limpa tambem a sessao guardada no navegador, sem chamar o servidor (AUTH-08)", async () => {
    await montar();
    await evento("SIGNED_IN", sessao("jwt-revogado"));
    statusDaResposta = 401;
    await act(async () => {
      await requisitarJson("/api/sleep-history").catch(() => {});
    });
    expect(signOut).toHaveBeenCalledWith({ scope: "local" });
  });

  it("503 (servico fora do ar) NAO desloga ninguem (AUTH-08)", async () => {
    await montar();
    await evento("SIGNED_IN", sessao("jwt-bom"));
    statusDaResposta = 503;
    await act(async () => {
      await requisitarJson("/api/sleep-history").catch(() => {});
    });
    expect(signOut).not.toHaveBeenCalled();
    statusDaResposta = 200;
    chamadas = [];
    await act(async () => {
      await requisitarJson("/api/sleep-history");
    });
    expect(chamadas[0]?.authorization).toBe("Bearer jwt-bom");
  });
});


it("envia o Bearer no primeiro pedido de perfil e preserva a sessão (AUTH-07)", async () => {
  vi.stubGlobal("fetch", vi.fn(async (url: string, opcoes?: RequestInit) => {
    const authorization = new Headers(opcoes?.headers).get("Authorization");
    chamadas.push({ url, authorization });
    return new Response(JSON.stringify(perfil()), { status: authorization ? 200 : 401 });
  }));
  await montar();
  await evento("SIGNED_IN", sessao("jwt-do-login"));
  expect({
    authorization: chamadas.find((c) => c.url === "/api/me/perfil")?.authorization,
    deslogou: signOut.mock.calls.length > 0,
  }).toEqual({ authorization: "Bearer jwt-do-login", deslogou: false });
});

it.each([200, 401])("ignora a resposta %s de perfil de uma conta anterior", async (status) => {
  let concluirA: ((r: Response) => void) | undefined;
  const resposta = (nome: string) => new Response(JSON.stringify({ ...perfil(), nome }));
  vi.stubGlobal("fetch", vi.fn(async (_url: string, opcoes?: RequestInit) => {
    const token = new Headers(opcoes?.headers).get("Authorization");
    return token === "Bearer jwt-a"
      ? new Promise<Response>((resolve) => { concluirA = resolve; })
      : resposta("Conta B");
  }));

  function Observador() {
    return <span>{useAuth().usuario?.id}|{usePerfil().perfil?.nome}</span>;
  }

  const tela = render(<AuthProvider><PerfilProvider><Observador /></PerfilProvider></AuthProvider>);
  await act(async () => {});
  await evento("SIGNED_IN", { access_token: "jwt-a", user: { id: "a" } });
  expect(concluirA).toBeTypeOf("function");
  await evento("SIGNED_IN", { access_token: "jwt-b", user: { id: "b" } });
  expect(tela.container.textContent).toBe("b|Conta B");

  await act(async () => concluirA?.(status === 200 ? resposta("Conta A") : new Response(null, { status })));
  expect({ texto: tela.container.textContent, deslogou: signOut.mock.calls.length > 0 })
    .toEqual({ texto: "b|Conta B", deslogou: false });
});

it("mantém o token confirmado quando outro render é descartado", async () => {
  const bloqueio = new Promise<never>(() => {});
  const renders: string[] = [];

  function Observador() {
    const id = useAuth().usuario?.id ?? "";
    renders.push(id);
    if (id === "b") throw bloqueio;
    return <span>{id}</span>;
  }

  const tela = render(
    <Suspense fallback={<span>aguarde</span>}>
      <AuthProvider><Observador /></AuthProvider>
    </Suspense>,
  );
  await act(async () => {});
  await evento("SIGNED_IN", { access_token: "jwt-a", user: { id: "a" } });
  await act(async () => startTransition(() => aoMudar?.("SIGNED_IN", { access_token: "jwt-b", user: { id: "b" } })));
  expect(renders).toContain("b");
  expect(tela.container.textContent).toBe("a");
  await requisitarJson("/api/sleep-history");
  await evento("SIGNED_IN", { access_token: "jwt-c", user: { id: "c" } });
  expect(tela.container.textContent).toBe("c");
  expect(chamadas[0]?.authorization).toBe("Bearer jwt-a");
});

it("desmontar AuthProvider encerra o provedor de credenciais", async () => {
  const tela = render(<AuthProvider><span /></AuthProvider>);
  await act(async () => {});
  await evento("SIGNED_IN", sessao("jwt-que-estava-montado"));
  tela.unmount();
  await requisitarJson("/api/sleep-history");
  expect(chamadas.at(-1)?.authorization).toBeNull();
});

function PerfilVisivel() {
  const { perfil, carregando } = usePerfil();
  return <span>{perfil?.nome ?? "-"}|{String(carregando)}</span>;
}

async function montarComPerfil() {
  const tela = render(<AuthProvider><PerfilProvider><PerfilVisivel /></PerfilProvider></AuthProvider>);
  await act(async () => {});
  await evento("SIGNED_IN", sessao("jwt-1"));
  expect(tela.container.textContent).toBe("Ana|false");
  return tela.container;
}

it.each(["TOKEN_REFRESHED", "SIGNED_IN"])("%s do mesmo usuário preserva o perfil sem consultar de novo", async (tipo) => {
  const tela = await montarComPerfil();
  const fetchMock = vi.mocked(fetch);
  fetchMock.mockImplementationOnce(() => new Promise<Response>(() => {}));

  await evento(tipo, sessao("jwt-2"));

  expect({ texto: tela.textContent, pedidos: fetchMock.mock.calls.length })
    .toEqual({ texto: "Ana|false", pedidos: 1 });
});

it("esconde o perfil de A enquanto a consulta de B está pendente", async () => {
  const tela = await montarComPerfil();
  const fetchMock = vi.mocked(fetch);
  fetchMock.mockImplementationOnce(() => new Promise<Response>(() => {}));

  await evento("SIGNED_IN", { access_token: "jwt-b", user: { id: "b" } });

  expect(fetchMock).toHaveBeenCalledTimes(2);
  expect(new Headers(fetchMock.mock.calls[1]?.[1]?.headers).get("Authorization")).toBe("Bearer jwt-b");
  expect(tela.textContent).toBe("-|true");
});

it("esconde o perfil guardado depois de sair da conta", async () => {
  const tela = await montarComPerfil();

  await evento("SIGNED_OUT", null);

  expect(tela.textContent).toBe("-|false");
  expect(fetch).toHaveBeenCalledTimes(1);
});
