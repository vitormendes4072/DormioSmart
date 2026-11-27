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
import { LIMITE_DO_PAINEL, MAX_PAGINAS_DO_HISTORICO } from "./lib/api";
import { VERSAO_DO_CONSENTIMENTO } from "./lib/consentimento";

// ---------------------------------------------------------------------
// Dublês de fronteira
// ---------------------------------------------------------------------

const SESSAO = {
  access_token: "jwt-de-teste",
  user: { id: "11111111-1111-1111-1111-111111111111", email: "titular@exemplo.com" },
};

let sessaoDoServidor: typeof SESSAO | null = SESSAO;
let publicarSessao: ((evento: string, sessao: typeof SESSAO) => void) | undefined;
const encerrarSessao = vi.fn(async () => ({ error: null }));

vi.mock("@supabase/supabase-js", () => ({
  createClient: () => ({
    auth: {
      getSession: async () => ({ data: { session: sessaoDoServidor }, error: null }),
      // O `AuthContext` chama o `unsubscribe` ao desmontar; sem ele o teste
      // quebraria na limpeza e não no que está sob teste.
      onAuthStateChange: (notificar: typeof publicarSessao) => {
        publicarSessao = notificar;
        return { data: { subscription: { unsubscribe: () => {} } } };
      },
      signOut: () => encerrarSessao(),
      updateUser: async () => ({ data: { user: SESSAO.user }, error: null }),
      signInWithPassword: async () => {
        publicarSessao?.("SIGNED_IN", SESSAO);
        return { error: null };
      },
      signUp: async () => {
        publicarSessao?.("SIGNED_IN", SESSAO);
        return { data: { session: SESSAO }, error: null };
      },
    },
  }),
}));

/** Perfil que a rota devolve nesta execução. Trocado por teste. */
let perfilDoServidor: { nome: string | null; idade: number | null; meta_diaria_min?: number | null; consentimento_saude_em?: string; consentimento_saude_versao?: string } = {
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
  publicarSessao = undefined;
  for (const chave of ["dormio-primeiros-passos-", "dormio-jornada-", "dormio-primeira-sessao-", "dormio-conta-com-registro-"]) {
    localStorage.removeItem(chave + SESSAO.user.id);
  }
  localStorage.removeItem("dormio-historico-aparelho");
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

/** UI-48/49: sem observador, mede pela janela como antes. */
function simularTelaLarga() {
  vi.stubGlobal("ResizeObserver", undefined);
  vi.stubGlobal("matchMedia", (consulta: string) => ({
    matches: consulta === "(min-width: 1050px)",
    media: consulta,
    addEventListener: () => {},
    removeEventListener: () => {},
  }));
}

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
    const verTodas = await screen.findByRole("button", { name: /ver as \d+ sessões/i });
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
    expect(await screen.findByText("Ainda não há sessões.")).toBeTruthy();
    const pedidos = vi.mocked(fetch).mock.calls
      .map(([caminho]) => new URL(String(caminho), "http://localhost"))
      .filter(({ pathname, searchParams }) => pathname === "/api/sleep-history" && searchParams.has("desde"));
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
    ["site", false, "Coletar registra sessões curtas e vincula o celular à sua conta."],
    ["app", true, "O celular é vinculado à sua conta depois da primeira gravação em Noite."],
  ] as const)("explica o vínculo do celular no %s", async (_, nativo, mensagem) => {
    const plataforma = vi.spyOn(Capacitor, "isNativePlatform").mockReturnValue(nativo);
    const plugin = vi.spyOn(Capacitor, "isPluginAvailable").mockImplementation((nome) => nome === "Noite");
    try {
      await montar("/dispositivos");
      const quadro = screen.getByRole("heading", { name: "Sobre o pareamento" }).closest("section");
      expect(quadro?.textContent).toContain(mensagem);
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
    expect(await screen.findByText(/^Nenhum aparelho conectado\./)).toBeTruthy();
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

describe("barra lateral recolhível (UI-50)", PRAZO, () => {
  const chave = "dormio-menu-lateral";
  const menu = () => within(screen.getByRole("navigation", { name: "Navegação principal" }));
  const alternador = (aberto: boolean) => screen.getByRole("button", {
    name: aberto ? "Recolher menu" : "Expandir menu", expanded: aberto,
  });

  beforeEach(() => window.localStorage.removeItem(chave));
  afterEach(() => window.localStorage.removeItem(chave));

  it("abre expandida e salva a escolha ao recolher e ao expandir", async () => {
    await montar("/dashboard?demo=1");
    const botao = alternador(true);
    fireEvent.click(botao);
    expect(alternador(false)).toBe(botao);
    expect(window.localStorage.getItem(chave)).toBe("recolhido");
    fireEvent.click(botao);
    expect(alternador(true)).toBe(botao);
    expect(window.localStorage.getItem(chave)).toBe("expandido");
  });

  it.each([["recolhido", false], ["valor estranho", true]] as const)(
    "restaura a preferência %s em uma montagem nova", async (salvo, aberto) => {
      window.localStorage.setItem(chave, salvo);
      await montar("/historico");
      expect(alternador(aberto)).toBeTruthy();
    },
  );

  it.each([["site", false, "Nova coleta", "/coletar"], ["Android", true, "Noite", "/noite"]] as const)(
    "mantém os destinos e os nomes acessíveis no trilho do %s", async (_, app, coleta, rota) => {
      const nativo = vi.spyOn(Capacitor, "isNativePlatform").mockReturnValue(app);
      const plugin = vi.spyOn(Capacitor, "isPluginAvailable").mockImplementation((nome) => nome === "Noite");
      window.localStorage.setItem(chave, "recolhido");
      try {
        await montar("/historico");
        const destinos = [
          ["Visão geral", "/dashboard"], [coleta, rota], ["Histórico", "/historico"],
          ["Dispositivos", "/dispositivos"], ["Configurações", "/configuracoes"],
        ];
        for (const [nome, destino] of destinos) {
          const link = menu().getByRole("link", { name: nome });
          expect(link.getAttribute("href")).toBe(destino);
          expect(link.getAttribute("aria-label")).toBe(nome);
        }
        expect(menu().getByRole("link", { name: "Histórico" }).getAttribute("aria-current")).toBe("page");
        const barra = screen.getByRole("navigation", { name: "Navegação principal" }).closest("aside")!;
        expect(within(barra).getByRole("button", { name: "Sair" }).querySelector("svg")).toBeTruthy();
      } finally {
        nativo.mockRestore();
        plugin.mockRestore();
      }
    },
  );

  it("mantém a conta de demonstração e a navegação móvel", async () => {
    window.localStorage.setItem(chave, "recolhido");
    await montar("/dashboard?demo=1");
    const barra = screen.getByRole("navigation", { name: "Navegação principal" }).closest("aside")!;
    expect(within(barra).getAllByText("Demonstração").length).toBeGreaterThan(0);
    expect(within(barra).queryByRole("button", { name: "Sair" })).toBeNull();
    const movel = within(screen.getByRole("navigation", { name: "Navegação móvel" }));
    expect(movel.getByRole("link", { name: "Histórico" }).getAttribute("href")).toBe("/historico?demo=1");
    expect(alternador(false).closest("aside")).toBe(barra);
    expect(barra.classList.contains("hidden")).toBe(true);
    expect(barra.classList.contains("md:flex")).toBe(true);
  });

  it("usa o mesmo limiar útil com o menu nos dois estados e mantém a instância do gráfico", async () => {
    let notificar: ResizeObserverCallback | undefined;
    let observado: Element | undefined;
    vi.stubGlobal("ResizeObserver", class {
      constructor(callback: ResizeObserverCallback) { notificar = callback; }
      observe(elemento: Element) { observado = elemento; }
      disconnect() {}
    });
    const largura = vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockImplementation(function (this: HTMLElement) {
      return this.tagName === "MAIN" ? 766 : 0;
    });
    try {
      await montar("/dashboard?demo=1");
      const grafico = await screen.findByRole("region", { name: "Tempo registrado por dia" });
      const calendario = screen.getByRole("region", { name: "Calendário de registros" });
      const emDuasColunas = () => grafico.closest("[data-vaga-do-grafico]") !== null;
      const medir = async (width: number) => {
        await act(async () => notificar?.([{ contentRect: { width } } as ResizeObserverEntry], {} as ResizeObserver));
        expect(screen.getByRole("region", { name: "Tempo registrado por dia" })).toBe(grafico);
        expect(screen.getByRole("region", { name: "Calendário de registros" })).toBe(calendario);
      };
      expect(observado).toBe(document.querySelector("main"));
      expect(emDuasColunas()).toBe(true);
      fireEvent.click(alternador(true));
      await medir(766);
      expect(emDuasColunas()).toBe(true);
      await medir(765);
      expect(emDuasColunas()).toBe(false);
      fireEvent.click(alternador(false));
      await medir(765);
      expect(emDuasColunas()).toBe(false);
      await medir(766);
      expect(emDuasColunas()).toBe(true);
    } finally {
      largura.mockRestore();
    }
  });

  it("UI-50: mantém duas colunas com 751 px úteis a 1050 px e rolagem clássica", async () => {
    vi.stubGlobal("innerWidth", 1050);
    const largura = vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockImplementation(function (this: HTMLElement) {
      // A janela mede 1050 px, dos quais 15 px são da barra de rolagem.
      if (this.tagName === "HTML") return 1035;
      return this.tagName === "MAIN" ? 751 : 0;
    });
    try {
      await montar("/dashboard?demo=1");
      expect(alternador(true)).toBeTruthy();
      const grafico = await screen.findByRole("region", { name: "Tempo registrado por dia" });
      expect(grafico.closest("[data-vaga-do-grafico]")).not.toBeNull();
    } finally {
      largura.mockRestore();
    }
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
    await screen.findByRole("heading", { name: "Seus registros" });
  }

  it("lacuna: mostra o aviso quando há interrupção no recorte", async () => {
    await montarComLeituras([0, 30, 180, 210], 30);
    // UI-38: a pausa curta fica na sessao, e o aviso aparece sem "Ver todas".
    expect(screen.queryByRole("button", { name: /ver as \d+ sessões/i })).toBeNull();
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
    await screen.findByRole("heading", { name: "Seus registros" });
    expect(screen.queryByText(lacuna)).toBeNull();
    expect(screen.getByRole("button", { name: /ver as \d+ sessões/i })).toBeTruthy();
  });

  it("UI-39: o resumo fala a língua do glossário", async () => {
    await montarComLeituras([0, 30, 60], 30);
    const resumo = screen.getByRole("region", { name: "Seus registros" }).textContent;
    for (const termo of ["Tempo registrado", "no tempo registrado", "Maior período sem movimento registrado"]) {
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

  it("escopo: a abertura da jornada explica os limites do registro", async () => {
    await montar("/primeiros-passos");
    expect(await screen.findByText("Não é diagnóstico e não mede o sono.")).toBeTruthy();
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

describe("jornada automática após autenticar (UI-62)", PRAZO, () => {
  it.each(["/login", "/cadastro"])("abre Primeiros passos para conta vazia autenticada a partir de %s", async (rota) => {
    sessaoDoServidor = null;
    const nativo = vi.spyOn(Capacitor, "isNativePlatform").mockReturnValue(true);
    const plugin = vi.spyOn(Capacitor, "isPluginAvailable").mockImplementation((nome) => nome === "Noite");
    try {
      await montar(rota);
      if (rota === "/cadastro") {
        fireEvent.change(screen.getByLabelText("Nome completo"), { target: { value: "Conta de teste" } });
        fireEvent.click(screen.getByRole("checkbox"));
      }
      fireEvent.change(screen.getByLabelText("E-mail"), { target: { value: "titular@exemplo.com" } });
      fireEvent.change(screen.getByLabelText("Senha"), { target: { value: "senha-segura-de-teste" } });
      fireEvent.click(screen.getByRole("button", { name: rota === "/cadastro" ? "Criar conta" : "Entrar" }));
      expect(await screen.findByRole("heading", { name: "Primeiros passos" }, { timeout: 8000 })).toBeTruthy();
      expect(window.location.pathname).toBe("/primeiros-passos");
    } finally {
      plugin.mockRestore();
      nativo.mockRestore();
    }
  });

  it("no Android volta ao destino Noite após a jornada ter sido vista", async () => {
    localStorage.setItem("dormio-jornada-" + SESSAO.user.id, JSON.stringify({ passo: "meta", caminho: "celular" }));
    const nativo = vi.spyOn(Capacitor, "isNativePlatform").mockReturnValue(true);
    const plugin = vi.spyOn(Capacitor, "isPluginAvailable").mockImplementation((nome) => nome === "Noite");
    try {
      await montar("/entrada");
      expect(await screen.findByRole("heading", { name: "A noite inteira" })).toBeTruthy();
      expect(window.location.pathname).toBe("/noite");
      expect(vi.mocked(fetch).mock.calls.some(([url]) => String(url).startsWith("/api/sleep-history"))).toBe(false);
    } finally {
      plugin.mockRestore();
      nativo.mockRestore();
    }
  });

  it("na segunda abertura do app, uma conta com registro vai à Noite sem consultar o histórico", async () => {
    const nativo = vi.spyOn(Capacitor, "isNativePlatform").mockReturnValue(true);
    const plugin = vi.spyOn(Capacitor, "isPluginAvailable").mockImplementation((nome) => nome === "Noite");
    const original = vi.mocked(fetch).getMockImplementation()!;
    let consultas = 0;
    vi.mocked(fetch).mockImplementation(async (url, opcoes) => {
      if (!String(url).startsWith("/api/sleep-history")) return original(url, opcoes);
      consultas++;
      return respostaJson([{ created_at: "2026-11-27T12:00:00Z", bancada: false }]);
    });
    try {
      await montar("/");
      await screen.findByRole("heading", { name: "A noite inteira" });
      expect(consultas).toBe(1);
      await act(async () => {
        window.history.pushState({}, "", "/");
        window.dispatchEvent(new PopStateEvent("popstate"));
      });
      await screen.findByRole("heading", { name: "A noite inteira" });
      expect(window.location.pathname).toBe("/noite");
      expect(consultas).toBe(1);
    } finally {
      plugin.mockRestore();
      nativo.mockRestore();
    }
  });

  it("sem rede, uma conta sem marca chega à Noite em até três segundos", async () => {
    const nativo = vi.spyOn(Capacitor, "isNativePlatform").mockReturnValue(true);
    const plugin = vi.spyOn(Capacitor, "isPluginAvailable").mockImplementation((nome) => nome === "Noite");
    const original = vi.mocked(fetch).getMockImplementation()!;
    let consulta: AbortSignal | null | undefined;
    let responderComVazio: ((resposta: Response) => void) | undefined;
    vi.mocked(fetch).mockImplementation((url, opcoes) => {
      if (!String(url).startsWith("/api/sleep-history")) return original(url, opcoes);
      consulta = opcoes?.signal;
      return new Promise<Response>((resolve) => { responderComVazio = resolve; });
    });
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
    try {
      await montar("/");
      expect(window.location.pathname).toBe("/entrada");
      expect(consulta?.aborted).toBe(false);
      await act(() => vi.advanceTimersByTimeAsync(3_000));
      expect(window.location.pathname).toBe("/noite");
      expect(consulta?.aborted).toBe(true);
      await act(async () => {
        responderComVazio?.(respostaJson([]));
        await vi.dynamicImportSettled();
      });
      expect(screen.getByRole("heading", { name: "A noite inteira" })).toBeTruthy();
      expect(screen.queryByRole("heading", { name: "Primeiros passos" })).toBeNull();
    } finally {
      vi.useRealTimers();
      plugin.mockRestore();
      nativo.mockRestore();
    }
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

  describe("jornada e Início (UI-57, UI-62 e UI-63)", () => {
    const faixa = () => within(screen.getByRole("region", { name: "Próximo passo" }));

    it("UI-62: o site mostra o APK, orienta a usar o mesmo e-mail e oferece a meta sem idade", async () => {
      await montar("/entrada");
      const comeco = await screen.findByRole("heading", { name: "Primeiros passos" });
      expect(document.activeElement).toBe(comeco);
      expect(screen.getByRole("img", { name: "Smart Dormio" })).toBeTruthy();
      const progresso = screen.getByRole("progressbar", { name: "Progresso dos primeiros passos" });
      expect(progresso.getAttribute("aria-valuenow")).toBe("1");
      expect(progresso.getAttribute("aria-valuemax")).toBe("5");
      fireEvent.click(screen.getByRole("button", { name: "Começar" }));
      expect(document.activeElement).toBe(screen.getByRole("heading", { name: "Como você vai registrar?" }));
      expect(progresso.getAttribute("aria-valuenow")).toBe("2");
      const celular = screen.getByRole("button", { name: "Celular", description: "App para Android, sobre o colchão" });
      expect(screen.getByRole("button", { name: "Travesseiro", description: "O sensor dentro da fronha" })).toBeTruthy();
      fireEvent.click(celular);
      expect(screen.getByRole("img", { name: /QR code para baixar/ })).toBeTruthy();
      expect(screen.getByRole("link", { name: "Baixar o app para Android" }).getAttribute("href")).toMatch(/releases\/latest/);
      fireEvent.click(screen.getByRole("button", { name: "Voltar" }));
      await screen.findByRole("heading", { name: "Como você vai registrar?" });
      fireEvent.click(screen.getByRole("button", { name: "Celular" }));
      fireEvent.click(screen.getByRole("button", { name: "Já instalei" }));
      expect(screen.getByText("Passo 4 de 5")).toBeTruthy();
      expect(screen.queryByLabelText(/idade/i)).toBeNull();
      fireEvent.click(screen.getByRole("button", { name: "Definir depois" }));
      expect(screen.getByText(/Entre no app com o mesmo e-mail desta conta/i)).toBeTruthy();
      fireEvent.click(screen.getByRole("button", { name: "Ir para o Início" }));
      expect(await faixaApareceu()).toBeTruthy();
      expect(faixa().getByText("Falta a primeira sessão")).toBeTruthy();
    });

    function faixaApareceu() {
      return screen.findByRole("region", { name: "Próximo passo" }, { timeout: 5000 });
    }

    it("UI-62: o teste no navegador abre Coletar e deixa a meta para a retomada", async () => {
      await montar("/primeiros-passos");
      fireEvent.click(await screen.findByRole("button", { name: "Começar" }));
      fireEvent.click(screen.getByRole("button", { name: "Celular" }));
      fireEvent.click(screen.getByRole("button", { name: "Testar no navegador (sessão curta)" }));
      await waitFor(() => expect(window.location.pathname).toBe("/coletar"));
      expect(localStorage.getItem("dormio-jornada-" + SESSAO.user.id)).toContain('"passo":"meta"');
    });

    it("UI-62: retoma o travesseiro, tenta novamente e avança só com o primeiro sinal do aparelho pareado", async () => {
      const original = vi.mocked(fetch).getMockImplementation()!;
      let criado = false;
      let indisponivel = false;
      let sinal = false;
      const outro = { ...travesseiro, id: "outro", last_seen_at: "2026-11-27T12:00:00Z" };
      vi.mocked(fetch).mockImplementation(async (entrada, opcoes) => {
        if (String(entrada) !== "/api/devices") return original(entrada, opcoes);
        if (opcoes?.method === "POST") {
          criado = true;
          return respostaJson({ device: travesseiro, token: "codigo-sintetico-para-o-teste" });
        }
        if (!criado) return respostaJson([]);
        if (indisponivel && opcoes?.signal) throw new Error("indisponível");
        return respostaJson([{ ...travesseiro, last_seen_at: sinal ? outro.last_seen_at : null }, outro]);
      });
      await montar("/primeiros-passos");
      fireEvent.click(await screen.findByRole("button", { name: "Começar" }));
      fireEvent.click(screen.getByRole("button", { name: "Travesseiro" }));
      const gerar = screen.getByRole<HTMLButtonElement>("button", { name: "Gerar código de conexão" });
      await waitFor(() => expect(gerar.disabled).toBe(false));
      fireEvent.click(gerar);
      expect(await screen.findByText("O código precisa ser gravado na placa do travesseiro.")).toBeTruthy();
      expect(localStorage.getItem("dormio-jornada-" + SESSAO.user.id)).not.toContain("codigo-sintetico");
      fireEvent.click(screen.getByRole("button", { name: "Já copiei, aguardar sinal" }));
      await screen.findByRole("heading", { name: "Aguardando o travesseiro" });
      expect(screen.queryByText("Recebemos o primeiro sinal dele")).toBeNull();
      fireEvent.click(screen.getByRole("button", { name: "Continuar depois" }));
      await faixaApareceu();
      expect(faixa().getByText("Falta conectar o travesseiro")).toBeTruthy();
      indisponivel = true;
      fireEvent.click(faixa().getByRole("link", { name: "Continuar" }));
      const tentar = await screen.findByRole("button", { name: "Tentar novamente" });
      sinal = true;
      indisponivel = false;
      fireEvent.click(tentar);
      expect(await screen.findByRole("heading", { name: "Recebemos o primeiro sinal dele" })).toBeTruthy();
    });

    it("UI-62: a jornada valida a meta do UI-61 e salva só esse campo", async () => {
      const original = vi.mocked(fetch).getMockImplementation()!;
      const alteracoes: unknown[] = [];
      vi.mocked(fetch).mockImplementation((entrada, opcoes) => {
        if (String(entrada) === "/api/me/perfil" && opcoes?.method === "PATCH") {
          const dados = JSON.parse(String(opcoes.body));
          alteracoes.push(dados);
          perfilDoServidor = { ...perfilDoServidor, ...dados };
          return Promise.resolve(respostaJson(perfilDoServidor));
        }
        return original(entrada, opcoes);
      });
      await montar("/primeiros-passos");
      fireEvent.click(await screen.findByRole("button", { name: "Começar" }));
      fireEvent.click(screen.getByRole("button", { name: "Celular" }));
      fireEvent.click(screen.getByRole("button", { name: "Já instalei" }));
      const campo = screen.getByLabelText("Meta de tempo registrado por dia");
      fireEvent.change(campo, { target: { value: "7:13" } });
      fireEvent.click(screen.getByRole("button", { name: "Salvar meta" }));
      expect(await screen.findByRole("alert")).toBeTruthy();
      expect(alteracoes).toEqual([]);
      fireEvent.change(campo, { target: { value: "7:15" } });
      fireEvent.click(screen.getByRole("button", { name: "Salvar meta" }));
      expect(await screen.findByRole("heading", { name: "Tudo pronto para hoje à noite" })).toBeTruthy();
      expect(alteracoes).toEqual([{ meta_diaria_min: 435 }]);
    });

    it("UI-61: Editar dados salva a meta na conta e campo em branco a remove", async () => {
      const original = vi.mocked(fetch).getMockImplementation()!;
      const alteracoes: unknown[] = [];
      vi.mocked(fetch).mockImplementation((entrada, opcoes) => {
        if (String(entrada) === "/api/me/perfil" && opcoes?.method === "PATCH") {
          const corpo = JSON.parse(String(opcoes.body));
          alteracoes.push(corpo);
          perfilDoServidor = { ...perfilDoServidor, ...corpo };
          return Promise.resolve(respostaJson(perfilDoServidor));
        }
        return original(entrada, opcoes);
      });
      await montar("/configuracoes");
      fireEvent.click(await screen.findByRole("button", { name: "Editar dados" }));
      const meta = screen.getByLabelText("Meta de tempo registrado por dia");
      expect((meta as HTMLInputElement).value).toBe("");
      fireEvent.change(meta, { target: { value: "7:45" } });
      fireEvent.click(screen.getByRole("button", { name: "Salvar" }));
      await waitFor(() => expect(alteracoes).toEqual([{ meta_diaria_min: 465 }]));
      const fechar = screen.getByRole<HTMLButtonElement>("button", { name: "Cancelar" });
      await waitFor(() => expect(fechar.disabled).toBe(false));
      fireEvent.click(fechar);
      const salvo = await screen.findByRole("button", { name: "Editar dados" });
      fireEvent.click(salvo);
      const preenchido = screen.getByLabelText("Meta de tempo registrado por dia");
      expect((preenchido as HTMLInputElement).value).toBe("7:45");
      fireEvent.change(preenchido, { target: { value: "" } });
      fireEvent.click(screen.getByRole("button", { name: "Salvar" }));
      await waitFor(() => expect(alteracoes).toEqual([{ meta_diaria_min: 465 }, { meta_diaria_min: null }]));
    });

    it("UI-57: mostra as ações de primeira utilização e abre o pareamento", async () => {
      await montar("/dashboard");
      await faixaApareceu();
      expect(await screen.findByText("Os dias com registro aparecem marcados aqui.")).toBeTruthy();
      expect(await screen.findByText("Depois da primeira sessão, o tempo registrado de cada dia aparece aqui.")).toBeTruthy();
      expect(cartaoDoAparelho().getByText("Nenhum aparelho conectado ainda.")).toBeTruthy();
      expect(screen.queryByText(/verifique se ele está ligado/i)).toBeNull();
      fireEvent.click(cartaoDoAparelho().getByRole("link", { name: "Parear o travesseiro" }));
      expect(await screen.findByRole("heading", { name: "Parear um travesseiro" })).toBeTruthy();
      expect(screen.getByRole("link", { name: "Baixar o app" }).getAttribute("href")).toMatch(/releases\/latest/);
      expect(screen.getByText(/depois de registrar uma sessão curta em/)).toBeTruthy();
    });

    it("UI-62: bancada não impede a abertura inicial, que acontece uma vez por conta", async () => {
      responder({ dispositivos: [], leituras: [leitura(0, { bancada: true })] });
      await montar("/entrada");
      await screen.findByRole("heading", { name: "Primeiros passos" });
      fireEvent.click(screen.getByRole("button", { name: "Voltar" }));
      expect(await faixaApareceu()).toBeTruthy();
      await act(async () => {
        window.history.pushState({}, "", "/entrada");
        window.dispatchEvent(new PopStateEvent("popstate"));
      });
      expect(await faixaApareceu()).toBeTruthy();
      expect(window.location.pathname).toBe("/dashboard");
      expect(screen.queryByRole("heading", { name: "Primeiros passos" })).toBeNull();
    });

    it("UI-62: conta com registros não abre a jornada", async () => {
      responder({ dispositivos: [travesseiro], leituras: [leitura(30), leitura(0)] });
      await montar("/entrada");
      await waitFor(() => expect(window.location.pathname).toBe("/dashboard"));
      expect(await screen.findByText("Intensidade do movimento")).toBeTruthy();
      expect(screen.queryByRole("heading", { name: "Primeiros passos" })).toBeNull();
      expect(screen.queryByText(/Sua primeira sessão/)).toBeNull();
    });

    it("UI-62: falha na entrada segue ao destino normal", async () => {
      const original = vi.mocked(fetch).getMockImplementation()!;
      vi.mocked(fetch).mockImplementation((url, opcoes) =>
        String(url).startsWith("/api/sleep-history") ? Promise.reject(new Error("Indisponível")) : original(url, opcoes));
      await montar("/entrada");
      expect(await screen.findByText("Não foi possível carregar")).toBeTruthy();
      expect(window.location.pathname).toBe("/dashboard");
      expect(screen.queryByRole("heading", { name: "Primeiros passos" })).toBeNull();
    });

    it("mantém o guia oculto após 16 páginas cheias apenas de bancada", async () => {
      const original = vi.mocked(fetch).getMockImplementation()!;
      let paginas = 0;
      vi.mocked(fetch).mockImplementation(async (entrada, opcoes) => {
        const { pathname, searchParams } = new URL(String(entrada), "http://localhost");
        if (pathname !== "/api/sleep-history" || searchParams.has("desde")) return original(entrada, opcoes);
        const pagina = ++paginas;
        if (pagina > MAX_PAGINAS_DO_HISTORICO * 2) return respostaJson([]);
        return respostaJson(Array.from({ length: LIMITE_DO_PAINEL }, (_, indice) =>
          leitura(pagina * LIMITE_DO_PAINEL + indice, { id: `${pagina}-${indice}`, bancada: true })));
      });

      await montar("/entrada");
      await waitFor(() => expect(window.location.pathname).toBe("/dashboard"));
      expect(screen.queryByRole("heading", { name: "Primeiros passos" })).toBeNull();
      await waitFor(() => expect(paginas).toBe(MAX_PAGINAS_DO_HISTORICO * 2));
      expect(await screen.findByText("Sem registros no recorte carregado.")).toBeTruthy();
      expect(screen.queryByRole("region", { name: "Próximo passo" })).toBeNull();
    });

    it("mantém o guia oculto quando a consulta da conta falha e o aparelho selecionado não tem registros", async () => {
      responder({ dispositivos: [travesseiro, celular], leituras: [] });
      const original = vi.mocked(fetch).getMockImplementation()!;
      let pedidosDaConta = 0;
      let pedidosDoAparelho = 0;
      let rejeitarConta!: (erro: Error) => void;
      const consultaDaConta = new Promise<Response>((_, rejeitar) => { rejeitarConta = rejeitar; });
      vi.mocked(fetch).mockImplementation((entrada, opcoes) => {
        const { pathname, searchParams } = new URL(String(entrada), "http://localhost");
        if (pathname === "/api/sleep-history" && !searchParams.has("desde")) {
          if (!searchParams.has("device")) {
            pedidosDaConta++;
            return consultaDaConta;
          }
          if (searchParams.get("device") === travesseiro.id) pedidosDoAparelho++;
        }
        return original(entrada, opcoes);
      });

      await montar("/dashboard");
      const seletor = await screen.findByRole("combobox", { name: "Dispositivo exibido" });
      fireEvent.change(seletor, { target: { value: travesseiro.id } });
      await waitFor(() => expect(pedidosDoAparelho).toBeGreaterThan(0));
      expect(pedidosDaConta).toBeGreaterThan(0);
      await act(async () => rejeitarConta(new Error("Consulta da conta indisponível")));
      expect(await screen.findByText("Sem registros no recorte carregado.")).toBeTruthy();
      expect(screen.queryByRole("region", { name: "Próximo passo" })).toBeNull();
    });

    it("UI-63: exibe uma vez o tempo da primeira sessão e retira a faixa", async () => {
      const leituras: ReturnType<typeof leitura>[] = [];
      responder({ dispositivos: [travesseiro], leituras });
      await montar("/dashboard");
      await faixaApareceu();
      fireEvent.click(screen.getAllByRole("link", { name: "Configurações" })[0]);
      await screen.findByRole("heading", { name: "Configurações", level: 1 });
      leituras.push(leitura(30), leitura(0));
      fireEvent.click(screen.getAllByRole("link", { name: "Início" })[0]);
      expect(await screen.findByText(/Sua primeira sessão: 1 min/)).toBeTruthy();
      expect(screen.queryByRole("region", { name: "Próximo passo" })).toBeNull();
      fireEvent.click(screen.getAllByRole("link", { name: "Configurações" })[0]);
      await screen.findByRole("heading", { name: "Configurações", level: 1 });
      fireEvent.click(screen.getAllByRole("link", { name: "Início" })[0]);
      await screen.findByText("Intensidade do movimento");
      expect(screen.queryByText(/Sua primeira sessão/)).toBeNull();
    });

    it("UI-63: dispensa a faixa sem impedir a abertura pelas Configurações", async () => {
      responder({ dispositivos: [travesseiro], leituras: [] });
      await montar("/dashboard");
      await faixaApareceu();
      fireEvent.click(faixa().getByRole("button", { name: "Dispensar" }));
      expect(await screen.findByText(/verifique se ele está ligado/i)).toBeTruthy();
      expect(screen.queryByRole("region", { name: "Próximo passo" })).toBeNull();
      fireEvent.click(screen.getAllByRole("link", { name: "Configurações" })[0]);
      fireEvent.click(await screen.findByRole("link", { name: "Primeiros passos" }));
      expect(await screen.findByRole("heading", { name: "Primeiros passos" })).toBeTruthy();
    });
    it("UI-57: Histórico vazio oferece retorno ao Início na visão de todos os aparelhos", async () => {
      responder({ dispositivos: [travesseiro, celular], leituras: [] });
      await montar("/historico");
      expect(await screen.findByText("Ainda não há sessões.")).toBeTruthy();
      expect(screen.getByRole("link", { name: "Ir para o Início" }).getAttribute("href")).toBe("/dashboard");
      const filtro = await screen.findByRole<HTMLSelectElement>("combobox", { name: "Dispositivo exibido" });
      const todos = filtro.value;
      fireEvent.change(filtro, { target: { value: travesseiro.id } });
      expect(await screen.findByText("Nenhuma sessão deste aparelho no período selecionado.")).toBeTruthy();
      expect(screen.queryByRole("link", { name: "Ir para o Início" })).toBeNull();
      fireEvent.change(filtro, { target: { value: todos } });
      expect(await screen.findByRole("link", { name: "Ir para o Início" })).toBeTruthy();
    });
  });
  const detalhes = () =>
    [...document.querySelectorAll("details")].find((d) =>
      d.querySelector("summary")?.textContent?.includes("Detalhes técnicos"))!;
  /** Está na tela sem precisar abrir nada. */
  const aVista = (elemento: Element) => elemento.closest("details:not([open])") === null;

  async function abrir() {
    await montar("/dashboard");
    await screen.findByRole("heading", { name: "Seus registros" });
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
      screen.getByRole("heading", { name: "Seus registros" }),
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
    expect(detalhes().textContent).toContain("Dispositivo no resumo: Meu travesseiro");
    expect(screen.queryByText(/Gráfico combina/)).toBeNull();
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
    const resumo = screen.getByRole("region", { name: "Seus registros" });
    const textoOriginal = resumo.textContent;
    const grafico = screen.getByRole("figure", { name: "Movimento ao longo do tempo" });
    const dentro = within(grafico);
    const opcao = (name: string) => dentro.getByRole("button", { name });

    expect(opcao("Sessão toda").getAttribute("aria-pressed")).toBe("true");
    expect(dentro.getByRole("img", { name: /6 pontos, 2 com movimento/ })).toBeTruthy();
    fireEvent.click(opcao("1ª metade"));
    expect(opcao("1ª metade").getAttribute("aria-pressed")).toBe("true");
    expect(dentro.getByRole("img", { name: /4 pontos, 0 com movimento/ })).toBeTruthy();
    expect(grafico.querySelectorAll("[data-lacuna]")).toHaveLength(1);
    fireEvent.click(opcao("2ª metade"));
    expect(opcao("2ª metade").getAttribute("aria-pressed")).toBe("true");
    expect(dentro.getByRole("img", { name: /3 pontos, 2 com movimento/ })).toBeTruthy();
    expect(grafico.querySelectorAll("[data-lacuna]")).toHaveLength(1);
    fireEvent.click(opcao("Sessão toda"));
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

  it.each([
    ["com leituras", "/dashboard", "/dispositivos", true],
    ["sem leituras", "/dashboard?demo=0", "/dispositivos", false],
    ["em demonstração", "/dashboard?demo=1", "/dispositivos?demo=1", true],
  ] as const)("Gerenciar dispositivos no cartão %s aponta para o destino do workspace", async (_, rota, destino, comLeituras) => {
    responder({ dispositivos: [travesseiro], leituras: comLeituras ? [0, 30, 60].map((s) => leitura(s)) : [] });
    await montar(rota);
    if (comLeituras) {
      await screen.findByRole("heading", { name: "Seus registros" });
    } else {
      fireEvent.click(await screen.findByRole("button", { name: "Dispensar" }));
      await screen.findByText("Nenhum registro ainda");
    }
    expect(cartaoDoAparelho().getByRole("link", { name: "Gerenciar dispositivos" }).getAttribute("href")).toBe(destino);
  });

  const seletorDeAparelho = () => screen.getByRole<HTMLSelectElement>("combobox", { name: "Dispositivo exibido" });
  const serieDeMovimento = () => within(screen.getByRole("figure", { name: "Movimento ao longo do tempo" }));

  describe("Calendário de registros (UI-45)", () => {
    beforeEach(() => {
      vi.useFakeTimers({ toFake: ["Date"] });
      vi.setSystemTime(new Date(2026, 10, 25, 12));
      const epoca = (dia: number, horas: number, minutos: number, segundos: number, extra = {}) =>
        leitura(0, { created_at: new Date(2026, 10, dia, horas, minutos, segundos).toISOString(), ...extra });
      responder({ dispositivos: [travesseiro, celular], leituras: [
        epoca(25, 3, 1, 0, { bancada: true }),
        epoca(24, 3, 1, 0, { device_id: "c" }),
        epoca(24, 0, 0, 30),
        epoca(24, 0, 0, 0),
        epoca(23, 23, 59, 30),
      ] });
    });

    afterEach(() => vi.useRealTimers());

    const calendario = () => within(screen.getByRole("region", { name: "Calendário de registros" }));

    it("fica entre o seletor e Seus registros, com a semana recolhida", async () => {
      await abrir();
      const regiao = screen.getByRole("region", { name: "Calendário de registros" });
      const registros = screen.getByRole("heading", { name: "Seus registros" });
      expect(seletorDeAparelho().compareDocumentPosition(regiao) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
      expect(regiao.compareDocumentPosition(registros) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
      expect(calendario().getByRole("button", { name: "Expandir", expanded: false })).toBeTruthy();
      const semana = within(calendario().getByRole("group", { name: "Semana atual" }));
      expect(semana.getAllByRole("button")).toHaveLength(7);
      await semana.findByRole("button", { name: /^segunda-feira, 23 de novembro, com registro/ });
      expect(semana.getByRole("button", { name: /^quarta-feira, 25 de novembro$/ })).toBeTruthy();
    });

    it("detalha a duração no dia em que a sessão anterior à meia-noite começou", async () => {
      await abrir();
      fireEvent.click(calendario().getByRole("button", { name: "Expandir" }));
      fireEvent.click(await calendario().findByRole("button", { name: /^segunda-feira, 23 de novembro, com registro/ }));
      expect(calendario().getByText("Tempo registrado · 1m 30s")).toBeTruthy();
      expect(calendario().getByRole("button", { name: "Recolher", expanded: true })).toBeTruthy();
      fireEvent.click(calendario().getByRole("button", { name: "Sequências" }));
      expect(calendario().getByText("Dias com registro em sequência:", { exact: false }).textContent).toMatch(/23.*24/);
    });

    it("consulta outro mês e o histórico do dispositivo selecionado", async () => {
      await abrir();
      fireEvent.click(calendario().getByRole("button", { name: "Expandir" }));
      fireEvent.click(calendario().getByRole("button", { name: "Mês" }));
      fireEvent.click(calendario().getByRole("button", { name: "Período anterior" }));
      expect(calendario().getByRole("heading", { name: "outubro de 2026" })).toBeTruthy();
      fireEvent.click(calendario().getByRole("button", { name: "Hoje" }));
      expect(calendario().getByRole("heading", { name: "novembro de 2026" })).toBeTruthy();
      fireEvent.change(seletorDeAparelho(), { target: { value: "c" } });
      await calendario().findByRole("button", { name: /^terça-feira, 24 de novembro, com registro/ });
      expect(calendario().getByRole("button", { name: /^segunda-feira, 23 de novembro$/ })).toBeTruthy();
      const consultas = vi.mocked(fetch).mock.calls
        .map(([caminho]) => new URL(String(caminho), "http://localhost"))
        .filter((url) => url.pathname === "/api/sleep-history" && url.searchParams.has("desde"));
      expect(consultas.some((url) =>
        url.searchParams.get("desde") === new Date(2026, 8, 27).toISOString()
        && url.searchParams.get("ate") === new Date(2026, 10, 2, 23, 59, 59, 999).toISOString(),
      )).toBe(true);
      expect(consultas.some((url) => url.searchParams.get("device") === "c")).toBe(true);
    });

    it("mantém como atual a sequência cujo último registro foi ontem", async () => {
      await abrir();
      expect(await calendario().findByText("2 dias consecutivos")).toBeTruthy();
      fireEvent.click(calendario().getByRole("button", { name: "Expandir" }));
      const resumo = within(calendario().getByRole("complementary", { name: "Resumo das sequências" }));
      expect(resumo.getByText("Sequência atual")).toBeTruthy();
      expect(resumo.getByText("2 dias consecutivos")).toBeTruthy();
    });

    it("mostra Histórico parcial quando ainda há registros após o limite de páginas", async () => {
      const { LIMITE_DO_PAINEL, MAX_PAGINAS_DO_HISTORICO } = await import("./lib/api");
      const responderPainel = vi.mocked(fetch).getMockImplementation()!;
      vi.mocked(fetch).mockImplementation((entrada, opcoes) => {
        const url = new URL(String(entrada), "http://localhost");
        if (url.pathname !== "/api/sleep-history" || !url.searchParams.has("desde")) {
          return responderPainel(entrada, opcoes);
        }
        const posicao = Number(url.searchParams.get("cursor_id") ?? 0);
        const total = LIMITE_DO_PAINEL * MAX_PAGINAS_DO_HISTORICO + 1;
        const quantidade = Math.min(Number(url.searchParams.get("limite")), total - posicao);
        const pagina = Array.from({ length: quantidade }, (_, i) => {
          const id = posicao + i + 1;
          return leitura(id * 30, { id: String(id) });
        });
        return Promise.resolve(respostaJson(pagina));
      });

      await abrir();
      expect(await calendario().findByText("Histórico parcial")).toBeTruthy();
      fireEvent.click(calendario().getByRole("button", { name: "Expandir" }));
      expect(calendario().getByText(/^Histórico parcial\./)).toBeTruthy();
    });

    it.each([
      ["Semana", /23 de nov.*29 de nov/, /16 de nov.*22 de nov/],
      ["Mês", /novembro de 2026/, /outubro de 2026/],
    ])("navega pelas setas em %s e bloqueia o próximo período ao voltar ao atual", async (visao, atual, anterior) => {
      await abrir();
      fireEvent.click(calendario().getByRole("button", { name: "Expandir" }));
      fireEvent.click(calendario().getByRole("button", { name: visao }));
      const proximo = () => calendario().getByRole<HTMLButtonElement>("button", { name: "Próximo período" });
      expect(calendario().getByRole("heading", { name: atual })).toBeTruthy();
      expect(proximo().disabled).toBe(true);
      fireEvent.click(calendario().getByRole("button", { name: "Período anterior" }));
      expect(calendario().getByRole("heading", { name: anterior })).toBeTruthy();
      expect(proximo().disabled).toBe(false);
      fireEvent.click(proximo());
      expect(calendario().getByRole("heading", { name: atual })).toBeTruthy();
      expect(proximo().disabled).toBe(true);
    });

    it("mostra pelo menos N dias quando a sequência vem do mês anterior e toca a borda", async () => {
      vi.setSystemTime(new Date(2026, 10, 3, 12));
      // Novembro começa no domingo. A grade consulta a partir de 26/10 e
      // 25/10 é a margem. A sequência real já começou em 24/10.
      const leituras = Array.from({ length: 10 }, (_, i) =>
        [0, 30, 60].map((segundos) =>
          leitura(0, { created_at: new Date(2026, 9, 24 + i, 3, 1, segundos).toISOString() }),
        )).flat();
      responder({ dispositivos: [travesseiro], leituras });

      await abrir();
      expect(await calendario().findByText("Pelo menos 8 dias consecutivos")).toBeTruthy();
      fireEvent.click(calendario().getByRole("button", { name: "Expandir" }));
      const resumo = within(calendario().getByRole("complementary", { name: "Resumo das sequências" }));
      expect(resumo.getByText("Pelo menos 8 dias consecutivos")).toBeTruthy();
      expect(resumo.getByText("Melhor sequência no período · Pelo menos 8 dias consecutivos")).toBeTruthy();
    });

    it("mostra pelo menos 1 dia, sem 'consecutivo', quando o único registro está na borda", async () => {
      vi.setSystemTime(new Date(2026, 10, 3, 12));
      // 26/10 é o primeiro dia da grade de novembro; 25/10, a margem, fica vazio.
      const leituras = [0, 30, 60].map((segundos) =>
        leitura(0, { created_at: new Date(2026, 9, 26, 3, 1, segundos).toISOString() }));
      responder({ dispositivos: [travesseiro], leituras });

      await abrir();
      fireEvent.click(await calendario().findByRole("button", { name: "Expandir" }));
      const resumo = within(calendario().getByRole("complementary", { name: "Resumo das sequências" }));
      expect(await resumo.findByText("Melhor sequência no período · Pelo menos 1 dia")).toBeTruthy();
      expect(calendario().queryByText(/Pelo menos 1 dia consecutivo/)).toBeNull();
    });
  });

  describe("Recorte do Início pelo dia (UI-46)", () => {
    const consultaDoDia = (dia: number) => new Date(2026, 10, dia - 1).toISOString();
    const calendario = () => within(screen.getByRole("region", { name: "Calendário de registros" }));
    const escolher = (nome: RegExp) => fireEvent.click(calendario().getByRole("button", { name: nome }));
    const titulo = "Sessões de terça-feira, 24 de novembro";
    const semanaPassada = /^terça-feira, 17 de novembro/;

    beforeEach(() => {
      vi.useFakeTimers({ toFake: ["Date"] });
      vi.setSystemTime(new Date(2026, 10, 25, 12));
      const sessao = (dia: number, hora: number, pontos: number, extra = {}) =>
        Array.from({ length: pontos }, (_, i) => leitura(0, {
          created_at: new Date(2026, 10, dia, hora, 0, (i + 1) * 30).toISOString(), ...extra,
        }));
      const ultimas = sessao(25, 5, 4);
      const historico = [
        ...ultimas, ...sessao(24, 7, 3), ...sessao(24, 2, 2),
        ...sessao(24, 6, 2, { device_id: "c" }), ...sessao(17, 4, 3),
      ];
      const anterior = vi.mocked(fetch).getMockImplementation()!;
      vi.mocked(fetch).mockImplementation((entrada, opcoes) => {
        const url = new URL(String(entrada), "http://localhost");
        if (url.pathname === "/api/devices") return Promise.resolve(respostaJson([travesseiro, celular]));
        if (url.pathname !== "/api/sleep-history") return anterior(entrada, opcoes);
        const desde = url.searchParams.get("desde");
        const ate = url.searchParams.get("ate");
        const dispositivo = url.searchParams.get("device");
        const filtradas = desde && ate ? historico.filter((l) => l.created_at >= desde && l.created_at <= ate) : ultimas;
        return Promise.resolve(respostaJson(filtradas.filter((l) => !dispositivo || dispositivo === l.device_id)));
      });
    });

    afterEach(() => vi.useRealTimers());

    it("abre na última sessão do dia e alterna apenas entre as sessões desse dia", async () => {
      await abrir();
      expect(serieDeMovimento().getByRole("img", { name: /4 pontos,/ })).toBeTruthy();
      escolher(/^terça-feira, 24 de novembro/);
      await screen.findByRole("img", { name: /3 pontos,/ });
      expect(screen.getByRole("heading", { name: titulo })).toBeTruthy();
      expect(calendario().getByRole("button", { name: "Expandir", expanded: false })).toBeTruthy();
      expect(calendario().getByRole("button", { name: /^terça-feira, 24 de novembro/, pressed: true })).toBeTruthy();
      expect(screen.queryByRole("heading", { name: "Sessões anteriores" })).toBeNull();
      expect(screen.getByRole("link", { name: "Ver histórico" }).getAttribute("href")).toBe("/historico");
      fireEvent.click(screen.getByRole("button", { name: "Ver as 3 sessões" }));
      expect(screen.getByText("7 registros no período, 0 com movimento.")).toBeTruthy();
      const consultas = vi.mocked(fetch).mock.calls.map(([entrada]) => new URL(String(entrada), "http://localhost"));
      expect(consultas.some((url) => url.searchParams.get("desde") === consultaDoDia(24)
        && url.searchParams.get("ate") === new Date(2026, 10, 25, 23, 59, 59, 999).toISOString())).toBe(true);
    });

    it("mantém a semana e o dia selecionados ao recolher depois de navegar", async () => {
      await abrir();
      fireEvent.click(calendario().getByRole("button", { name: "Expandir" }));
      fireEvent.click(calendario().getByRole("button", { name: "Período anterior" }));
      escolher(semanaPassada);
      await screen.findByRole("img", { name: /3 pontos,/ });
      fireEvent.click(calendario().getByRole("button", { name: "Recolher" }));
      const semana = within(calendario().getByRole("group", { name: "Semana selecionada" }));
      expect(semana.getByRole("button", { name: semanaPassada, pressed: true })).toBeTruthy();
      expect(semana.queryByRole("button", { name: /^quarta-feira, 25 de novembro/ })).toBeNull();
    });

    it("mostra um dia vazio e volta à última sessão ao clicar de novo", async () => {
      await abrir();
      const diaVazio = /^segunda-feira, 23 de novembro/;
      escolher(diaVazio);
      await screen.findByText("Sem registros neste dia");
      expect(screen.queryByRole("figure", { name: "Movimento ao longo do tempo" })).toBeNull();
      escolher(diaVazio);
      await screen.findByRole("heading", { name: "Seus registros" });
      expect(serieDeMovimento().getByRole("img", { name: /4 pontos,/ })).toBeTruthy();
    });

    it("limpa a seleção no botão Hoje e volta à última sessão", async () => {
      await abrir();
      fireEvent.click(calendario().getByRole("button", { name: "Expandir" }));
      escolher(/^terça-feira, 24 de novembro/);
      await screen.findByRole("img", { name: /3 pontos,/ });
      fireEvent.click(calendario().getByRole("button", { name: "Hoje" }));
      await screen.findByRole("heading", { name: "Seus registros" });
      expect(serieDeMovimento().getByRole("img", { name: /4 pontos,/ })).toBeTruthy();
      expect(calendario().queryByRole("button", { pressed: true, name: /^terça-feira, 24 de novembro/ })).toBeNull();
    });

    it("mantém a data e volta ao período completo do gráfico ao trocar de aparelho", async () => {
      await abrir();
      escolher(/^terça-feira, 24 de novembro/);
      await screen.findByRole("img", { name: /3 pontos,/ });
      fireEvent.click(screen.getByRole("button", { name: "1ª metade" }));
      fireEvent.change(seletorDeAparelho(), { target: { value: "c" } });
      await screen.findByRole("img", { name: /2 pontos,/ });
      expect(screen.getByRole("heading", { name: titulo })).toBeTruthy();
      expect(screen.getByRole("button", { name: "Sessão toda", pressed: true })).toBeTruthy();
    });

    it("UI-47: acompanha a semana navegada e compartilha o dia marcado com o calendário", async () => {
      await abrir();
      const grafico = () => within(screen.getByRole("region", { name: "Tempo registrado por dia" }));
      const dia = /^terça-feira, 17 de novembro/;
      fireEvent.click(calendario().getByRole("button", { name: "Expandir" }));
      fireEvent.click(calendario().getByRole("button", { name: "Período anterior" }));
      fireEvent.click(await grafico().findByRole("button", { name: /^terça-feira, 17 de novembro, 0h 01m registrados$/ }));
      await screen.findByRole("img", { name: /3 pontos,/ });
      fireEvent.click(calendario().getByRole("button", { name: "Recolher" }));
      expect(calendario().getByRole("button", { name: dia, pressed: true }).querySelector("[data-marca-dia]")).toBeTruthy();
      expect(grafico().getByRole("button", { name: dia, pressed: true }).querySelector("[data-marca-dia]")).toBeTruthy();
      fireEvent.click(grafico().getByRole("button", { name: dia, pressed: true }));
      await screen.findByRole("heading", { name: "Seus registros" });
      expect(grafico().queryByRole("button", { name: dia })).toBeNull();
    });

    it("UI-47: reutiliza a consulta do calendário e acompanha o dispositivo", async () => {
      await abrir();
      const grafico = () => within(screen.getByRole("region", { name: "Tempo registrado por dia" }));
      await grafico().findByRole("button", { name: /^terça-feira, 24 de novembro, 0h 03m registrados$/ });
      const desde = new Date(2026, 9, 25).toISOString();
      const consultas = vi.mocked(fetch).mock.calls
        .map(([entrada]) => new URL(String(entrada), "http://localhost"))
        .filter((url) => url.pathname === "/api/sleep-history" && url.searchParams.get("desde") === desde);
      expect(consultas).toHaveLength(1);
      fireEvent.change(seletorDeAparelho(), { target: { value: "c" } });
      await grafico().findByRole("button", { name: /^terça-feira, 24 de novembro, 0h 01m registrados$/ });
    });

    it("UI-48: em tela larga o gráfico fica na coluna da direita, inclusive num dia sem registro", async () => {
      simularTelaLarga();
      await abrir();
      const regiao = () => screen.getByRole("region", { name: "Tempo registrado por dia" });
      const naColuna = () => regiao().closest("[data-vaga-do-grafico]") !== null && regiao().closest("header") === null;
      // Com sessão, na mesma linha dos cartões do resumo, para começar e terminar alinhado com eles.
      const aoLadoDosCartoes = () => regiao().closest("[data-resumo-da-sessao]") !== null;
      await waitFor(() => expect(naColuna()).toBe(true));
      expect(aoLadoDosCartoes()).toBe(true);
      escolher(/^segunda-feira, 23 de novembro/);
      await screen.findByText("Sem registros neste dia");
      expect(naColuna()).toBe(true);
      escolher(/^terça-feira, 24 de novembro/);
      await screen.findByRole("heading", { name: titulo });
      expect(naColuna()).toBe(true);
      expect(aoLadoDosCartoes()).toBe(true);
    });

    it("UI-49: em tela larga o título e o filtro ficam ao lado do calendário, que fica na coluna do gráfico", async () => {
      simularTelaLarga();
      await abrir();
      const topo = document.querySelector("[data-topo-do-inicio]")!;
      const [esquerda, direita] = Array.from(topo.children);
      const titulo = screen.getByRole("heading", { level: 1, name: "Seus registros" });
      expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
      expect(esquerda.contains(titulo)).toBe(true);
      expect(esquerda.contains(screen.getByRole("combobox", { name: "Dispositivo exibido" }))).toBe(true);
      expect(direita.matches("[data-calendario-do-inicio]")).toBe(true);
      expect(direita.contains(screen.getByRole("region", { name: "Calendário de registros" }))).toBe(true);
      // As linhas do Início usam a mesma grade, e a coluna da direita não fica estreita demais
      // para o calendário e o gráfico (UI-49, ajuste: com 220 px de mínimo, chegava a 262 px).
      const grades = ["[data-topo-do-inicio]", "[data-linha-dos-cartoes]", "[data-linha-do-movimento]"]
        .map((seletor) => document.querySelector(seletor)?.className.match(/grid-cols-\[[^\]]+\]/)?.[0]);
      expect(new Set(grades)).toEqual(new Set(["grid-cols-[minmax(0,1.8fr)_minmax(320px,0.9fr)]"]));
      // O resumo aponta para o título do topo, e os cartões seguem nomeados por ele.
      expect(screen.getByRole("region", { name: "Seus registros" }).querySelector("ul[aria-label='Métricas da sessão']")).toBeTruthy();

      escolher(/^terça-feira, 24 de novembro/);
      const doDia = await screen.findByRole("heading", { level: 1, name: "Sessões de terça-feira, 24 de novembro" });
      expect(esquerda.contains(doDia)).toBe(true);

      fireEvent.click(calendario().getByRole("button", { name: "Expandir" }));
      expect(direita.classList.contains("col-span-full")).toBe(true);
      fireEvent.click(calendario().getByRole("button", { name: "Recolher" }));
      expect(direita.classList.contains("col-span-full")).toBe(false);
    });

    it("UI-48: em tela estreita o gráfico continua logo abaixo do calendário", async () => {
      await abrir();
      const regiao = await screen.findByRole("region", { name: "Tempo registrado por dia" });
      expect(regiao.closest("header")).not.toBeNull();
      expect(document.querySelector("[data-vaga-do-grafico]")).toBeNull();
    });

    it("UI-48: o dia escolhido leva o anel também no calendário expandido", async () => {
      await abrir();
      escolher(/^terça-feira, 24 de novembro/);
      await screen.findByRole("heading", { name: titulo });
      fireEvent.click(calendario().getByRole("button", { name: "Expandir" }));
      const dia = calendario().getByRole("button", { name: /^terça-feira, 24 de novembro/, pressed: true });
      expect(dia.querySelector("[data-marca-dia]")).toBeTruthy();
      expect(calendario().getAllByRole("button").filter((b) => b.querySelector("[data-marca-dia]"))).toHaveLength(1);
    });

    it("permite tentar novamente quando falha a consulta daquele dia", async () => {
      const anterior = vi.mocked(fetch).getMockImplementation()!;
      vi.mocked(fetch).mockImplementation((entrada, opcoes) => {
        const url = new URL(String(entrada), "http://localhost");
        if (url.searchParams.get("desde") === consultaDoDia(24)) return Promise.reject(new Error("sem conexão"));
        return anterior(entrada, opcoes);
      });
      await abrir();
      escolher(/^terça-feira, 24 de novembro/);
      const tentar = await screen.findByRole("button", { name: "Tentar novamente" });
      expect(screen.getByRole("heading", { name: titulo })).toBeTruthy();
      vi.mocked(fetch).mockImplementation(anterior);
      fireEvent.click(tentar);
      await screen.findByRole("img", { name: /3 pontos,/ });
    });

    describe("aberto pelo Histórico (UI-54)", () => {
      async function abrirNoDia(busca: string) {
        await montar(`/dashboard${busca}`);
      }

      it("o dia do endereço abre selecionado, na semana dele", async () => {
        await abrirNoDia("?dia=2026-11-24");
        expect(await screen.findByRole("heading", { name: titulo })).toBeTruthy();
        await screen.findByRole("img", { name: /3 pontos,/ });
        expect(await calendario().findByRole("button", { name: /^terça-feira, 24 de novembro/, pressed: true })).toBeTruthy();
      });

      it("com o aparelho, abre só as sessões dele naquele dia", async () => {
        await abrirNoDia("?dia=2026-11-24&aparelho=c");
        await screen.findByRole("img", { name: /2 pontos,/ });
        expect((seletorDeAparelho() as HTMLSelectElement).value).toBe("c");
        expect(screen.getByRole("heading", { name: titulo })).toBeTruthy();
      });

      it("escolher outro dia no Início tira o dia do endereço", async () => {
        await abrirNoDia("?dia=2026-11-24");
        await screen.findByRole("img", { name: /3 pontos,/ });
        fireEvent.click(await calendario().findByRole("button", { name: /^terça-feira, 24 de novembro/, pressed: true }));
        await screen.findByRole("heading", { name: "Seus registros" });
        expect(window.location.search).toBe("");
      });

      it("um dia que não existe é ignorado: o Início abre como sempre", async () => {
        await abrirNoDia("?dia=2026-02-31&aparelho=c");
        expect(await screen.findByRole("heading", { name: "Seus registros" })).toBeTruthy();
        expect((seletorDeAparelho() as HTMLSelectElement).value).not.toBe("c");
      });
    });
  });

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
    await screen.findByText("Dispositivo no resumo: Meu celular.");
    expect(seletorDeAparelho().value).toBe("c");
    expect(cartaoDoAparelho().getByRole("button", { name: "Meu celular", pressed: true })).toBeTruthy();
    expect(cartaoDoAparelho().getByRole("term").textContent).toBe("Último envio");
    expect(serieDeMovimento().getByRole("img", { name: /2 pontos,/ })).toBeTruthy();
  });

  it("Todos os dispositivos no cartão restaura o resumo e o gráfico gerais", async () => {
    responderComDoisAparelhos();
    await abrir();
    fireEvent.change(seletorDeAparelho(), { target: { value: "c" } });
    await screen.findByText("Dispositivo no resumo: Meu celular.");
    expect(cartaoDoAparelho().getByRole("button", { name: "Meu celular", pressed: true })).toBeTruthy();
    fireEvent.click(cartaoDoAparelho().getByRole("button", { name: "Todos os dispositivos", pressed: false }));
    await screen.findByText("Gráfico combina Travesseiro e Celular");
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

  it("explica a mistura sob demanda e acompanha o recorte do gráfico", async () => {
    responderComDoisAparelhos();
    await abrir();
    const aviso = screen.getByText("Gráfico combina Travesseiro e Celular");
    const ajuda = aviso.closest("details")!;
    expect(ajuda.open).toBe(false);
    expect(ajuda.querySelector("summary")?.textContent).toContain("Entenda");
    expect(ajuda.textContent).toContain("captam o mesmo movimento de formas diferentes");

    // UI-49: o aviso acompanha o filtro, no topo, e não fica solto entre o topo e os cartões.
    expect(aviso.closest("header")?.contains(seletorDeAparelho())).toBe(true);

    selecionarSegundaMetade();
    expect(screen.queryByText(/Gráfico combina/)).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Sessão toda" }));
    expect(screen.getByText("Gráfico combina Travesseiro e Celular")).toBeTruthy();
    fireEvent.change(seletorDeAparelho(), { target: { value: "c" } });
    await screen.findByText("Dispositivo no resumo: Meu celular.");
    expect(screen.queryByText(/Gráfico combina/)).toBeNull();
  });

  it("UI-49: em tela larga o aviso de mistura fica ao lado do seletor, na coluna do título", async () => {
    simularTelaLarga();
    responderComDoisAparelhos();
    await abrir();
    const coluna = document.querySelector("[data-topo-do-inicio]")!.firstElementChild!;
    expect(coluna.contains(screen.getByText("Gráfico combina Travesseiro e Celular"))).toBe(true);
    expect(coluna.contains(seletorDeAparelho())).toBe(true);
  });

  it("indica a sessão exibida e deixa a contagem descartada nos detalhes", async () => {
    responder({ dispositivos: [travesseiro], leituras: duasSessoes() });
    await abrir();
    const resumo = within(screen.getByRole("region", { name: "Seus registros" }));
    const fora = screen.getByText("3 registros ficaram fora do recorte.");
    expect(resumo.getByText("Última sessão")).toBeTruthy();
    expect(fora.closest("details")).toBe(detalhes());
    expect(aVista(fora)).toBe(false);

    fireEvent.click(resumo.getByRole("button", { name: "Ver as 2 sessões" }));
    expect(resumo.getByText("2 sessões")).toBeTruthy();
    expect(screen.queryByText(/registros ficaram fora do recorte/)).toBeNull();
    fireEvent.click(resumo.getByRole("button", { name: "Ver só a última" }));
    expect(resumo.getByText("Última sessão")).toBeTruthy();
  });

  it("volta para Sessão toda ao trocar de aparelho", async () => {
    responder({
      dispositivos: [travesseiro, celular],
      leituras: [0, 30, 60, 7200, 7230, 7260].map((s) => leitura(s, { device_id: s < 100 ? "p" : "c" })),
    });
    await abrir();
    selecionarSegundaMetade();
    fireEvent.change(screen.getByRole("combobox", { name: "Dispositivo exibido" }), { target: { value: "c" } });
    await screen.findByText("Dispositivo no resumo: Meu celular.");
    expect(screen.getByRole("button", { name: "Sessão toda", pressed: true })).toBeTruthy();
  });

  it("volta para Sessão toda ao alternar entre todas e a última sessão", async () => {
    responder({ dispositivos: [travesseiro], leituras: duasSessoes() });
    await abrir();
    selecionarSegundaMetade();
    fireEvent.click(screen.getByRole("button", { name: /ver as \d+ sessões/i }));
    fireEvent.click(screen.getByRole("button", { name: "Ver só a última" }));
    expect(screen.getByRole("button", { name: "Sessão toda", pressed: true })).toBeTruthy();
  });

  it("esconde o seletor de período quando mostra todas as sessões", async () => {
    responder({ dispositivos: [travesseiro], leituras: duasSessoes() });
    await abrir();
    expect(screen.getByRole("group", { name: "Período do gráfico" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /ver as \d+ sessões/i }));
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
      /duração:/i,
      /foi estimada pelo intervalo entre eles/i,
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
    fireEvent.click(screen.getByRole("button", { name: /ver as \d+ sessões/i }));
    expect(detalhes().textContent).not.toContain("do período.");
  });

  it("o limite de registros e o estado do envio ficam à vista", async () => {
    responder({ dispositivos: [travesseiro], leituras: Array.from({ length: 2000 }, (_, i) => leitura(i * 30)) });
    await abrir();
    expect(aVista(screen.getByText(/^Período incompleto/))).toBe(true);
    expect(aVista(screen.getByText("Nunca enviou"))).toBe(true);
  });
});
