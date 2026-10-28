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

import { act, fireEvent, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { aplicabilidadeDaIdade } from "./lib/aplicabilidade";

// ---------------------------------------------------------------------
// Dublês de fronteira
// ---------------------------------------------------------------------

const SESSAO = {
  access_token: "jwt-de-teste",
  user: { id: "11111111-1111-1111-1111-111111111111", email: "titular@exemplo.com" },
};

vi.mock("@supabase/supabase-js", () => ({
  createClient: () => ({
    auth: {
      getSession: async () => ({ data: { session: SESSAO }, error: null }),
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

  it("a rota /configuracoes existe e passa pelos guardas até o Layout", async () => {
    await montar("/configuracoes");

    // As cinco asserções acima dependem desta, e ela merece nome próprio: se a
    // rota saísse do `App.tsx`, o `*` levaria à Landing e os erros seriam
    // "não achei o botão", que mandam procurar o botão em vez da rota.
    expect(screen.getByRole("heading", { name: /configurações/i })).toBeTruthy();
  });
});

/**
 * Toda rota declarada no `App.tsx` renderiza alguma coisa.
 *
 * ── POR QUE A LISTA NÃO É ESCRITA AQUI ──────────────────────────────────
 *
 * A ocorrência 4 do §1 das lições é um alvo de `make` com dois dos quatro
 * sketches, porque a lista era manual — e os dois de fora não compilavam. Uma
 * lista de rotas escrita à mão neste arquivo teria o mesmo destino: a rota
 * nova entra no `App.tsx`, ninguém se lembra de acrescentá-la aqui, e a
 * verificação silenciosamente para de acompanhar o aplicativo.
 *
 * Então as rotas saem do próprio `App.tsx`, lido do disco. Rota nova é coberta
 * sozinha; se o padrão deixar de casar, a guarda de contagem reprova em vez de
 * aprovar um conjunto vazio.
 *
 * ── O QUE ESTA VARREDURA PROVA, E O QUE NÃO PROVA ───────────────────────
 *
 * Prova que cada rota monta sem estourar e põe nós na raiz. **Não** prova que
 * a tela certa apareceu, nem que o conteúdo dela está correto — para
 * `/configuracoes` isso está provado acima, uma asserção por coisa afirmada.
 * Para as demais é catraca: pega a tela que deixa de renderizar, não a tela
 * que renderiza errado. As afirmações condicionais do painel (o
 * `AvisoDeLacuna`, a `NotaDeInferencia`, a `NotaDeEscopo` — texto de honestidade
 * científica que o trabalho afirma mostrar e que nunca foi visto renderizado)
 * exigem séries de leitura construídas para satisfazer cada condição, que é
 * trabalho de fixture e não de montagem: é o item `UI-18`.
 *
 * E uma assimetria que precisa estar dita, porque ela é o limite da ideia de
 * derivar a lista da fonte: **esta varredura cobre rota nova, não rota
 * removida.** Apagar um `<Route>` do `App.tsx` encurta a lista, e uma lista
 * mais curta passa. Quem pega a remoção é a asserção nomeada da rota — e hoje
 * existe uma só, a de `/configuracoes` (medida por controle positivo). Para as
 * outras seis, a remoção passaria em silêncio: é a parte do `UI-18`.
 */
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
