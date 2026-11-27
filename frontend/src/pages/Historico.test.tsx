// @vitest-environment jsdom
/**
 * DATA-16: excluir uma sessão e marcá-la como bancada, pelo Histórico.
 *
 * A API é mockada: o que se confere aqui é a tela — as ações por sessão, a
 * confirmação antes de excluir, o trecho que vai ao servidor, a seção das
 * marcadas e o recarregamento depois. A posse e o alcance estão nos testes de
 * RLS (`web-app/tests/rls/test_rls_trecho.py`).
 */
import { webcrypto } from "node:crypto";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { apagarSessao, buscarJanelaDoHistorico, marcarSessao, ErroApi } from "../lib/api";
import type { LeituraSono } from "../types/sleep";
import { Historico } from "./Historico";
import { useDispositivos } from "../hooks/useDispositivos";
import type { Dispositivo } from "../lib/dispositivos";

vi.mock("../hooks/useDispositivos", () => ({ useDispositivos: vi.fn(() => []) }));

vi.mock("../lib/api", async (original) => ({
  ...await original<typeof import("../lib/api")>(),
  buscarJanelaDoHistorico: vi.fn(),
  apagarSessao: vi.fn(),
  marcarSessao: vi.fn(),
}));

const buscar = vi.mocked(buscarJanelaDoHistorico);
const apagar = vi.mocked(apagarSessao);
const marcar = vi.mocked(marcarSessao);

const MIN = 60_000;
const AGORA = Date.now();

/** `n` épocas de 30 s de um aparelho, começando `antesMin` minutos atrás. */
function sessao(device: string, antesMin: number, n: number, bancada = false): LeituraSono[] {
  return Array.from({ length: n }, (_, i) => {
    const instante = new Date(AGORA - antesMin * MIN + i * 30_000).toISOString();
    return {
      id: `00000000-0000-0000-0000-${String(Math.round(antesMin * 1000 + i)).padStart(12, "0")}`,
      created_at: instante,
      captured_at: instante,
      epoca_segundos: 30,
      movimento_total: 9.8,
      temp: null,
      status: "Repouso",
      device_id: device,
      bancada,
    } as LeituraSono;
  });
}

const NOITE = sessao("travesseiro", 600, 20);
const BANCADA = sessao("travesseiro", 120, 10, true);

/** UI-53: as ações ficam atrás do "…" de cada sessão; abre todos os do escopo. */
function abrirMenus(escopo: HTMLElement) {
  for (const menu of within(escopo).queryAllByRole("button", { name: /^Ações da sessão/, expanded: false })) {
    fireEvent.click(menu);
  }
}

function acao(escopo: HTMLElement, nome: string) {
  abrirMenus(escopo);
  return within(escopo).getByRole("button", { name: nome });
}

function mostrar() {
  render(<MemoryRouter><Historico /></MemoryRouter>);
}

beforeEach(() => {
  vi.stubGlobal("HTMLDialogElement", window.HTMLDialogElement);
  HTMLDialogElement.prototype.showModal = function () { this.setAttribute("open", ""); };
  HTMLDialogElement.prototype.close = function () { this.removeAttribute("open"); };
  vi.stubGlobal("crypto", webcrypto);
  vi.stubGlobal("matchMedia", vi.fn(() => ({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() })));
  buscar.mockResolvedValue({ leituras: [...NOITE, ...BANCADA], truncada: false });
  apagar.mockResolvedValue(20);
  marcar.mockResolvedValue(20);
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.unstubAllGlobals();
});

it("pede cada janela selecionada e mostra as sessões que ela devolve", async () => {
  const agora = vi.spyOn(Date, "now").mockReturnValue(AGORA);
  const ate = new Date(AGORA).toISOString();
  const diasEmMinutos = 24 * 60;
  const secao = () => screen.findByRole("region", { name: "Tabela do histórico" });

  buscar
    .mockResolvedValueOnce({ leituras: sessao("travesseiro", 4 * diasEmMinutos, 21), truncada: false })
    .mockResolvedValueOnce({ leituras: sessao("travesseiro", 600, 12), truncada: false })
    .mockResolvedValueOnce({ leituras: sessao("travesseiro", 20 * diasEmMinutos, 31), truncada: false });

  try {
    mostrar();
    const seletor = within(screen.getByRole("group", { name: "Período do histórico" }));
    const janelas = [
      [1, 7, "21", "Últimos 7 dias"],
      [2, 1, "12", "Últimas 24 horas"],
      [3, 30, "31", "Últimos 30 dias"],
    ] as const;
    for (const [indice, dias, registros, rotulo] of janelas) {
      const botao = seletor.getByRole("button", { name: rotulo });
      if (indice > 1) fireEvent.click(botao);
      expect(botao.getAttribute("aria-pressed")).toBe("true");
      expect(buscar).toHaveBeenNthCalledWith(indice, {
        desde: new Date(AGORA - dias * diasEmMinutos * MIN).toISOString(),
        ate,
      }, expect.any(AbortSignal), expect.any(Function));

      const tabela = within(await secao());
      expect(tabela.getAllByRole("row")).toHaveLength(2);
      expect(tabela.getByRole("cell", { name: registros })).toBeTruthy();
    }
  } finally {
    agora.mockRestore();
  }
});

describe("Histórico: excluir e marcar uma sessão (DATA-16)", () => {
  it("separa as sessões marcadas como bancada numa seção própria", async () => {
    mostrar();
    const principal = await screen.findByRole("region", { name: "Tabela do histórico" });
    const marcadas = screen.getByRole("region", { name: "Tabela das sessões marcadas como bancada" });
    expect(within(principal).getByText("20")).toBeTruthy();
    expect(within(marcadas).getByText("10")).toBeTruthy();
    expect(acao(principal, "Marcar como bancada")).toBeTruthy();
    expect(acao(marcadas, "Desmarcar")).toBeTruthy();
  });

  it("marcar manda o aparelho e o primeiro e o último instante da sessão, e recarrega", async () => {
    mostrar();
    const principal = await screen.findByRole("region", { name: "Tabela do histórico" });
    fireEvent.click(acao(principal, "Marcar como bancada"));
    await waitFor(() => expect(marcar).toHaveBeenCalledTimes(1));
    expect(marcar).toHaveBeenCalledWith(expect.objectContaining({
      device: "travesseiro",
      desde: NOITE[0].captured_at,
      ate: NOITE.at(-1)!.captured_at,
      epocas_esperadas: 20, bancada_atual: false, ids: NOITE.map((l) => l.id),
    }), true);
    expect(await screen.findByText(/Sessão marcada como bancada\/teste \(20 registros\)/)).toBeTruthy();
    expect(buscar).toHaveBeenCalledTimes(2);
  });

  it("desmarcar manda a marca falsa", async () => {
    mostrar();
    const marcadas = await screen.findByRole("region", { name: "Tabela das sessões marcadas como bancada" });
    fireEvent.click(acao(marcadas, "Desmarcar"));
    await waitFor(() => expect(marcar).toHaveBeenCalledWith(expect.objectContaining({
      device: "travesseiro",
      desde: BANCADA[0].captured_at,
      ate: BANCADA.at(-1)!.captured_at,
      epocas_esperadas: 10, bancada_atual: true, ids: BANCADA.map((l) => l.id),
    }), false));
  });

  it("excluir pede confirmação, e cancelar não apaga nada", async () => {
    mostrar();
    const principal = await screen.findByRole("region", { name: "Tabela do histórico" });
    fireEvent.click(acao(principal, "Excluir…"));
    const confirmacao = screen.getByRole("alertdialog", { name: "Confirmar exclusão da sessão" });
    expect(within(confirmacao).getByText(/não há como desfazer/)).toBeTruthy();
    expect(within(confirmacao).getByText("20 registros")).toBeTruthy();
    fireEvent.click(within(confirmacao).getByRole("button", { name: "Cancelar" }));
    expect(screen.queryByRole("alertdialog")).toBeNull();
    expect(apagar).not.toHaveBeenCalled();
  });

  it("mantém a confirmação aberta se Escape ocorrer durante a exclusão", async () => {
    let concluir!: (quantidade: number) => void;
    apagar.mockImplementationOnce(() => new Promise((resolve) => { concluir = resolve; }));
    mostrar();
    const principal = await screen.findByRole("region", { name: "Tabela do histórico" });
    fireEvent.click(acao(principal, "Excluir…"));
    const dialogo = screen.getByRole("alertdialog", { name: "Confirmar exclusão da sessão" });
    fireEvent.click(within(dialogo).getByRole("button", { name: "Excluir definitivamente" }));
    expect(apagar).toHaveBeenCalledTimes(1);
    const cancelar = new Event("cancel", { cancelable: true });
    fireEvent(dialogo, cancelar);
    expect(cancelar.defaultPrevented).toBe(true);
    expect(screen.getByRole("alertdialog")).toBe(dialogo);
    expect(dialogo.hasAttribute("open")).toBe(true);

    concluir(20);
    expect(await screen.findByText("Sessão excluída: 20 registros apagados.")).toBeTruthy();
    expect(screen.queryByRole("alertdialog")).toBeNull();
  });

  it("confirmar apaga a sessão, mostra quantas épocas saíram e recarrega", async () => {
    mostrar();
    const principal = await screen.findByRole("region", { name: "Tabela do histórico" });
    fireEvent.click(acao(principal, "Excluir…"));
    fireEvent.click(screen.getByRole("button", { name: "Excluir definitivamente" }));
    await waitFor(() => expect(apagar).toHaveBeenCalledWith(expect.objectContaining({
      device: "travesseiro",
      desde: NOITE[0].captured_at,
      ate: NOITE.at(-1)!.captured_at,
      epocas_esperadas: 20, bancada_atual: false, ids: NOITE.map((l) => l.id),
    })));
    expect(await screen.findByText("Sessão excluída: 20 registros apagados.")).toBeTruthy();
    expect(buscar).toHaveBeenCalledTimes(2);
  });

  it("uma falha do servidor aparece como alerta e não recarrega", async () => {
    apagar.mockRejectedValue(new Error("rede"));
    mostrar();
    const principal = await screen.findByRole("region", { name: "Tabela do histórico" });
    fireEvent.click(acao(principal, "Excluir…"));
    fireEvent.click(screen.getByRole("button", { name: "Excluir definitivamente" }));
    expect((await screen.findByRole("alert")).textContent).toContain("Não foi possível concluir");
    expect(buscar).toHaveBeenCalledTimes(1);
  });

  it("leitura sem aparelho não ganha ações", async () => {
    buscar.mockResolvedValue({
      leituras: sessao("x", 300, 5).map((l) => ({ ...l, device_id: null })),
      truncada: false,
    });
    mostrar();
    const principal = await screen.findByRole("region", { name: "Tabela do histórico" });
    expect(within(principal).queryByRole("button")).toBeNull();
  });
});

/** O que a função do banco alcança (migração 023): o aparelho e a janela,
 *  inclusiva nas duas pontas, sem olhar a marca. */
function alcance(todas: LeituraSono[], trecho: { device: string; desde: string; ate: string }) {
  const micro = (iso: string) =>
    Date.parse(iso) * 1000 + Number((/\.\d{3}(\d{1,3})/.exec(iso)?.[1] ?? "").padEnd(3, "0"));
  return todas.filter((l) => {
    const t = micro(l.captured_at || l.created_at);
    return l.device_id === trecho.device && t >= micro(trecho.desde) && t <= micro(trecho.ate);
  });
}

describe("excluir e marcar alcançam só a sessão mostrada (UI-38)", () => {
  /** `n` épocas a partir da época `de` de uma série de 30 s. */
  const pedaco = (de: number, n: number, bancada = false) =>
    sessao("travesseiro", 300 - de / 2, n, bancada);
  const comMicro = pedaco(0, 4).map((l) => ({
    ...l, captured_at: null, created_at: l.created_at.replace("Z", "456+00:00"),
  }));

  const CASOS: Array<[string, LeituraSono[], number[], number[]]> = [
    ["A: bancada curta dentro da sessão normal",
      [...pedaco(0, 20), ...pedaco(20, 10, true), ...pedaco(30, 20)], [20, 20], [10]],
    ["B: normal curto entre duas bancadas",
      [...pedaco(0, 20, true), ...pedaco(20, 10), ...pedaco(30, 20, true)], [10], [20, 20]],
    ["C: uma época normal entre duas bancadas",
      [...pedaco(0, 20, true), ...pedaco(20, 1), ...pedaco(21, 20, true)], [1], [20, 20]],
    ["D: instante com microssegundos", comMicro, [4], []],
  ];

  describe.each(CASOS)("%s", (_, todas, normais, marcadas) => {
    const linhas = [...normais.map((n) => [n, false] as const), ...marcadas.map((n) => [n, true] as const)];

    for (const acao of ["excluir", "marcar"] as const) {
      it(`${acao} leva exatamente as épocas de cada linha`, async () => {
        buscar.mockResolvedValue({ leituras: [...todas].reverse(), truncada: false });
        const nome = (bancada: boolean) =>
          acao === "excluir" ? "Excluir…" : bancada ? "Desmarcar" : "Marcar como bancada";

        for (const [indice, [esperadas, bancada]] of linhas.entries()) {
          cleanup();
          apagar.mockClear();
          marcar.mockClear();
          mostrar();
          await screen.findByRole("region", { name: "Tabela do histórico" });
          abrirMenus(document.body);
          const botoes = screen.getAllByRole("button", { name: acao === "excluir"
            ? nome(bancada)
            : /^(Marcar como bancada|Desmarcar)$/ });
          expect(botoes).toHaveLength(linhas.length);
          fireEvent.click(botoes[indice]);
          if (acao === "excluir") fireEvent.click(screen.getByRole("button", { name: "Excluir definitivamente" }));

          const chamada = acao === "excluir" ? apagar : marcar;
          await waitFor(() => expect(chamada).toHaveBeenCalledTimes(1));
          const atingidas = alcance(todas, chamada.mock.calls[0][0]);
          expect(atingidas).toHaveLength(esperadas);
          expect(atingidas.every((l) => (l.bancada === true) === bancada)).toBe(true);
        }
      });
    }
  });

  it("a confirmação diz o início e o fim", async () => {
    mostrar();
    const principal = await screen.findByRole("region", { name: "Tabela do histórico" });
    fireEvent.click(acao(principal, "Excluir…"));
    const hora = new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
    const texto = screen.getByRole("alertdialog").textContent;
    expect(texto).toContain(hora.format(Date.parse(NOITE[0].captured_at!) - 30_000));
    expect(texto).toContain(hora.format(Date.parse(NOITE.at(-1)!.captured_at!)));
  });

  it("sem como separar (mesmo instante, marcas diferentes), a linha fica sem ações", async () => {
    buscar.mockResolvedValue({ leituras: [...pedaco(0, 1), ...pedaco(0, 1, true)], truncada: false });
    mostrar();
    await screen.findByRole("region", { name: "Tabela do histórico" });
    expect(screen.queryByRole("button", { name: /^Ações da sessão/ })).toBeNull();
    expect(screen.queryByRole("button", { name: "Excluir…" })).toBeNull();
  });
});

describe("a linguagem do Histórico (UI-39)", () => {
  /** A situação da única linha, com as épocas nos instantes dados (em s). */
  async function situacao(segundos: number[]) {
    buscar.mockResolvedValue({
      leituras: segundos.map((s) => {
        const instante = new Date(AGORA - 120 * MIN + s * 1000).toISOString();
        return { created_at: instante, captured_at: instante, epoca_segundos: 30, movimento_total: 9.8,
          temp: null, status: "Repouso", device_id: "travesseiro" } as LeituraSono;
      }),
      truncada: false,
    });
    mostrar();
    return (await screen.findByRole("region", { name: "Tabela do histórico" })).textContent;
  }
  const serie = (de: number, n: number, passo = 30) => Array.from({ length: n }, (_, i) => de + i * passo);

  it("interrupção é 'Com pausas', com o registrado e o período", async () => {
    const texto = await situacao([...serie(0, 20), ...serie(570 + 150, 20)]);
    expect(texto).toContain("Com pausas");
    expect(texto).toContain("20m 0s de 22m 0s");
  });

  it("falha de segundo sem o aparelho parar é 'Incompleta', e não pausa", async () => {
    const texto = await situacao(serie(0, 20, 31));
    expect(texto).toContain("Incompleta");
    expect(texto).not.toContain("Com pausas");
  });

  it("sem falha nenhuma é 'Completa'", async () => {
    expect(await situacao(serie(0, 20))).toContain("Completa");
  });
});


it("DATA-17: divergência avisa e recarrega sem sucesso", async () => {
  marcar.mockRejectedValue(new ErroApi(409, "A sessão mudou desde que a tela carregou."));
  mostrar();
  const principal = await screen.findByRole("region", { name: "Tabela do histórico" });
  fireEvent.click(acao(principal, "Marcar como bancada"));
  expect((await screen.findByRole("alert")).textContent).toContain("A sessão mudou");
  expect(buscar).toHaveBeenCalledTimes(2);
  expect(screen.queryByText(/Sessão marcada como bancada/)).toBeNull();
});

it("UI-41: a lista de cartões traz situação, ações e a confirmação modal", async () => {
  vi.stubGlobal("matchMedia", vi.fn((consulta: string) => ({
    matches: consulta === "(max-width: 767px)", addEventListener: vi.fn(), removeEventListener: vi.fn(),
  })));
  mostrar();
  const lista = await screen.findByRole("list", { name: "Sessões do histórico" });
  expect(within(lista).getByText("Completa")).toBeTruthy();
  expect(acao(lista, "Marcar como bancada")).toBeTruthy();
  fireEvent.click(acao(lista, "Excluir…"));
  const dialogo = screen.getByRole("alertdialog", { name: "Confirmar exclusão da sessão" });
  expect(dialogo.tagName).toBe("DIALOG");
  expect(apagar).not.toHaveBeenCalled();
});

it("UI-41: um erro desconhecido do Histórico aparece com detalhes recolhidos", async () => {
  buscar.mockRejectedValueOnce(new ErroApi(500, "Não foi possível concluir o pedido.", "mensagem original"));
  mostrar();
  expect(await screen.findByText("Não foi possível concluir o pedido.")).toBeTruthy();
  const detalhes = screen.getByText("Detalhes técnicos").closest("details");
  expect(detalhes?.hasAttribute("open")).toBe(false);
  expect(detalhes?.textContent).toContain("mensagem original");
});

function simularCelular() {
  vi.stubGlobal("matchMedia", vi.fn((consulta: string) => ({
    matches: consulta === "(max-width: 767px)", addEventListener: vi.fn(), removeEventListener: vi.fn(),
  })));
}

it("mostra cartões com situação, duração registrada e total de registros no celular", async () => {
  simularCelular();
  const completa = sessao("completa", 600, 20);
  const comPausas = sessao("com-pausas", 1200, 40).map((leitura, indice) => {
    if (indice < 20) return leitura;
    const instante = new Date(Date.parse(leitura.created_at) + 2 * MIN).toISOString();
    return { ...leitura, captured_at: instante, created_at: instante };
  });
  const incompleta = sessao("incompleta", 1800, 20).map((leitura, indice) => {
    const instante = new Date(Date.parse(leitura.created_at) + indice * 1000).toISOString();
    return { ...leitura, captured_at: instante, created_at: instante };
  });
  buscar.mockResolvedValue({ leituras: [...completa, ...comPausas, ...incompleta], truncada: false });
  mostrar();

  const lista = await screen.findByRole("list", { name: "Sessões do histórico" });
  const cartoes = within(lista).getAllByRole("article");
  expect(cartoes).toHaveLength(3);
  // UI-53: todos os cartões iguais — o gráfico da sessão e três números embaixo.
  const metricas = (cartao: HTMLElement) =>
    within(within(cartao).getByRole("list", { name: "Métricas da sessão" })).getAllByRole("listitem").map((item) => item.textContent);
  expect(within(cartoes[0]).getByText("Completa")).toBeTruthy();
  expect(metricas(cartoes[0])).toEqual(["10m 0sregistrado de 10m 0s", "0%com movimento", "20registros"]);
  expect(within(cartoes[1]).getByText("Com pausas")).toBeTruthy();
  expect(metricas(cartoes[1])).toEqual(["20m 0sregistrado de 22m 0s", "0%com movimento", "40registros"]);
  expect(within(cartoes[2]).getByText("Incompleta")).toBeTruthy();
  expect(metricas(cartoes[2])).toEqual(["10m 0sregistrado de 10m 19s", "0%com movimento", "20registros"]);
  for (const cartao of cartoes) {
    expect(within(cartao).getByRole("img", { name: /^Intensidade do movimento na sessão/ })).toBeTruthy();
  }
  // A pausa de 2 min aparece no gráfico como trecho sem registro.
  expect(within(cartoes[1]).getByRole("img", { name: /com trechos sem registro/ })).toBeTruthy();
});

it("mostra as três janelas e destaca a selecionada nos botões do celular", async () => {
  simularCelular();
  mostrar();
  const seletor = within(screen.getByRole("group", { name: "Período do histórico" }));
  const seteDias = seletor.getByRole("button", { name: "Últimos 7 dias", pressed: true });
  const umDia = seletor.getByRole("button", { name: "Últimas 24 horas", pressed: false });
  expect(seletor.getByRole("button", { name: "Últimos 30 dias", pressed: false })).toBeTruthy();
  fireEvent.click(umDia);
  expect(seletor.getByRole("button", { name: "Últimas 24 horas", pressed: true })).toBe(umDia);
  expect(seletor.getByRole("button", { name: "Últimos 7 dias", pressed: false })).toBe(seteDias);
  expect(await screen.findByRole("list", { name: "Sessões do histórico" })).toBeTruthy();
});

describe("o topo do período (UI-52)", () => {
  it("resume só as sessões normais e a barra leva à linha da sessão", async () => {
    const scroll = vi.fn();
    Element.prototype.scrollIntoView = scroll;
    mostrar();
    const numeros = within(await screen.findByRole("list", { name: "Números do período" }));
    // A bancada (10 registros) fica de fora: uma sessão, 20 registros de 30 s.
    expect(numeros.getAllByRole("listitem")[0].textContent).toBe("1Sessão");
    expect(numeros.getAllByRole("listitem")[1].textContent).toBe("10m 0sTempo registrado");
    fireEvent.click(screen.getByRole("button", { name: /registrados de/ }));
    const linha = within(screen.getByRole("region", { name: "Tabela do histórico" })).getAllByRole("row")[1];
    expect(document.activeElement).toBe(linha);
    expect(scroll).toHaveBeenCalledTimes(1);
  });

  it("em 24 horas, com um aparelho, o gráfico é o de movimento", async () => {
    mostrar();
    await screen.findByRole("list", { name: "Números do período" });
    fireEvent.click(screen.getByRole("button", { name: "Últimas 24 horas" }));
    expect(await screen.findByRole("heading", { name: "Movimento nas últimas 24 horas" })).toBeTruthy();
  });

  it("em 24 horas, com dois aparelhos, ficam as barras por sessão", async () => {
    buscar.mockResolvedValue({ leituras: [...NOITE, ...sessao("celular", 300, 20)], truncada: false });
    mostrar();
    await screen.findByRole("list", { name: "Números do período" });
    fireEvent.click(screen.getByRole("button", { name: "Últimas 24 horas" }));
    expect(await screen.findByRole("heading", { name: "Tempo registrado por sessão" })).toBeTruthy();
  });
});

describe("a faixa e o movimento de cada sessão (UI-53)", () => {
  it("a tabela mostra a faixa da sessão e a parte do tempo com movimento", async () => {
    const comMovimento = NOITE.map((leitura, i) => (i % 4 === 0 ? { ...leitura, status: "Movimento" } : leitura));
    buscar.mockResolvedValue({ leituras: comMovimento, truncada: false });
    mostrar();
    const tabela = within(await screen.findByRole("region", { name: "Tabela do histórico" }));
    const [, linha] = tabela.getAllByRole("row");
    expect(within(linha).getAllByRole("cell").map((celula) => celula.textContent)[2]).toBe("25%");
    const faixa = within(linha).getByRole("img", { name: /registros com movimento/ });
    expect(faixa.getAttribute("aria-label")).toMatch(/: 10m 0s com registro, 5 registros com movimento\.$/);
    expect(faixa.querySelectorAll("[data-movimento]")).toHaveLength(5);
  });
});

describe("abrir a sessão no Início (UI-54)", () => {
  const diaDe = (leitura: LeituraSono) => {
    const d = new Date(Date.parse(leitura.captured_at!) - 30_000);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  };

  it("no computador, a data da linha leva ao Início no dia e no aparelho da sessão", async () => {
    mostrar();
    const tabela = within(await screen.findByRole("region", { name: "Tabela do histórico" }));
    const link = tabela.getByRole("link");
    expect(link.getAttribute("href")).toBe(`/dashboard?dia=${diaDe(NOITE[0])}&aparelho=travesseiro`);
  });

  it("no celular, cada cartão tem o link Abrir no Início", async () => {
    vi.stubGlobal("matchMedia", vi.fn((consulta: string) => ({
      matches: consulta === "(max-width: 767px)", addEventListener: vi.fn(), removeEventListener: vi.fn(),
    })));
    mostrar();
    const lista = await screen.findByRole("list", { name: "Sessões do histórico" });
    expect(within(lista).getByRole("link", { name: "Abrir no Início" }).getAttribute("href"))
      .toBe(`/dashboard?dia=${diaDe(NOITE[0])}&aparelho=travesseiro`);
  });
});


describe("o aparelho de cada sessão (UI-55)", () => {
  const aparelhos: Dispositivo[] = [
    { id: "travesseiro", nome: "Quarto", tipo: "travesseiro", created_at: "", last_seen_at: null, revoked_at: null },
    { id: "celular", nome: "Meu celular", tipo: "celular", created_at: "", last_seen_at: null, revoked_at: null },
  ];
  const seletor = () => screen.getByRole<HTMLSelectElement>("combobox");

  beforeEach(() => {
    window.localStorage.clear();
    vi.mocked(useDispositivos).mockReturnValue(aparelhos);
    buscar.mockResolvedValue({ leituras: [...NOITE, ...sessao("celular", 300, 12)], truncada: false });
  });

  afterEach(() => vi.mocked(useDispositivos).mockReturnValue([]));

  it("com dois aparelhos, cada linha diz de qual veio", async () => {
    mostrar();
    const tabela = within(await screen.findByRole("region", { name: "Tabela do histórico" }));
    const nomes = tabela.getAllByRole("row").slice(1)
      .map((linha) => linha.querySelector("[data-aparelho]")?.textContent);
    expect(nomes).toEqual(["Meu celular", "Travesseiro · Quarto"]);
  });

  it("escolher um aparelho mostra só as sessões dele e a escolha fica para a próxima visita", async () => {
    mostrar();
    await screen.findByRole("region", { name: "Tabela do histórico" });
    fireEvent.change(seletor(), { target: { value: "celular" } });
    const tabela = within(screen.getByRole("region", { name: "Tabela do histórico" }));
    expect(tabela.getAllByRole("row")).toHaveLength(2);
    expect(tabela.getByRole("cell", { name: "12" })).toBeTruthy();
    expect(within(screen.getByRole("list", { name: "Números do período" })).getAllByRole("listitem")[0].textContent).toBe("1Sessão");
    cleanup();
    mostrar();
    await screen.findByRole("region", { name: "Tabela do histórico" });
    expect(seletor().value).toBe("celular");
  });

  it("um aparelho guardado que saiu da conta vale como todos", async () => {
    window.localStorage.setItem("dormio-historico-aparelho", "apagado");
    mostrar();
    const tabela = within(await screen.findByRole("region", { name: "Tabela do histórico" }));
    expect(tabela.getAllByRole("row")).toHaveLength(3);
  });

  it("com um aparelho só, não há seletor nem nome", async () => {
    vi.mocked(useDispositivos).mockReturnValue([aparelhos[0]]);
    buscar.mockResolvedValue({ leituras: NOITE, truncada: false });
    mostrar();
    const tabela = await screen.findByRole("region", { name: "Tabela do histórico" });
    expect(screen.queryByRole("combobox")).toBeNull();
    expect(tabela.querySelector("[data-aparelho]")).toBeNull();
  });
});


describe("o mesmo período com dois aparelhos (UI-56)", () => {
  const aparelhos: Dispositivo[] = [
    { id: "celular", nome: "Meu celular", tipo: "celular", created_at: "", last_seen_at: null, revoked_at: null },
    { id: "travesseiro", nome: "Quarto", tipo: "travesseiro", created_at: "", last_seen_at: null, revoked_at: null },
  ];
  // O travesseiro: 20 registros (10 min) a partir de 600 min atrás. O celular: 24 registros
  // começando 4 min antes, sobrepostos ao travesseiro.
  const CELULAR = sessao("celular", 604, 24);

  beforeEach(() => {
    window.localStorage.clear();
    vi.mocked(useDispositivos).mockReturnValue(aparelhos);
    buscar.mockResolvedValue({ leituras: [...NOITE, ...CELULAR], truncada: false });
  });

  afterEach(() => vi.mocked(useDispositivos).mockReturnValue([]));

  it("no computador, uma data com 2 aparelhos e uma linha por aparelho, o travesseiro primeiro", async () => {
    mostrar();
    const tabela = within(await screen.findByRole("region", { name: "Tabela do histórico" }));
    const [, primeira, segunda] = tabela.getAllByRole("row");
    expect(within(primeira).getByRole("rowheader").getAttribute("rowspan")).toBe("2");
    expect(within(primeira).getByRole("rowheader").textContent).toContain("2 aparelhos");
    expect(primeira.querySelector("td [data-aparelho]")?.textContent).toBe("Travesseiro · Quarto");
    expect(segunda.querySelector("td [data-aparelho]")?.textContent).toBe("Meu celular");
    expect(within(segunda).getAllByRole("cell")[1].textContent).toBe("12m 0s de 12m 0s");
  });

  it("o topo conta uma sessão e o tempo em que pelo menos um registrou, sem somar", async () => {
    mostrar();
    const numeros = within(await screen.findByRole("list", { name: "Números do período" })).getAllByRole("listitem");
    expect(numeros[0].textContent).toBe("1Sessão1 registrada com mais de um aparelho");
    // O celular (12 min) e o travesseiro (10 min) se sobrepõem em 8 min: a união é 14 min, e não 22.
    expect(numeros[1].textContent).toBe("14m 0sTempo registrado");
  });

  it("no celular, um cartão com uma seção por aparelho e as ações de cada um", async () => {
    vi.stubGlobal("matchMedia", vi.fn((consulta: string) => ({
      matches: consulta === "(max-width: 767px)", addEventListener: vi.fn(), removeEventListener: vi.fn(),
    })));
    mostrar();
    const lista = await screen.findByRole("list", { name: "Sessões do histórico" });
    const [cartao] = within(lista).getAllByRole("article");
    expect(cartao.getAttribute("aria-label")).toMatch(/, 2 aparelhos$/);
    const secoes = within(cartao).getAllByRole("region");
    expect(secoes.map((secao) => secao.getAttribute("aria-label"))).toEqual(["Travesseiro · Quarto", "Meu celular"]);
    for (const secao of secoes) expect(within(secao).getByRole("button", { name: /^Ações da sessão/ })).toBeTruthy();
    expect(within(cartao).getByRole("link", { name: "Abrir no Início" }).getAttribute("href")).not.toContain("aparelho=");
  });

  it("com um aparelho escolhido no filtro, não há grupo", async () => {
    window.localStorage.setItem("dormio-historico-aparelho", "celular");
    mostrar();
    const tabela = within(await screen.findByRole("region", { name: "Tabela do histórico" }));
    expect(tabela.getAllByRole("row")).toHaveLength(2);
    expect(tabela.queryByText("2 aparelhos")).toBeNull();
  });
});
