// @vitest-environment jsdom
/**
 * As telas estão MONTADAS e RENDERIZADAS, não só importadas? (UI-17, 2ª metade)
 *
 * ── O QUE O `alcance.test.ts` NÃO PEGA, E FOI MEDIDO ────────────────────
 *
 * O `alcance.test.ts` (UI-17, 1ª metade) percorre os `import` relativos a
 * partir de `main.tsx` e reprova quando um módulo de `src/` fica fora do
 * grafo. Fecha o defeito do `UI-10` — arquivo que ninguém importa. **E para
 * aí.** Medido em 18/10 por controle positivo: **removido o
 * `<PerfilProvider>` do `main.tsx`, o `alcance.test.ts` passa** — o módulo
 * continua no grafo porque `main.tsx` continua importando o símbolo. O mesmo
 * vale para `<ExcluirConta />`: apagar a tag do `Settings.tsx` e deixar o
 * `import` em cima não move uma letra naquela suíte.
 *
 * Então a catraca de alcance pega metade do problema: *está no grafo*. Esta
 * aqui pega a outra metade: *chega à tela*.
 *
 * ── POR QUE MONTAR PELO `main.tsx`, E NÃO POR UMA ÁRVORE DESTE ARQUIVO ──
 *
 * É a decisão de desenho que faz esta verificação valer algo, e a armadilha
 * em que ela quase caiu. O caminho óbvio com `@testing-library/react` é
 * `render(<AuthProvider><PerfilProvider><App /></PerfilProvider></AuthProvider>)`.
 * Esse teste **reproduziria o defeito que existe para pegar**: a composição
 * sob teste seria a escrita aqui, e remover o `<PerfilProvider>` do
 * `main.tsx` — o defeito concreto, medido — deixaria a suíte verde. Seria o
 * §1 das lições em forma de teste de componente.
 *
 * Por isso a montagem é `await import("./main.tsx")`: o ponto de entrada de
 * produção, executando o `createRoot(...).render(...)` que ele de fato tem,
 * sobre a árvore que ele de fato compõe. Não há composição duplicada em lugar
 * nenhum, logo não há composição que possa divergir.
 *
 * ── O QUE ESTÁ DUBLADO, E O QUE ISSO CUSTA NA AFIRMAÇÃO ─────────────────
 *
 * Três dublês, todos na fronteira externa, nenhum em módulo nosso:
 *
 *   1. `createClient` de `@supabase/supabase-js` — devolve sessão. Mantém
 *      `lib/supabase.ts`, `lib/chaveSupabase.ts` e o `AuthContext` reais.
 *   2. `fetch` global — responde `/api/me/perfil` e `/api/devices`.
 *   3. `window.matchMedia`, que o jsdom não implementa (o `useTema` o usa).
 *
 * **Logo, o que esta suíte afirma é montagem e renderização — não integração
 * com o Supabase nem com o Flask.** Dito aqui porque afirmação de alcance
 * escrita longe da verificação é como o §1 acontece. O ponto cego de
 * integração continua sendo o declarado no `UI-11`/`PERFIL-01`, e não é
 * fechado nem agravado por este arquivo.
 *
 * ── CONTROLE POSITIVO (§1, regra 1) ─────────────────────────────────────
 *
 * Cada afirmação abaixo foi validada removendo de fato a coisa afirmada do
 * JSX de produção e confirindo que o teste nomeado reprova. As seis direções,
 * com o resultado medido, estão na entrada de 19/10 (ii) do
 * `docs/DIARIO-DE-ENGENHARIA.md` e no item `UI-17` do backlog.
 */
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { aplicabilidadeDaIdade } from "./lib/aplicabilidade";

// ---------------------------------------------------------------------
// Dublês de fronteira
// ---------------------------------------------------------------------

const SESSAO = {
  access_token: "jwt-de-teste",
  user: { id: "11111111-1111-1111-1111-111111111111", email: "titular@exemplo.com" },
};

let sessaoDoServidor: typeof SESSAO | null = SESSAO;

vi.mock("@supabase/supabase-js", () => ({
  createClient: () => ({
    auth: {
      getSession: async () => ({ data: { session: sessaoDoServidor }, error: null }),
      // O `AuthContext` chama o `unsubscribe` ao desmontar; sem ele o teste
      // quebraria na limpeza e não no que está sob teste.
      onAuthStateChange: () => ({ data: { subscription: { unsubscribe: () => {} } } }),
      signOut: async () => ({ error: null }),
      updateUser: async () => ({ data: { user: SESSAO.user }, error: null }),
    },
  }),
}));

/** Perfil que a rota devolve nesta execução. Trocado por teste. */
let perfilDoServidor: { nome: string | null; idade: number | null } = {
  nome: "Titular de Teste",
  idade: null,
};

function respostaJson(corpo: unknown): Response {
  return {
    ok: true,
    status: 200,
    json: async () => corpo,
  } as Response;
}

beforeEach(() => {
  sessaoDoServidor = SESSAO;
  // Lidos no topo de `lib/supabase.ts`, então têm de valer antes do import
  // dinâmico. Valores de teste: a suíte não depende do `.env` de ninguém.
  vi.stubEnv("VITE_SUPABASE_URL", "https://projeto-de-teste.supabase.co");
  vi.stubEnv("VITE_SUPABASE_ANON_KEY", "sb_publishable_chave_de_teste");

  vi.stubGlobal(
    "fetch",
    vi.fn(async (caminho: string) => {
      if (String(caminho).startsWith("/api/me/perfil")) return respostaJson(perfilDoServidor);
      if (String(caminho).startsWith("/api/devices")) return respostaJson([]);
      if (String(caminho).startsWith("/api/sleep-history")) return respostaJson([]);
      // Qualquer outra rota de API é um caminho que o teste não previu, e
      // devolver `[]` em silêncio faria uma tela quebrada parecer vazia.
      throw new Error(`caminho não previsto no dublê de fetch: ${caminho}`);
    }),
  );

  // O jsdom não implementa `matchMedia`, e o `useTema` (montado pelo
  // `SeletorDeTema`, nas Configurações) o usa.
  vi.stubGlobal(
    "matchMedia",
    (consulta: string) => ({
      matches: false,
      media: consulta,
      addEventListener: () => {},
      removeEventListener: () => {},
    }),
  );

  // Idem `ResizeObserver`, que o recharts usa no painel.
  vi.stubGlobal(
    "ResizeObserver",
    class {
      observe() {}
      unobserve() {}
      disconnect() {}
    },
  );
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
  vi.resetModules();
  document.body.innerHTML = "";
  perfilDoServidor = { nome: "Titular de Teste", idade: null };
});

// ---------------------------------------------------------------------
// Montagem pelo ponto de entrada de produção
// ---------------------------------------------------------------------

/**
 * Monta o aplicativo de verdade na rota pedida.
 *
 * `vi.resetModules()` no `afterEach` é o que permite montar mais de uma vez:
 * `main.tsx` tem efeito de módulo (o `createRoot(...).render(...)`), então sem
 * limpar o registro o segundo `import` devolveria o módulo em cache e não
 * renderizaria nada — e um teste que não renderiza nada passa por vazio, que é
 * o modo de falha do §1.
 */
async function montar(rota: string): Promise<void> {
  const raiz = document.createElement("div");
  raiz.id = "root";
  document.body.appendChild(raiz);
  window.history.pushState({}, "", rota);

  await act(async () => {
    await import("./main.tsx");
  });
}

/**
 * Prazo generoso, e o motivo: a primeira montagem paga a transformação de todo
 * o grafo de `src/` pelo Vite (~12 s nesta máquina); as seguintes levam
 * centenas de milissegundos. Com o prazo padrão de 5 s, o primeiro teste
 * estoura, o `import("./main.tsx")` em curso resolve **depois** do `afterEach`
 * e o `createRoot` da montagem abandonada cai no `#root` do teste seguinte —
 * que foi exatamente o que aconteceu na primeira execução deste arquivo, e
 * produziu oito falhas com `useAuth precisa estar dentro de <AuthProvider>`
 * numa árvore em que o provedor estava lá.
 */
const PRAZO = { timeout: 60_000 };

describe("montagem real das telas (UI-17)", PRAZO, () => {
  it("o ponto de entrada renderiza alguma coisa na raiz", async () => {
    // Guarda do próprio instrumento, pelo mesmo motivo das duas do
    // `alcance.test.ts`: se o `montar` parar de montar — `#root` com outro id,
    // `main.tsx` renomeado, dublê que faz o render abortar —, todas as
    // asserções seguintes passariam a procurar texto numa página vazia, e
    // `queryByText` devolvendo nulo é indistinguível de "a tela não tem isso".
    await montar("/configuracoes");
    expect(document.getElementById("root")?.childElementCount).toBeGreaterThan(0);
  });

  it("o <PerfilProvider> está montado na árvore de produção", async () => {
    await montar("/configuracoes");

    // Duas provas independentes, e são independentes de propósito.
    //
    // (a) O efeito do provedor correu: ele é o único lugar do aplicativo que
    //     pede `/api/me/perfil`. Sem o provedor no JSX, ninguém pede.
    const pedidos = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls.map(
      (c) => String(c[0]),
    );
    expect(pedidos.some((p) => p.startsWith("/api/me/perfil"))).toBe(true);

    // (b) O valor que ele carregou chegou à tela. A prova (a) sozinha
    //     aceitaria um provedor montado fora da árvore que as telas usam.
    expect(screen.getAllByText("Titular de Teste").length).toBeGreaterThan(0);
  });

  it("o EditarPerfil está renderizado na tela de Configurações", async () => {
    await montar("/configuracoes");

    expect(screen.getByRole("button", { name: /editar dados/i })).toBeTruthy();
    expect(screen.getByText("Idade")).toBeTruthy();
  });

  it("o campo de idade existe na tela, depois de abrir a edição", async () => {
    await montar("/configuracoes");

    // Antes de abrir, o campo não existe — e isto é asserção, não comentário:
    // sem ela, um `#perfil-idade` que aparecesse sempre passaria por correto.
    expect(document.getElementById("perfil-idade")).toBeNull();

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /editar dados/i }));
    });

    const campo = document.getElementById("perfil-idade") as HTMLInputElement | null;
    expect(campo).not.toBeNull();
    // `inputMode` numérico em vez de `type="number"` é decisão com motivo
    // escrito no componente; presa aqui para não se perder em refatoração.
    expect(campo?.inputMode).toBe("numeric");
    expect(screen.getByText(/Idade \(opcional\)/)).toBeTruthy();
  });

  it("o aviso de aplicabilidade da idade aparece na tela quando há idade", async () => {
    // 70 anos: faixa `pessoa-idosa`, cobertura `nao-coberta` — o aviso que
    // mais importa aparecer, porque é o que diz ao titular que os números do
    // trabalho não foram medidos para ele.
    perfilDoServidor = { nome: "Titular de Teste", idade: 70 };
    await montar("/configuracoes");

    const esperado = aplicabilidadeDaIdade(70);
    // O texto vem de `lib/aplicabilidade.ts`, não de uma cópia escrita aqui:
    // copiá-lo faria a asserção passar depois de alguém trocar a frase do
    // módulo, que é a forma mais barata de um teste de texto apodrecer.
    expect(esperado).not.toBeNull();
    expect(screen.getByText(esperado!.aviso)).toBeTruthy();
  });

  it("sem idade, o aviso não aparece — e é o caso normal", async () => {
    // O par negativo do teste acima. Sem ele, um `<p>` que mostrasse o aviso
    // sempre (ou texto fixo no lugar da função) passaria no positivo.
    perfilDoServidor = { nome: "Titular de Teste", idade: null };
    await montar("/configuracoes");

    expect(aplicabilidadeDaIdade(null)).toBeNull();
    expect(screen.queryByText(/coortes de validação/i)).toBeNull();
    expect(screen.getByText("não informada")).toBeTruthy();
  });

  it("o ExcluirConta está renderizado, e a barreira de duas etapas funciona na tela", async () => {
    await montar("/configuracoes");

    const botao = screen.getByRole("button", { name: /excluir minha conta/i });
    expect(botao).toBeTruthy();

    // Não basta o botão: o `UI-10` é a barreira, e ela tem de estar na tela.
    // Checar só o botão deixaria passar um componente cujo segundo passo
    // sumisse numa refatoração — exatamente o modo de falha que este arquivo
    // existe para pegar, um nível abaixo.
    expect(document.getElementById("confirmacao-exclusao")).toBeNull();

    await act(async () => {
      fireEvent.click(botao);
    });

    expect(document.getElementById("confirmacao-exclusao")).not.toBeNull();
    expect(screen.getByText(/Isto é irreversível/i)).toBeTruthy();
  });

  it("Configurações leva à Política de Privacidade (LGPD-01 (b))", async () => {
    await montar("/configuracoes");
    const links = screen.getAllByRole("link", { name: "Política de Privacidade" });
    expect(links.some((a) => a.getAttribute("href") === "/privacidade")).toBe(true);
  });

  it("abre Configurações pelo menu da demonstração sem montar ações da conta", async () => {
    await montar("/dashboard?demo=1");
    const links = await screen.findAllByRole("link", { name: "Configurações" });
    expect(links.map((link) => link.getAttribute("href"))).toEqual([
      "/configuracoes?demo=1", "/configuracoes?demo=1",
    ]);
    fireEvent.click(links[0]);
    expect(await screen.findByRole("heading", { name: "Aparência" })).toBeTruthy();
    expect(screen.getByText(/editar o perfil, gerenciar dispositivos/i)).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Exportar meus dados (CSV)" })).toBeNull();
    expect(vi.mocked(fetch).mock.calls.some(([url]) => String(url).startsWith("/api/devices"))).toBe(false);
  });

  it("mostra o status de envio de um dispositivo que ainda não tem leituras", async () => {
    const original = vi.mocked(fetch).getMockImplementation()!;
    vi.mocked(fetch).mockImplementation((entrada, opcoes) =>
      String(entrada).startsWith("/api/devices")
        ? Promise.resolve(respostaJson([{
            id: "dispositivo-teste", nome: "Sensor de teste", tipo: "travesseiro",
            last_seen_at: null, revoked_at: null,
          }]))
        : original(entrada, opcoes),
    );
    await montar("/dashboard");
    expect(await screen.findByText("Nunca enviou")).toBeTruthy();
  });

  it("a legenda das leituras recentes corresponde à ordem de medição", async () => {
    const original = vi.mocked(fetch).getMockImplementation()!;
    const agora = Date.now();
    const instante = (segundos: number) => new Date(agora - segundos * 1000).toISOString();
    const comum = { movimento_total: 9.81, epoca_segundos: 30 };
    vi.mocked(fetch).mockImplementation((entrada, opcoes) =>
      String(entrada).startsWith("/api/sleep-history")
        ? Promise.resolve(respostaJson([
          { ...comum, created_at: instante(1), captured_at: instante(60), temp: 31, status: "Repouso" },
          { ...comum, created_at: instante(2), captured_at: instante(30), temp: 32, status: "Movimento" },
        ]))
        : original(entrada, opcoes),
    );
    await montar("/dashboard");
    const recente = await screen.findByText("32.0°C", { selector: "td" });
    const anterior = screen.getByText("31.0°C", { selector: "td" });
    expect(recente.closest("tr")?.nextElementSibling).toBe(anterior.closest("tr"));
    expect(screen.getByText(/da medição mais recente à mais antiga/)).toBeTruthy();
  });

  function simularTemperaturas(leituras: Array<{ device_id: string; temp?: number }>) {
    const original = vi.mocked(fetch).getMockImplementation()!;
    vi.mocked(fetch).mockImplementation((entrada, opcoes) => {
      const caminho = String(entrada);
      if (caminho.startsWith("/api/devices")) return Promise.resolve(respostaJson([
        { id: "p", nome: "Travesseiro", tipo: "travesseiro" },
        { id: "c", nome: "Celular", tipo: "celular" },
      ]));
      if (caminho.startsWith("/api/sleep-history")) return Promise.resolve(respostaJson(
        leituras.map((leitura, i) => ({
          created_at: new Date(Date.now() - i * 30_000).toISOString(),
          movimento_total: 9.81, status: "Repouso", ...leitura,
        })),
      ));
      return original(entrada, opcoes);
    });
  }

  it("mostra a origem da temperatura na linha de cada tipo de aparelho", async () => {
    simularTemperaturas([{ device_id: "p", temp: 31 }, { device_id: "c", temp: 32 }]);
    await montar("/dashboard");
    const tabela = (await screen.findByRole("columnheader", { name: "Temperatura" })).closest("table")!;
    const chip = await within(tabela).findByText("Chip MPU6050");
    const bateria = await within(tabela).findByText("Bateria");
    expect(chip.closest("td")?.textContent).toContain("31.0°C");
    expect(bateria.closest("td")?.textContent).toContain("32.0°C");
  });

  it("mostra -- na coluna Temperatura quando a leitura não tem t", async () => {
    simularTemperaturas([{ device_id: "c" }]);
    await montar("/dashboard");
    const cabecalho = await screen.findByRole("columnheader", { name: "Temperatura" });
    const [, linha] = within(cabecalho.closest("table")!).getAllByRole("row");
    expect(within(linha).getAllByRole("cell")[(cabecalho as HTMLTableCellElement).cellIndex].textContent).toBe("--");
  });

  it("conta até o primeiro registro e avisa ao encerrar a coleta sem registros", async () => {
    const original = vi.mocked(fetch).getMockImplementation()!;
    vi.stubGlobal("DeviceMotionEvent", class {});
    vi.mocked(fetch).mockImplementation((entrada, opcoes) => {
      if (String(entrada) === "/api/me/perfil") {
        return Promise.resolve(respostaJson({ ...perfilDoServidor, consentimento_saude_versao: "2026-11-10" }));
      }
      if (String(entrada) === "/api/devices/celular") {
        return Promise.resolve(respostaJson({ id: "celular-teste", nome: "Celular de teste" }));
      }
      return original(entrada, opcoes);
    });

    await montar("/coletar");
    const iniciar = await screen.findByRole("button", { name: "Iniciar coleta" });
    vi.useFakeTimers();
    try {
      await act(async () => fireEvent.click(iniciar));
      expect(screen.getByText("Primeiro registro em 30 s.")).toBeTruthy();
      act(() => {
        window.dispatchEvent(Object.assign(new Event("devicemotion"), {
          accelerationIncludingGravity: { x: 0, y: 0, z: 9.81 },
        }));
        vi.advanceTimersByTime(5000);
      });
      expect(screen.getByText("Primeiro registro em 25 s.")).toBeTruthy();
      fireEvent.click(screen.getByRole("button", { name: "Encerrar sessão" }));
      expect(screen.getByText("Coleta encerrada sem registros.")).toBeTruthy();
      expect(screen.queryByText(/Primeiro registro em/)).toBeNull();
    } finally {
      vi.useRealTimers();
    }
  });

  it("exporta todas as páginas do histórico", async () => {
    const original = vi.mocked(fetch).getMockImplementation()!;
    const criarUrl = vi.fn(() => "blob:csv");
    const url = class extends URL {};
    Object.assign(url, { createObjectURL: criarUrl, revokeObjectURL: vi.fn() });
    vi.stubGlobal("URL", url);
    const clique = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    const leitura = { id: "00000000-0000-0000-0000-000000000001", created_at: "2026-11-01T00:00:00Z", movimento_total: 9.81, temp: null, status: "Repouso" };
    let pedidos = 0;
    vi.mocked(fetch).mockImplementation((entrada, opcoes) =>
      String(entrada).startsWith("/api/sleep-history")
        ? Promise.resolve(respostaJson(++pedidos === 1 ? Array.from({ length: 2000 }, () => leitura) : [leitura]))
        : original(entrada, opcoes),
    );
    try {
      await montar("/configuracoes");
      fireEvent.click(await screen.findByRole("button", { name: "Exportar meus dados (CSV)" }));
      await waitFor(() => expect(clique).toHaveBeenCalledTimes(1));
      expect(pedidos).toBe(2);
      expect(criarUrl).toHaveBeenCalledTimes(1);
    } finally { clique.mockRestore(); }
  });

  function simularSessoesNaBorda(quantidade = 2000) {
    const original = vi.mocked(fetch).getMockImplementation()!;
    const agora = Date.now();
    const leitura = (distancia: number) => ({
      created_at: new Date(agora - distancia).toISOString(),
      movimento_total: 9.81, temp: null, status: "Repouso", epoca_segundos: 30,
      device_id: "dispositivo",
    });
    const recentes = [leitura(30_000), leitura(60_000)];
    const antigas = Array.from({ length: 1998 }, (_, i) => leitura(86_400_000 + i * 30_000));
    let dados = [...recentes, ...antigas].slice(0, quantidade);
    vi.mocked(fetch).mockImplementation((entrada, opcoes) =>
      String(entrada).startsWith("/api/sleep-history")
        ? Promise.resolve(respostaJson(dados))
        : original(entrada, opcoes),
    );

    return () => { dados = [...recentes, ...antigas.slice(0, -1)]; };
  }

  it("mostra o progresso e inclui a sessão que chega na segunda página do Histórico", async () => {
    const original = vi.mocked(fetch).getMockImplementation()!;
    const agora = Date.now();
    const leitura = (id: number, distancia: number) => ({
      id: String(id), created_at: new Date(agora - distancia).toISOString(),
      movimento_total: 9.81, temp: null, status: "Repouso", epoca_segundos: 30,
    });
    const primeira = Array.from({ length: 2000 }, (_, i) => leitura(i, (i + 1) * 30_000));
    const segunda = [leitura(2000, 86_400_000), leitura(2001, 86_430_000)];
    let responder!: (r: Response) => void;
    vi.mocked(fetch).mockImplementation((entrada, opcoes) => {
      if (!String(entrada).startsWith("/api/sleep-history")) return original(entrada, opcoes);
      const url = new URL(String(entrada), "https://exemplo.test");
      if (!url.searchParams.has("cursor_id")) return Promise.resolve(respostaJson(primeira));
      return new Promise((resolve) => { responder = resolve; });
    });
    await montar("/historico");
    expect(await screen.findByText(/página 2 de até 16/)).toBeTruthy();
    expect(screen.queryByRole("table")).toBeNull();
    await act(async () => responder(respostaJson(segunda)));
    const tabela = await screen.findByRole("table");
    const [, recente, antiga] = within(tabela).getAllByRole("row");
    expect(within(recente).getByText("2000")).toBeTruthy();
    expect(within(antiga).getByText("2")).toBeTruthy();
    expect(within(tabela).getAllByText("Completa")).toHaveLength(2);
  });

  it.each([2000, 1999])("aviso de cobertura do painel com %i leituras", async (quantidade) => {
    simularSessoesNaBorda(quantidade);
    await montar("/dashboard");
    const aviso = "Cobertura parcial: a consulta atingiu o limite de leituras.";
    const verTodas = await screen.findByRole("button", { name: /ver todas/i });
    expect(screen.queryByText(aviso)).toBeNull();
    fireEvent.click(verTodas);
    expect(Boolean(screen.queryByText(aviso))).toBe(quantidade === 2000);
  });

  it("marca apenas a sessão na borda na tabela do painel", async () => {
    simularSessoesNaBorda();
    await montar("/dashboard");
    const secao = await screen.findByRole("region", { name: "Sessões recentes" });
    const [, recente, antiga] = within(secao).getAllByRole("row");
    expect(within(recente).getByText("100%")).toBeTruthy();
    expect(within(antiga).getByText("100% · Parcial")).toBeTruthy();
  });

  it("a rota /historico monta o histórico autenticado com filtro e estado vazio", async () => {
    const original = vi.mocked(fetch).getMockImplementation()!;
    let responder: ((resposta: Response) => void) | undefined;
    const sinais: AbortSignal[] = [];
    vi.mocked(fetch).mockImplementation((entrada, opcoes) => {
      if (!String(entrada).startsWith("/api/sleep-history")) return original(entrada, opcoes);
      if (opcoes?.signal) sinais.push(opcoes.signal);
      return new Promise((resolve) => { responder = resolve; });
    });

    await montar("/historico");
    expect(await screen.findByRole("heading", { name: "Histórico de sessões", level: 1 })).toBeTruthy();
    expect(await screen.findByText(/Carregando sessões/)).toBeTruthy();
    await act(async () => responder!(respostaJson([])));
    expect(await screen.findByText("Nenhuma sessão no período selecionado.")).toBeTruthy();

    fireEvent.change(screen.getByRole("combobox", { name: "Período do histórico" }), { target: { value: "30" } });
    expect(await screen.findByText(/Carregando sessões/)).toBeTruthy();
    expect(sinais[0].aborted).toBe(true);
    await act(async () => responder!(new Response(JSON.stringify({ error: "Serviço indisponível" }), { status: 503 })));
    expect(await screen.findByText("Não foi possível carregar")).toBeTruthy();

    vi.mocked(fetch).mockImplementation(original);
    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(await screen.findByText("Nenhuma sessão no período selecionado.")).toBeTruthy();
    const pedidos = vi.mocked(fetch).mock.calls
      .map(([caminho]) => new URL(String(caminho), "http://localhost"))
      .filter(({ pathname }) => pathname === "/api/sleep-history");
    const recortes = pedidos.map(({ searchParams }) => Date.parse(searchParams.get("desde") ?? ""));
    expect(recortes.at(-1)!).toBeLessThan(recortes[0]);
  });

  it("confirma o descarte antes de pausar e retoma em um toque", async () => {
    const original = vi.mocked(fetch).getMockImplementation()!;
    const aparelho = { id: "p", nome: "Travesseiro", tipo: "travesseiro", receber_leituras: true, revoked_at: null };
    const alterar = vi.fn(async (_entrada: RequestInfo | URL, opcoes?: RequestInit) => {
      Object.assign(aparelho, JSON.parse(String(opcoes?.body)));
      return respostaJson(aparelho);
    });
    const confirmar = vi.spyOn(window, "confirm").mockReturnValueOnce(false).mockReturnValueOnce(true);
    vi.mocked(fetch).mockImplementation(async (entrada, opcoes) => {
      if (String(entrada).includes("/api/devices/p/recebimento")) return alterar(entrada, opcoes);
      if (String(entrada).startsWith("/api/devices")) return respostaJson([aparelho]);
      return original(entrada, opcoes);
    });
    try {
      await montar("/dispositivos");
      const pausar = await screen.findByRole("button", { name: /pausar recebimento de travesseiro/i });
      fireEvent.click(pausar);
      expect(alterar).not.toHaveBeenCalled();
      fireEvent.click(pausar);
      expect(await screen.findByText("Pausado")).toBeTruthy();
      expect(confirmar).toHaveBeenCalledWith(
        "Enquanto pausado, as leituras deste aparelho são descartadas e não podem ser recuperadas.",
      );
      fireEvent.click(screen.getByRole("button", { name: /retomar recebimento de travesseiro/i }));
      expect(await screen.findByRole("button", { name: /pausar recebimento de travesseiro/i })).toBeTruthy();
      expect(screen.queryByText("Pausado")).toBeNull();
      expect(confirmar).toHaveBeenCalledTimes(2);
      expect(alterar.mock.calls.map(([, opcoes]) => JSON.parse(String(opcoes?.body)))).toEqual([
        { receber_leituras: false }, { receber_leituras: true },
      ]);
    } finally {
      confirmar.mockRestore();
    }
  });

  it("avisa no painel vazio que o travesseiro está pausado", async () => {
    const original = vi.mocked(fetch).getMockImplementation()!;
    vi.mocked(fetch).mockImplementation((entrada, opcoes) =>
      String(entrada).startsWith("/api/devices")
        ? Promise.resolve(respostaJson([{ id: "p", nome: "Travesseiro", tipo: "travesseiro", receber_leituras: false }]))
        : original(entrada, opcoes),
    );
    await montar("/dashboard");
    expect((await screen.findByText("Pausado:")).parentElement?.textContent).toContain("Travesseiro");
  });

  function simularPareamento() {
    const original = vi.mocked(fetch).getMockImplementation()!;
    const aparelho = { id: "novo", nome: "Travesseiro novo", tipo: "travesseiro", revoked_at: null, last_seen_at: null as string | null };
    const token = "credencial-sintetica";
    const criar = vi.fn(() => respostaJson({ device: aparelho, token }));
    const listar = vi.fn(() => respostaJson([aparelho]));
    vi.mocked(fetch).mockImplementation(async (entrada, opcoes) => {
      if (String(entrada) === "/api/devices") return opcoes?.method === "POST" ? criar() : listar();
      return original(entrada, opcoes);
    });
    return { aparelho, token, criar, listar };
  }

  async function abrirPareamento() {
    await montar("/dispositivos");
    fireEvent.click(await screen.findByRole("button", { name: "Parear dispositivo" }));
    return await screen.findByRole("button", { name: "Parear" });
  }

  it("leva o celular a Coletar sem gerar token manual", async () => {
    const { criar } = simularPareamento();
    await abrirPareamento();
    fireEvent.click(screen.getByRole("radio", { name: /celular/i }));
    fireEvent.click(screen.getByRole("link", { name: "Ir para Coletar" }));
    expect(await screen.findByRole("heading", { name: /nova coleta/i })).toBeTruthy();
    expect(criar).not.toHaveBeenCalled();
  });

  it.each([false, true])("copia a credencial ou oferece seleção manual e a remove ao fechar (%s)", async (falhar) => {
    const { token } = simularPareamento();
    const anterior = Object.getOwnPropertyDescriptor(navigator, "clipboard");
    const escrever = vi.fn(async () => { if (falhar) throw new Error("sem permissão"); });
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText: escrever } });
    try {
      fireEvent.click(await abrirPareamento());
      expect((await screen.findByText(token)).classList.contains("select-all")).toBe(true);
      fireEvent.click(screen.getByRole("button", { name: "Copiar token" }));
      expect(await screen.findByText(falhar ? /copie manualmente/i : "Token copiado.")).toBeTruthy();
      expect(escrever).toHaveBeenCalledWith(token);
      fireEvent.click(screen.getByRole("button", { name: "Ocultar pareamento" }));
      expect(screen.queryByText(token)).toBeNull();
      fireEvent.click(screen.getByRole("button", { name: "Parear dispositivo" }));
      expect(screen.queryByText(token)).toBeNull();
    } finally {
      if (anterior) Object.defineProperty(navigator, "clipboard", anterior);
      else Reflect.deleteProperty(navigator, "clipboard");
    }
  });

  it("consulta periodicamente e mostra o primeiro envio sem recarregar a página", async () => {
    const { aparelho, listar } = simularPareamento();
    const parear = await abrirPareamento();
    const visibilidade = vi.spyOn(document, "visibilityState", "get").mockReturnValue("hidden");
    vi.useFakeTimers();
    try {
      await act(async () => fireEvent.click(parear));
      expect(screen.getByText("Travesseiro · Aguardando primeiro envio")).toBeTruthy();
      const antes = listar.mock.calls.length;
      await act(async () => vi.advanceTimersByTimeAsync(15_000));
      expect(listar).toHaveBeenCalledTimes(antes);
      aparelho.last_seen_at = new Date().toISOString();
      visibilidade.mockReturnValue("visible");
      await act(async () => vi.advanceTimersByTimeAsync(15_000));
      expect(listar).toHaveBeenCalledTimes(antes + 1);
      expect(screen.queryByText(/aguardando primeiro envio/i)).toBeNull();
      expect(screen.getByText(/travesseiro · último envio/i)).toBeTruthy();
      await act(async () => vi.advanceTimersByTimeAsync(15_000));
      expect(listar).toHaveBeenCalledTimes(antes + 1);
    } finally {
      vi.useRealTimers();
      visibilidade.mockRestore();
    }
  });

  it("encerra a consulta periódica após dez minutos sem primeiro envio", async () => {
    const { listar } = simularPareamento();
    const parear = await abrirPareamento();
    const visibilidade = vi.spyOn(document, "visibilityState", "get").mockReturnValue("visible");
    vi.useFakeTimers();
    try {
      await act(async () => fireEvent.click(parear));
      await act(async () => vi.advanceTimersByTimeAsync(600_000));
      const chamadas = listar.mock.calls.length;
      await act(async () => vi.advanceTimersByTimeAsync(15_000));
      expect(listar).toHaveBeenCalledTimes(chamadas);
      expect(screen.getByRole("button", { name: "Verificar agora" })).toBeTruthy();
    } finally {
      vi.useRealTimers();
      visibilidade.mockRestore();
    }
  });

  it("verifica primeiro envio manualmente pelo cartão", async () => {
    const { aparelho } = simularPareamento();
    await montar("/dispositivos");
    aparelho.last_seen_at = new Date().toISOString();
    fireEvent.click(await screen.findByRole("button", { name: "Verificar agora" }));
    expect(await screen.findByText(/travesseiro · último envio/i)).toBeTruthy();
  });

  it("a rota /dispositivos monta o gerenciamento para a sessão autenticada", async () => {
    await montar("/dispositivos");
    expect(await screen.findByRole("heading", { name: "Dispositivos", level: 1 })).toBeTruthy();
    expect(await screen.findByText("Nenhum dispositivo pareado")).toBeTruthy();
  });

  it("a rota /configuracoes existe e passa pelos guardas até o Layout", async () => {
    await montar("/configuracoes");

    // As cinco asserções acima dependem desta, e ela merece nome próprio: se a
    // rota saísse do `App.tsx`, o `*` levaria à Landing e os erros seriam
    // "não achei o botão", que mandam procurar o botão em vez da rota.
    expect(screen.getByRole("heading", { name: /configurações/i })).toBeTruthy();
  });
});

describe("rotas esperadas (UI-18)", PRAZO, () => {
  it.each([
    ["/login", /bem-vindo de volta/i],
    ["/cadastro", /^criar conta$/i],
    ["/nova-senha", /^nova senha$/i],
    ["/dashboard", /^olá, titular$|^visão geral$/i],
    ["/coletar", /^nova coleta$/i],
    ["/historico", /^histórico de sessões$/i],
    ["/dispositivos", /^dispositivos$/i],
    ["/noite", /^a noite inteira$/i],
    ["/configuracoes", /^configurações$/i],
  ] as const)("a rota %s mostra sua tela", async (rota, titulo) => {
    if (rota === "/login" || rota === "/cadastro") sessaoDoServidor = null;
    await montar(rota);
    expect(await screen.findByRole("heading", { name: titulo })).toBeTruthy();
    expect(window.location.pathname).toBe(rota);
  });

  it("a rota / mostra a página inicial", async () => {
    await montar("/");
    expect(await screen.findByTitle("Smart Dormio — página inicial")).toBeTruthy();
    expect(window.location.pathname).toBe("/");
  });

  it("a rota /privacidade mostra a política", async () => {
    await montar("/privacidade");
    expect(await screen.findByText("Versão preliminar.", {}, { timeout: 5000 })).toBeTruthy();
    expect(window.location.pathname).toBe("/privacidade");
  });

  it("a rota * redireciona um endereço desconhecido para /", async () => {
    await montar("/rota-inexistente");
    expect(await screen.findByTitle("Smart Dormio — página inicial")).toBeTruthy();
    expect(window.location.pathname).toBe("/");
  });
});

describe("avisos no painel (UI-18)", PRAZO, () => {
  const lacuna = /faltou medição em/i;
  const inferencia = /foi estimada pelo intervalo entre elas/i;
  const escopo = /não realiza estadiamento de sono.*nem diagnóstico clínico/i;

  function responderHistorico(responder: () => Promise<Response>) {
    const original = vi.mocked(fetch).getMockImplementation()!;
    vi.mocked(fetch).mockImplementation((entrada, opcoes) =>
      String(entrada).startsWith("/api/sleep-history") ? responder() : original(entrada, opcoes),
    );
  }

  async function montarComLeituras(segundos: number[], epoca: number | null) {
    const agora = Date.now();
    responderHistorico(async () => respostaJson(segundos.map((segundo) => ({
      created_at: new Date(agora - segundo * 1000).toISOString(),
      movimento_total: 9.81, temp: null, status: "Repouso", epoca_segundos: epoca,
    }))));
    await montar("/dashboard");
    await screen.findByRole("heading", { name: "Leituras recentes" });
  }

  it("lacuna: mostra o aviso quando há interrupção no recorte", async () => {
    await montarComLeituras([0, 30, 180, 210], 30);
    fireEvent.click(await screen.findByRole("button", { name: /ver todas/i }));
    expect(screen.getByText(lacuna)).toBeTruthy();
  });

  it("lacuna: omite o aviso com cobertura contínua", async () => {
    await montarComLeituras([0, 30, 60], 30);
    expect(screen.queryByText(lacuna)).toBeNull();
  });

  it("inferência: mostra a nota com cadência estimada e sem lacuna", async () => {
    await montarComLeituras([0, 30, 60], null);
    expect(screen.getByText(inferencia)).toBeTruthy();
    expect(screen.queryByText(lacuna)).toBeNull();
  });

  it("inferência: omite a nota quando as leituras declaram a duração", async () => {
    await montarComLeituras([0, 30, 60], 30);
    expect(screen.queryByText(inferencia)).toBeNull();
  });

  it("escopo: mostra a nota no painel com leituras", async () => {
    await montarComLeituras([0, 30, 60], 30);
    expect(screen.getByText(escopo)).toBeTruthy();
  });

  it("escopo: mostra a nota no painel sem leituras", async () => {
    await montar("/dashboard");
    expect(await screen.findByText(escopo)).toBeTruthy();
  });

  it("escopo: omite a nota durante o carregamento", async () => {
    responderHistorico(() => new Promise(() => {}));
    await montar("/dashboard");
    expect(await screen.findByText("Carregando leituras...")).toBeTruthy();
    expect(screen.queryByText(escopo)).toBeNull();
  });

  it("escopo: omite a nota em caso de erro", async () => {
    responderHistorico(async () => new Response(JSON.stringify({ error: "Serviço indisponível" }), { status: 503 }));
    await montar("/dashboard");
    expect(await screen.findByText("Não foi possível carregar")).toBeTruthy();
    expect(screen.queryByText(escopo)).toBeNull();
  });
});

/** A varredura continua cobrindo rotas novas. As expectativas fixas acima detectam remoções. */
describe("toda rota do App.tsx monta (UI-17)", PRAZO, () => {
  // `process.cwd()` e não `import.meta.url`: em ambiente jsdom o
  // `import.meta.url` é uma URL `http://`, e `readFileSync` a recusa. O
  // `vitest` roda a partir da raiz do pacote, e se não rodasse o `readFileSync`
  // estouraria aqui — falha ruidosa, não lista vazia.
  const fonteDoApp = readFileSync(resolve(process.cwd(), "src/App.tsx"), "utf8");
  const rotas = [...fonteDoApp.matchAll(/<Route\s+path="([^"]+)"/g)]
    .map((m) => m[1])
    .filter((p) => p !== "*");

  it("a lista de rotas não é trivialmente pequena", () => {
    // Guarda do instrumento: um padrão que deixasse de casar devolveria lista
    // vazia, e `it.each([])` não roda teste nenhum — passaria por vazio.
    console.log(`[montagem] rotas lidas do App.tsx (${rotas.length}): ${rotas.join(", ")}`);
    expect(rotas.length).toBeGreaterThanOrEqual(6);
  });

  it.each(rotas)("a rota %s renderiza alguma coisa", async (rota) => {
    await montar(rota);
    expect(document.getElementById("root")?.childElementCount).toBeGreaterThan(0);
  });
});
