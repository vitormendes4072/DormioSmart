// @vitest-environment jsdom
/**
 * DATA-16: excluir uma sessão e marcá-la como bancada, pelo Histórico.
 *
 * A API é mockada: o que se confere aqui é a tela — as ações por sessão, a
 * confirmação antes de excluir, o trecho que vai ao servidor, a seção das
 * marcadas e o recarregamento depois. A posse e o alcance estão nos testes de
 * RLS (`web-app/tests/rls/test_rls_trecho.py`).
 */
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { apagarSessao, buscarJanelaDoHistorico, marcarSessao } from "../lib/api";
import type { LeituraSono } from "../types/sleep";
import { Historico } from "./Historico";

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
      id: `${device}-${antesMin}-${i}`,
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

function mostrar() {
  render(<MemoryRouter><Historico /></MemoryRouter>);
}

beforeEach(() => {
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

describe("Histórico: excluir e marcar uma sessão (DATA-16)", () => {
  it("separa as sessões marcadas como bancada numa seção própria", async () => {
    mostrar();
    const principal = await screen.findByRole("region", { name: "Tabela do histórico" });
    const marcadas = screen.getByRole("region", { name: "Tabela das sessões marcadas como bancada" });
    expect(within(principal).getByText("20")).toBeTruthy();
    expect(within(marcadas).getByText("10")).toBeTruthy();
    expect(within(principal).getByRole("button", { name: "Marcar como bancada" })).toBeTruthy();
    expect(within(marcadas).getByRole("button", { name: "Desmarcar" })).toBeTruthy();
  });

  it("marcar manda o aparelho e o primeiro e o último instante da sessão, e recarrega", async () => {
    mostrar();
    const principal = await screen.findByRole("region", { name: "Tabela do histórico" });
    fireEvent.click(within(principal).getByRole("button", { name: "Marcar como bancada" }));
    await waitFor(() => expect(marcar).toHaveBeenCalledTimes(1));
    expect(marcar).toHaveBeenCalledWith({
      device: "travesseiro",
      desde: NOITE[0].captured_at,
      ate: NOITE.at(-1)!.captured_at,
    }, true);
    expect(await screen.findByText(/Sessão marcada como bancada\/teste \(20 épocas\)/)).toBeTruthy();
    expect(buscar).toHaveBeenCalledTimes(2);
  });

  it("desmarcar manda a marca falsa", async () => {
    mostrar();
    const marcadas = await screen.findByRole("region", { name: "Tabela das sessões marcadas como bancada" });
    fireEvent.click(within(marcadas).getByRole("button", { name: "Desmarcar" }));
    await waitFor(() => expect(marcar).toHaveBeenCalledWith({
      device: "travesseiro",
      desde: BANCADA[0].captured_at,
      ate: BANCADA.at(-1)!.captured_at,
    }, false));
  });

  it("excluir pede confirmação, e cancelar não apaga nada", async () => {
    mostrar();
    const principal = await screen.findByRole("region", { name: "Tabela do histórico" });
    fireEvent.click(within(principal).getByRole("button", { name: "Excluir…" }));
    const confirmacao = screen.getByRole("alertdialog", { name: "Confirmar exclusão da sessão" });
    expect(within(confirmacao).getByText(/não há como desfazer/)).toBeTruthy();
    expect(within(confirmacao).getByText("20 leituras")).toBeTruthy();
    fireEvent.click(within(confirmacao).getByRole("button", { name: "Cancelar" }));
    expect(screen.queryByRole("alertdialog")).toBeNull();
    expect(apagar).not.toHaveBeenCalled();
  });

  it("confirmar apaga a sessão, mostra quantas épocas saíram e recarrega", async () => {
    mostrar();
    const principal = await screen.findByRole("region", { name: "Tabela do histórico" });
    fireEvent.click(within(principal).getByRole("button", { name: "Excluir…" }));
    fireEvent.click(screen.getByRole("button", { name: "Excluir definitivamente" }));
    await waitFor(() => expect(apagar).toHaveBeenCalledWith({
      device: "travesseiro",
      desde: NOITE[0].captured_at,
      ate: NOITE.at(-1)!.captured_at,
    }));
    expect(await screen.findByText("Sessão excluída: 20 épocas apagadas.")).toBeTruthy();
    expect(buscar).toHaveBeenCalledTimes(2);
  });

  it("uma falha do servidor aparece como alerta e não recarrega", async () => {
    apagar.mockRejectedValue(new Error("rede"));
    mostrar();
    const principal = await screen.findByRole("region", { name: "Tabela do histórico" });
    fireEvent.click(within(principal).getByRole("button", { name: "Excluir…" }));
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
