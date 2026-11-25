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
import { Capacitor } from "@capacitor/core";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { aplicabilidadeDaIdade } from "./lib/aplicabilidade";
import { VERSAO_DO_CONSENTIMENTO } from "./lib/consentimento";

// ---------------------------------------------------------------------
// Dublês de fronteira
// ---------------------------------------------------------------------

const SESSAO = {
  access_token: "jwt-de-teste",
  user: { id: "11111111-1111-1111-1111-111111111111", email: "titular@exemplo.com" },
};

let sessaoDoServidor: typeof SESSAO | null = SESSAO;
const encerrarSessao = vi.fn(async () => ({ error: null }));

vi.mock("@supabase/supabase-js", () => ({
  createClient: () => ({
    auth: {
      getSession: async () => ({ data: { session: sessaoDoServidor }, error: null }),
      // O `AuthContext` chama o `unsubscribe` ao desmontar; sem ele o teste
      // quebraria na limpeza e não no que está sob teste.
      onAuthStateChange: () => ({ data: { subscription: { unsubscribe: () => {} } } }),
      signOut: () => encerrarSessao(),
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
  encerrarSessao.mockClear();
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

  // Idem `ResizeObserver`, que o painel usava com o recharts; o stub fica, inofensivo, para o próximo componente que o use.
  vi.stubGlobal(
    "ResizeObserver",
    class {
      observe() {}
      unobserve() {}
      disconnect() {}
    },
  );
});

const raizes: Array<{ unmount: () => void }> = [];
vi.mock("react-dom/client", async (importOriginal) => {
  const original = await importOriginal<typeof import("react-dom/client")>();
  return {
    ...original,
    createRoot(...args: Parameters<typeof original.createRoot>) {
      const raiz = original.createRoot(...args);
      raizes.push(raiz);
      return raiz;
    },
  };
});

afterEach(async () => {
  await act(async () => {
    for (const raiz of raizes.splice(0)) raiz.unmount();
    await vi.dynamicImportSettled();
  });
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
  await act(async () => vi.dynamicImportSettled());
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

  it("sair encerra a sessão com signOut e leva ao login", async () => {
    await montar("/configuracoes");

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Sair da conta" }));
    });

    expect(encerrarSessao).toHaveBeenCalledTimes(1);
    expect(window.location.pathname).toBe("/login");
    expect(await screen.findByRole("button", { name: "Entrar" })).toBeTruthy();
  });

  it.each([
    ["Aparência", "radio", "Claro"],
    ["Conta", "button", "Editar dados"],
    ["Lembrete de dormir", "checkbox", "Lembrar todo dia"],
    ["Meus dispositivos", "button", "Parear"],
    ["Seus dados", "button", "Exportar meus dados (CSV)"],
    ["Sair", "button", "Sair da conta"],
    ["Excluir conta", "button", "Excluir minha conta"],
  ] as const)("agrupa a seção %s num cartão com seu controle", async (titulo, papel, nome) => {
    const lembrete = titulo === "Lembrete de dormir";
    if (lembrete) {
      vi.doMock("./lib/noiteNativa", async (original) => ({
        ...await original<typeof import("./lib/noiteNativa")>(),
        noiteNativaDisponivel: () => true,
        Noite: { lembrete: async () => ({ ativo: true, hora: 22, minuto: 30, notificacoes: true }) },
      }));
    }

    try {
      await montar(titulo === "Aparência" ? "/configuracoes?demo=1" : "/configuracoes");
      const cartao = await screen.findByRole("region", { name: titulo });
      expect(cartao.classList.contains("rounded-2xl")).toBe(true);
      expect(cartao.classList.contains("border")).toBe(true);
      expect(cartao.classList.contains("bg-card")).toBe(true);
      expect(await within(cartao).findByRole(papel, { name: nome })).toBeTruthy();
      if (titulo === "Excluir conta") {
        expect(screen.getByRole("region", { name: "Seus dados" }).contains(cartao)).toBe(false);
      }
    } finally {
      if (lembrete) vi.doUnmock("./lib/noiteNativa");
    }
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

  it("só envia a exclusão da conta depois da frase exata", async () => {
    const original = vi.mocked(fetch).getMockImplementation()!;
    const excluir = vi.fn<(opcoes?: RequestInit) => Promise<Response>>().mockResolvedValue(respostaJson({
      leituras_apagadas: 1,
      dispositivos_apagados: 1,
      perfil_apagado: true,
      conta_de_acesso_removida: true,
    }));
    vi.mocked(fetch).mockImplementation((entrada, opcoes) =>
      String(entrada) === "/api/me" ? excluir(opcoes) : original(entrada, opcoes));

    await montar("/configuracoes");
    fireEvent.click(screen.getByRole("button", { name: "Excluir minha conta" }));
    const campo = screen.getByRole("textbox", { name: /para confirmar, digite/i });
    const botao = screen.getByRole("button", { name: "Excluir definitivamente" }) as HTMLButtonElement;

    for (const texto of ["", "APAGAR MINHA NOITE", "apagar minha conta", "APAGAR MINHA CONTA "]) {
      fireEvent.change(campo, { target: { value: texto } });
      expect(botao.disabled, JSON.stringify(texto)).toBe(true);
      await act(async () => { fireEvent.click(botao); });
      expect(excluir).not.toHaveBeenCalled();
    }

    fireEvent.change(campo, { target: { value: "APAGAR MINHA CONTA" } });
    expect(botao.disabled).toBe(false);
    await act(async () => { fireEvent.click(botao); });
    expect(excluir).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({
      method: "DELETE",
      body: JSON.stringify({ confirmacao: "APAGAR MINHA CONTA" }),
    }));
    expect(await screen.findByText("Conta excluída.")).toBeTruthy();
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
    await act(async () => fireEvent.click(links[0]));
    await act(async () => vi.dynamicImportSettled());
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
    const chip = await within(tabela).findByText("Chip do sensor");
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
        return Promise.resolve(respostaJson({ ...perfilDoServidor, consentimento_saude_versao: VERSAO_DO_CONSENTIMENTO }));
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
    const aviso = "Período incompleto: só os registros mais recentes foram carregados.";
    const verTodas = await screen.findByRole("button", { name: /ver todas/i });
    expect(screen.queryByText(aviso)).toBeNull();
    fireEvent.click(verTodas);
    expect(Boolean(screen.queryByText(aviso))).toBe(quantidade === 2000);
  });

  it("marca apenas a sessão na borda na tabela do painel", async () => {
    simularSessoesNaBorda();
    await montar("/dashboard");
    // UI-40: a sessão exibida está no resumo; aqui ficam as de antes dela.
    const secao = await screen.findByRole("region", { name: "Sessões anteriores" });
    const [, ...linhas] = within(secao).getAllByRole("row");
    const antiga = linhas[linhas.length - 1];
    expect(within(secao).getAllByRole("columnheader")).toHaveLength(within(antiga).getAllByRole("cell").length);
    expect(within(antiga).getByText(/ de .+ · Parcial/)).toBeTruthy();
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

    fireEvent.click(within(screen.getByRole("group", { name: "Período do histórico" }))
      .getByRole("button", { name: "Últimos 30 dias" }));
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
        "Enquanto pausado, os registros deste aparelho são descartados e não podem ser recuperados.",
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

  it.each([
    ["Conectado", 2, true],
    ["Pausado", 2, false],
    ["Inativo", 48 * 60, true],
  ] as const)("mostra ícone, último envio e etiqueta %s no cartão do dispositivo", async (estado, minutos, receber) => {
    const original = vi.mocked(fetch).getMockImplementation()!;
    const dispositivo = {
      id: "travesseiro-estado",
      nome: "Travesseiro de teste",
      tipo: "travesseiro",
      revoked_at: null,
      last_seen_at: new Date(Date.now() - minutos * 60_000).toISOString(),
      receber_leituras: receber,
    };
    vi.mocked(fetch).mockImplementation(async (entrada, opcoes) =>
      String(entrada) === "/api/devices" ? respostaJson([dispositivo]) : original(entrada, opcoes));
    await montar("/dispositivos");
    const lista = await screen.findByRole("list", { name: "Dispositivos da conta" });
    const cartao = within(lista).getByRole("listitem");
    expect(within(cartao).getByText(dispositivo.nome)).toBeTruthy();
    expect(within(cartao).getByText(/Travesseiro · Último envio/)).toBeTruthy();
    expect(within(cartao).getByText(estado, { exact: true })).toBeTruthy();
    expect(cartao.querySelector('svg[aria-hidden="true"]')).toBeTruthy();
  });

  function simularGerenciamentoDeDispositivo() {
    const original = vi.mocked(fetch).getMockImplementation()!;
    const aparelho = {
      id: "quarto",
      nome: "Travesseiro do quarto",
      tipo: "travesseiro",
      last_seen_at: new Date().toISOString(),
      revoked_at: null as string | null,
    };
    const renomear = vi.fn((opcoes?: RequestInit) => {
      const { nome } = JSON.parse(String(opcoes?.body)) as { nome: string };
      if (nome.trim().length > 60) {
        return new Response(JSON.stringify({ error: "nome deve ter no maximo 60 caracteres" }), { status: 400 });
      }
      aparelho.nome = nome.trim();
      return respostaJson(aparelho);
    });
    const revogar = vi.fn((opcoes?: RequestInit) => {
      aparelho.revoked_at = new Date().toISOString();
      expect(opcoes?.method).toBe("POST");
      return respostaJson(aparelho);
    });
    vi.mocked(fetch).mockImplementation(async (entrada, opcoes) => {
      if (String(entrada) === "/api/devices/quarto") return renomear(opcoes);
      if (String(entrada) === "/api/devices/quarto/revogar") return revogar(opcoes);
      if (String(entrada) === "/api/devices") return respostaJson([aparelho]);
      return original(entrada, opcoes);
    });
    return { renomear, revogar };
  }

  it("envia o novo nome do dispositivo e o mostra na lista", async () => {
    const { renomear } = simularGerenciamentoDeDispositivo();
    await montar("/dispositivos");
    fireEvent.click(await screen.findByRole("button", { name: "Renomear Travesseiro do quarto" }));
    fireEvent.change(screen.getByRole("textbox", { name: "Nome do dispositivo" }), {
      target: { value: "Travesseiro da cabeceira" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Salvar nome" }));
    expect(await screen.findByText("Travesseiro da cabeceira")).toBeTruthy();
    expect(screen.queryByText("Travesseiro do quarto")).toBeNull();
    expect(renomear).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({
      method: "PATCH", body: JSON.stringify({ nome: "Travesseiro da cabeceira" }),
    }));
  });

  it.each([
    ["vazio", "   ", "Informe um nome para o dispositivo."],
    ["longo demais", "a".repeat(61), "O nome tem mais caracteres do que o permitido."],
  ])("recusa nome %s com a mensagem certa", async (_, nome, mensagem) => {
    const { renomear } = simularGerenciamentoDeDispositivo();
    await montar("/dispositivos");
    fireEvent.click(await screen.findByRole("button", { name: "Renomear Travesseiro do quarto" }));
    const campo = screen.getByRole("textbox", { name: "Nome do dispositivo" }) as HTMLInputElement;
    fireEvent.change(campo, { target: { value: nome } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar nome" }));
    expect((await screen.findByRole("alert")).textContent).toBe(mensagem);
    expect(campo.value).toBe(nome);
    expect(renomear).not.toHaveBeenCalled();
  });

  it("só revoga após confirmação e remove as ações do aparelho ativo", async () => {
    const { revogar } = simularGerenciamentoDeDispositivo();
    const confirmar = vi.spyOn(window, "confirm").mockReturnValueOnce(false).mockReturnValueOnce(true);
    try {
      await montar("/dispositivos");
      const acao = await screen.findByRole("button", { name: "Revogar Travesseiro do quarto" });
      await act(async () => { fireEvent.click(acao); });
      expect(confirmar).toHaveBeenCalledWith(expect.stringContaining('Revogar "Travesseiro do quarto"?'));
      expect(revogar).not.toHaveBeenCalled();
      expect(screen.getByRole("button", { name: "Revogar Travesseiro do quarto" })).toBe(acao);

      fireEvent.click(acao);
      expect(await screen.findByText("Revogado")).toBeTruthy();
      expect(confirmar).toHaveBeenCalledTimes(2);
      expect(revogar).toHaveBeenCalledTimes(1);
      expect(screen.queryByRole("button", { name: "Revogar Travesseiro do quarto" })).toBeNull();
      expect(screen.queryByRole("button", { name: "Renomear Travesseiro do quarto" })).toBeNull();
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

  it("pareia só o travesseiro, sem escolha de tipo (UI-42)", async () => {
    const { criar } = simularPareamento();
    await abrirPareamento();
    expect(screen.getByText("Parear um travesseiro")).toBeTruthy();
    expect(screen.queryAllByRole("radio")).toHaveLength(0);
    expect(screen.queryByText(/O novo dispositivo será um/i)).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Parear" }));
    await waitFor(() => expect(criar).toHaveBeenCalledTimes(1));
    const corpo = JSON.parse(String((vi.mocked(fetch).mock.calls.find(([u, o]) => String(u) === "/api/devices" && o?.method === "POST")?.[1] as RequestInit).body));
    expect(corpo.tipo).toBe("travesseiro");
  });

  it("no site, explica que o celular entra pela Coletar, sem gerar token manual", async () => {
    const { criar } = simularPareamento();
    await abrirPareamento();
    const explicacao = screen.getByText(/O celular não precisa de pareamento/);
    fireEvent.click(within(explicacao).getByRole("link", { name: "Coletar" }));
    expect(await screen.findByRole("heading", { name: /nova coleta/i })).toBeTruthy();
    expect(criar).not.toHaveBeenCalled();
  });

  it.each([
    ["site", false, "Coletar"],
    ["app", true, "Noite"],
  ] as const)("explica o vínculo do celular no %s", async (_, nativo, tela) => {
    const plataforma = vi.spyOn(Capacitor, "isNativePlatform").mockReturnValue(nativo);
    const plugin = vi.spyOn(Capacitor, "isPluginAvailable").mockImplementation((nome) => nome === "Noite");
    try {
      await montar("/dispositivos");
      const quadro = screen.getByRole("heading", { name: "Sobre o pareamento" }).closest("section");
      expect(quadro?.textContent).toContain(`O celular é vinculado à sua conta ao usar ${tela}.`);
    } finally {
      plataforma.mockRestore();
      plugin.mockRestore();
    }
  });

  it("no app, a explicação leva à Noite", async () => {
    const plataforma = vi.spyOn(Capacitor, "isNativePlatform").mockReturnValue(true);
    const plugin = vi.spyOn(Capacitor, "isPluginAvailable").mockImplementation((nome) => nome === "Noite");
    const { criar } = simularPareamento();
    try {
      await abrirPareamento();
      const irParaNoite = within(screen.getByText(/O celular não precisa de pareamento/)).getByRole("link", { name: "Noite" });
      expect(irParaNoite.getAttribute("href")).toBe("/noite");
      expect(criar).not.toHaveBeenCalled();
    } finally {
      plataforma.mockRestore();
      plugin.mockRestore();
    }
  });

  it.each([false, true])("copia a credencial ou oferece seleção manual e a remove ao fechar (%s)", async (falhar) => {
    const { token } = simularPareamento();
    const anterior = Object.getOwnPropertyDescriptor(navigator, "clipboard");
    const escrever = vi.fn(async () => { if (falhar) throw new Error("sem permissão"); });
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText: escrever } });
    try {
      fireEvent.click(await abrirPareamento());
      expect((await screen.findByText(token)).classList.contains("select-all")).toBe(true);
      fireEvent.click(screen.getByRole("button", { name: "Copiar código de conexão" }));
      expect(await screen.findByText(falhar ? /copie manualmente/i : "Código copiado.")).toBeTruthy();
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

  it("remove a credencial do DOM ao confirmar que já copiou", async () => {
    const { token } = simularPareamento();
    fireEvent.click(await abrirPareamento());
    expect(await screen.findByText(token)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Já copiei, pode ocultar" }));
    expect(screen.queryByText(token)).toBeNull();
    expect(screen.getByRole("button", { name: "Parear" })).toBeTruthy();
  });

  it("mostra a mensagem do ErroApi 403 no alerta de pareamento", async () => {
    const { criar } = simularPareamento();
    const mensagem = "consentimento para dado de saude pendente";
    criar.mockReturnValueOnce(new Response(JSON.stringify({ error: mensagem }), { status: 403 }));
    fireEvent.click(await abrirPareamento());
    const alerta = await screen.findByRole("alert");
    expect(alerta.textContent).toBe("Revise e aceite o consentimento para continuar.");
    expect(alerta.classList.contains("text-destructive")).toBe(true);
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

  it.each([
    ["site", "/dashboard"],
    ["site", "/historico"],
    ["site", "/dispositivos"],
    ["site", "/configuracoes"],
    ["app", "/dashboard"],
    ["app", "/historico"],
    ["app", "/dispositivos"],
    ["app", "/configuracoes"],
    ["app", "/noite"],
  ] as const)("mantém a barra lateral workspace no %s em %s", async (plataforma, rota) => {
    const app = plataforma === "app";
    const nativo = vi.spyOn(Capacitor, "isNativePlatform").mockReturnValue(app);
    const plugin = vi.spyOn(Capacitor, "isPluginAvailable").mockImplementation((nome) => nome === "Noite");
    try {
      await montar(rota);
      const barra = await screen.findByRole("navigation", { name: "Navegação principal" });
      const visaoGeral = ["Visão geral", "/dashboard", "layout-grid"];
      const historico = ["Histórico", "/historico", "clock-3"];
      const dispositivos = ["Dispositivos", "/dispositivos", "radio"];
      const trabalho = app
        ? [["Noite", "/noite", "moon"], visaoGeral, historico, dispositivos]
        : [visaoGeral, ["Nova coleta", "/coletar", "activity"], historico, dispositivos];
      expect(Array.from(barra.children, (item) => item.textContent?.trim())).toEqual([
        "Workspace", ...trabalho.map(([nome]) => nome), "Preferências", "Configurações",
      ]);
      for (const [nome, href, icone] of [...trabalho, ["Configurações", "/configuracoes", "settings"]]) {
        const link = within(barra).getByRole("link", { name: nome });
        expect(link.getAttribute("href")).toBe(href);
        expect(link.querySelector(`svg.lucide-${icone}`)).toBeTruthy();
      }
    } finally {
      nativo.mockRestore();
      plugin.mockRestore();
    }
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
    ["/dashboard", /^seus registros$/i],
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
  const lacuna = /faltou registro em/i;
  const inferencia = /foi estimada pelo intervalo entre eles/i;
  const escopo = /não é diagnóstico nem mede fases do sono/i;

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
    await screen.findByRole("heading", { name: /^Última sessão/ });
  }

  it("lacuna: mostra o aviso quando há interrupção no recorte", async () => {
    await montarComLeituras([0, 30, 180, 210], 30);
    // UI-38: a pausa curta fica na sessao, e o aviso aparece sem "Ver todas".
    expect(screen.queryByRole("button", { name: /ver todas/i })).toBeNull();
    expect(screen.getByText(lacuna)).toBeTruthy();
  });

  it("UI-38: a bancada marcada corta a sessão, e não vira pausa", async () => {
    const agora = Date.now();
    responderHistorico(async () => respostaJson(Array.from({ length: 50 }, (_, i) => ({
      created_at: new Date(agora - i * 30_000).toISOString(),
      movimento_total: 9.81, temp: null, status: "Repouso", epoca_segundos: 30,
      device_id: "d1", bancada: i >= 20 && i < 30,
    }))));
    await montar("/dashboard");
    await screen.findByRole("heading", { name: /^Última sessão/ });
    expect(screen.queryByText(lacuna)).toBeNull();
    expect(screen.getByRole("button", { name: /ver todas/i })).toBeTruthy();
  });

  it("UI-39: o resumo fala a língua do glossário", async () => {
    await montarComLeituras([0, 30, 60], 30);
    const resumo = screen.getByRole("region", { name: /^Última sessão/ }).textContent;
    for (const termo of ["Registrado", "do tempo registrado", "Maior período sem movimento registrado"]) {
      expect(resumo).toContain(termo);
    }
    expect(screen.getByText("Intensidade do movimento")).toBeTruthy();
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
    expect(await screen.findByText("Carregando registros...")).toBeTruthy();
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

describe("o painel em camadas (UI-40)", PRAZO, () => {
  function responder({ dispositivos, leituras }: { dispositivos: unknown[]; leituras: ReturnType<typeof leitura>[] }) {
    const original = vi.mocked(fetch).getMockImplementation()!;
    vi.mocked(fetch).mockImplementation((entrada, opcoes) => {
      const caminho = String(entrada);
      if (caminho.startsWith("/api/devices")) return Promise.resolve(respostaJson(dispositivos));
      if (caminho.startsWith("/api/sleep-history")) {
        const device = new URL(caminho, "http://localhost").searchParams.get("device");
        return Promise.resolve(respostaJson(device ? leituras.filter((l) => l.device_id === device) : leituras));
      }
      return original(entrada, opcoes);
    });
  }

  const travesseiro = { id: "p", nome: "Meu travesseiro", tipo: "travesseiro", last_seen_at: null, revoked_at: null };
  const celular = { id: "c", nome: "Meu celular", tipo: "celular", last_seen_at: null, revoked_at: null };
  const leitura = (segundos: number, extra = {}) => ({
    created_at: new Date(Date.now() - segundos * 1000).toISOString(),
    movimento_total: 9.81, temp: null, status: "Repouso", epoca_segundos: 30, device_id: "p", ...extra,
  });
  const detalhes = () =>
    [...document.querySelectorAll("details")].find((d) =>
      d.querySelector("summary")?.textContent?.includes("Detalhes técnicos"))!;
  /** Está na tela sem precisar abrir nada. */
  const aVista = (elemento: Element) => elemento.closest("details:not([open])") === null;

  async function abrir() {
    await montar("/dashboard");
    await screen.findByRole("heading", { name: /^(Última sessão|\d+ sessões)/ });
  }

  it("os detalhes técnicos nascem recolhidos, com fórmula, limite e tabela dentro", async () => {
    responder({ dispositivos: [travesseiro], leituras: [0, 30, 60].map((s) => leitura(s)) });
    await abrir();
    const tecnico = detalhes();
    expect(tecnico.open).toBe(false);
    expect(tecnico.textContent).toContain("magnitude");
    expect(tecnico.textContent).toContain("1,2 m/s²");
    expect(tecnico.textContent).toContain("Registros recentes");

    const fora = document.querySelector("main")!.cloneNode(true) as HTMLElement;
    fora.querySelectorAll("details, style").forEach((no) => no.remove());
    expect(fora.textContent).not.toMatch(/m\/s²|9,81|1,2|magnitude|Registros recentes/);
    // DASH-07: sem a linha do limite, só repouso parece muito movimento.
    expect(fora.textContent).toContain("Limite de movimento");
  });

  it("a ordem é resumo, gráfico, sessões anteriores, detalhes e escopo", async () => {
    responder({ dispositivos: [travesseiro], leituras: [0, 30, 60, 7200, 7230].map((s) => leitura(s)) });
    await abrir();
    const ordem = [
      screen.getByRole("heading", { name: /^Última sessão/ }),
      screen.getByRole("heading", { name: "Movimento ao longo do tempo" }),
      screen.getByRole("heading", { name: "Sessões anteriores" }),
      detalhes(),
      screen.getByText(/não é diagnóstico nem mede fases do sono/i),
    ];
    for (let i = 1; i < ordem.length; i++) {
      expect(ordem[i - 1].compareDocumentPosition(ordem[i]) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    }
  });

  it("o resumo diz o aparelho da sessão, mesmo com todos selecionados", async () => {
    responder({ dispositivos: [travesseiro, celular], leituras: [0, 30, 60].map((s) => leitura(s)) });
    await abrir();
    expect(screen.getByRole("heading", { name: "Última sessão · Meu travesseiro" })).toBeTruthy();
  });

  it("recorta o gráfico pelo horário da metade, preservando a lacuna e o resumo", async () => {
    const inicio = new Date(2026, 10, 17, 22).getTime();
    responder({
      dispositivos: [travesseiro],
      leituras: [300, 240, 60, 30, 0].map((s) => leitura(s, {
        captured_at: new Date(inicio + s * 1000).toISOString(),
        status: s >= 240 ? "Movimento" : "Repouso",
      })),
    });
    await abrir();
    const resumo = screen.getByRole("region", { name: /^Última sessão/ });
    const textoOriginal = resumo.textContent;
    const grafico = screen.getByRole("figure", { name: "Movimento ao longo do tempo" });
    const dentro = within(grafico);
    const opcao = (name: string) => dentro.getByRole("button", { name });

    expect(opcao("Noite toda").getAttribute("aria-pressed")).toBe("true");
    expect(dentro.getByRole("img", { name: /6 pontos, 2 com movimento/ })).toBeTruthy();
    fireEvent.click(opcao("1ª metade"));
    expect(opcao("1ª metade").getAttribute("aria-pressed")).toBe("true");
    expect(dentro.getByRole("img", { name: /4 pontos, 0 com movimento/ })).toBeTruthy();
    expect(grafico.querySelectorAll("[data-lacuna]")).toHaveLength(1);
    fireEvent.click(opcao("2ª metade"));
    expect(opcao("2ª metade").getAttribute("aria-pressed")).toBe("true");
    expect(dentro.getByRole("img", { name: /3 pontos, 2 com movimento/ })).toBeTruthy();
    expect(grafico.querySelectorAll("[data-lacuna]")).toHaveLength(1);
    fireEvent.click(opcao("Noite toda"));
    expect(dentro.getByRole("img", { name: /6 pontos, 2 com movimento/ })).toBeTruthy();
    expect(resumo.textContent).toBe(textoOriginal);
  });

  function selecionarSegundaMetade() {
    const segunda = screen.getByRole("button", { name: "2ª metade" });
    fireEvent.click(segunda);
    expect(segunda.getAttribute("aria-pressed")).toBe("true");
  }

  const duasSessoes = () => [0, 30, 60, 7200, 7230, 7260].map((s) => leitura(s));

  const cartaoDoAparelho = () => within(screen.getByRole("complementary", { name: "Resumo do dispositivo" }));
  const seletorDeAparelho = () => screen.getByRole<HTMLSelectElement>("combobox", { name: "Dispositivo exibido" });
  const serieDeMovimento = () => within(screen.getByRole("figure", { name: "Movimento ao longo do tempo" }));

  function responderComDoisAparelhos() {
    responder({
      dispositivos: [travesseiro, celular],
      leituras: [0, 30, 60, 90, 120].map((s) => leitura(s, {
        device_id: s < 90 ? "p" : "c",
        captured_at: new Date(Date.UTC(2026, 10, 24, 6, 0, -s)).toISOString(),
      })),
    });
  }

  it("selecionar no cartão sincroniza o topo, o gráfico e o resumo", async () => {
    responderComDoisAparelhos();
    await abrir();
    expect(serieDeMovimento().getByRole("img", { name: /5 pontos,/ })).toBeTruthy();
    fireEvent.click(cartaoDoAparelho().getByRole("button", { name: "Meu celular", pressed: false }));
    await screen.findByRole("heading", { name: "Última sessão · Meu celular" });
    expect(seletorDeAparelho().value).toBe("c");
    expect(cartaoDoAparelho().getByRole("button", { name: "Meu celular", pressed: true })).toBeTruthy();
    expect(cartaoDoAparelho().getByRole("term").textContent).toBe("Último envio");
    expect(serieDeMovimento().getByRole("img", { name: /2 pontos,/ })).toBeTruthy();
  });

  it("Todos os dispositivos no cartão restaura o resumo e o gráfico gerais", async () => {
    responderComDoisAparelhos();
    await abrir();
    fireEvent.change(seletorDeAparelho(), { target: { value: "c" } });
    await screen.findByRole("heading", { name: "Última sessão · Meu celular" });
    expect(cartaoDoAparelho().getByRole("button", { name: "Meu celular", pressed: true })).toBeTruthy();
    fireEvent.click(cartaoDoAparelho().getByRole("button", { name: "Todos os dispositivos", pressed: false }));
    await screen.findByRole("heading", { name: "Última sessão · Todos os dispositivos" });
    expect(seletorDeAparelho().value).toBe("");
    expect(cartaoDoAparelho().getByRole("button", { name: "Todos os dispositivos", pressed: true })).toBeTruthy();
    expect(serieDeMovimento().getByRole("img", { name: /5 pontos,/ })).toBeTruthy();
  });

  it("exibe o último envio direto quando só há um aparelho disponível", async () => {
    responder({
      dispositivos: [
        { ...travesseiro, last_seen_at: new Date(Date.now() - 125_000).toISOString() },
        { ...celular, revoked_at: new Date().toISOString() },
      ],
      leituras: [0, 30, 60].map((s) => leitura(s)),
    });
    await abrir();
    expect(cartaoDoAparelho().getByRole("term").textContent).toBe("Último envio");
    expect(cartaoDoAparelho().getByText("Enviou recentemente")).toBeTruthy();
    expect(cartaoDoAparelho().queryByText(/nenhum dispositivo disponível/i)).toBeNull();
  });

  it("cada aparelho disponível recebe o ícone, o último envio e a etiqueta de estado", async () => {
    const ultimoEnvio = new Date(Date.now() - 125_000).toISOString();
    responder({
      dispositivos: [
        { ...travesseiro, last_seen_at: ultimoEnvio },
        { ...celular, receber_leituras: false, last_seen_at: ultimoEnvio },
        { ...travesseiro, id: "i", nome: "De reserva" },
        { ...celular, id: "r", nome: "Revogado de exemplo", revoked_at: ultimoEnvio },
      ],
      leituras: [0, 30, 60].map((s) => leitura(s)),
    });
    await abrir();
    for (const [name, estado, icone, envio] of [
      ["Meu travesseiro", "Conectado", "radio", "há 2 minutos"],
      ["Meu celular", "Pausado", "smartphone", "há 2 minutos"],
      ["De reserva", "Inativo", "radio", "Nunca enviou dados"],
    ]) {
      const linha = cartaoDoAparelho().getByRole("button", { name });
      expect(within(linha).getByText(estado)).toBeTruthy();
      expect(within(linha).getByText(envio)).toBeTruthy();
      expect(linha.querySelector(`svg.lucide-${icone}`)).toBeTruthy();
    }
    expect(cartaoDoAparelho().queryByText("Revogado de exemplo")).toBeNull();
    expect(screen.getByRole("option", { name: /Revogado de exemplo/ })).toBeTruthy();
  });

  it("volta para Noite toda ao trocar de aparelho", async () => {
    responder({
      dispositivos: [travesseiro, celular],
      leituras: [0, 30, 60, 7200, 7230, 7260].map((s) => leitura(s, { device_id: s < 100 ? "p" : "c" })),
    });
    await abrir();
    selecionarSegundaMetade();
    fireEvent.change(screen.getByRole("combobox", { name: "Dispositivo exibido" }), { target: { value: "c" } });
    await screen.findByRole("heading", { name: "Última sessão · Meu celular" });
    expect(screen.getByRole("button", { name: "Noite toda", pressed: true })).toBeTruthy();
  });

  it("volta para Noite toda ao alternar entre todas e a última sessão", async () => {
    responder({ dispositivos: [travesseiro], leituras: duasSessoes() });
    await abrir();
    selecionarSegundaMetade();
    fireEvent.click(screen.getByRole("button", { name: /ver todas/i }));
    fireEvent.click(screen.getByRole("button", { name: "Ver só a última" }));
    expect(screen.getByRole("button", { name: "Noite toda", pressed: true })).toBeTruthy();
  });

  it("esconde o seletor de período quando mostra todas as sessões", async () => {
    responder({ dispositivos: [travesseiro], leituras: duasSessoes() });
    await abrir();
    expect(screen.getByRole("group", { name: "Período do gráfico" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /ver todas/i }));
    expect(screen.queryByRole("group", { name: "Período do gráfico" })).toBeNull();
  });

  it("sem sessão anterior, diz isso em vez de repetir a atual", async () => {
    responder({ dispositivos: [travesseiro], leituras: [0, 30, 60].map((s) => leitura(s)) });
    await abrir();
    expect(screen.getByText("Nenhuma sessão anterior nos registros carregados.")).toBeTruthy();
  });

  it("nenhum aviso de falha fica escondido", async () => {
    responder({
      dispositivos: [{ ...travesseiro, receber_leituras: false }, celular],
      // Com pausa e sem duração declarada em parte: lacuna e inferência juntas.
      leituras: [0, 30, 60, 300, 330, 360].map((s) =>
        leitura(s, { device_id: s < 100 ? "p" : "c", epoca_segundos: s === 30 ? null : 30 })),
    });
    await abrir();
    for (const aviso of [
      /leituras? recebidas|registros recebidos durante a pausa/i,
      /faltou registro em/i,
      /o registro parou 1 vez/i,
      /foi estimada pelo intervalo entre eles/i,
      /medem o mesmo movimento de formas diferentes/i,
      /não é diagnóstico nem mede fases do sono/i,
    ]) {
      const achados = screen.getAllByText((_, elemento) =>
        elemento?.tagName === "P" && aviso.test(elemento.textContent ?? ""));
      expect(achados.length, String(aviso)).toBeGreaterThan(0);
      for (const elemento of achados) expect(aVista(elemento), String(aviso)).toBe(true);
    }
  });

  it("em todas as sessões, os detalhes não dividem pelo intervalo entre elas", async () => {
    responder({ dispositivos: [travesseiro], leituras: [0, 30, 60, 7200, 7230].map((s) => leitura(s)) });
    await abrir();
    expect(detalhes().textContent).toContain("do período.");
    fireEvent.click(screen.getByRole("button", { name: /ver todas/i }));
    expect(detalhes().textContent).not.toContain("do período.");
  });

  it("o limite de registros e o estado do envio ficam à vista", async () => {
    responder({ dispositivos: [travesseiro], leituras: Array.from({ length: 2000 }, (_, i) => leitura(i * 30)) });
    await abrir();
    expect(aVista(screen.getByText(/^Período incompleto/))).toBe(true);
    expect(aVista(screen.getByText("Nunca enviou"))).toBe(true);
  });
});
