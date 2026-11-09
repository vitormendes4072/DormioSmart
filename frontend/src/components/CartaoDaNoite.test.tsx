// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CartaoDaNoite } from "./CartaoDaNoite";
import type { EstadoDaNoite, PluginNoite } from "../lib/noiteNativa";

const INICIO = 1_794_096_000_000;

function estado(parcial: Partial<EstadoDaNoite> = {}): EstadoDaNoite {
  return {
    ativa: false,
    rodando: false,
    inicioUtcMs: 0,
    epocasGravadas: 0,
    recusadas: 0,
    recusadasPorTaxa: 0,
    semFeatures: 0,
    amostras: 0,
    taxaHz: 0,
    retomadas: 0,
    ultimaEpocaUtcMs: 0,
    isentoDeBateria: true,
    ...parcial,
  };
}

function plugin(inicial: EstadoDaNoite): PluginNoite & { atual: EstadoDaNoite } {
  const p = {
    atual: inicial,
    iniciar: vi.fn(async () => {
      p.atual = { ...p.atual, ativa: true, rodando: true, inicioUtcMs: INICIO };
      return { notificacoes: true };
    }),
    encerrar: vi.fn(async () => {
      p.atual = { ...p.atual, ativa: false, rodando: false };
    }),
    estado: vi.fn(async () => p.atual),
    pedirIsencaoDeBateria: vi.fn(async () => ({ isentoDeBateria: false })),
  };
  return p;
}

afterEach(() => cleanup());

describe("CartaoDaNoite (APP-02)", () => {
  it("inicia e encerra o servico pelo plugin", async () => {
    const p = plugin(estado());
    render(<CartaoDaNoite plugin={p} agora={() => INICIO} />);
    const iniciar = await screen.findByRole("button", { name: /iniciar a noite/i });
    await waitFor(() => expect((iniciar as HTMLButtonElement).disabled).toBe(false));
    await act(async () => fireEvent.click(iniciar));
    expect(p.iniciar).toHaveBeenCalledTimes(1);
    const encerrar = await screen.findByRole("button", { name: /encerrar a noite/i });
    await act(async () => fireEvent.click(encerrar));
    expect(p.encerrar).toHaveBeenCalledTimes(1);
    expect(await screen.findByRole("button", { name: /iniciar a noite/i })).toBeTruthy();
  });

  it("mostra a cobertura, a taxa e as retomadas da noite em curso", async () => {
    // 10 epocas que ja deviam ter fechado, 9 gravadas.
    const agora = INICIO + 3000 + 4200 + 10 * 30_000;
    const p = plugin(
      estado({ ativa: true, rodando: true, inicioUtcMs: INICIO, epocasGravadas: 9, taxaHz: 49.98, retomadas: 1, temperaturaC: 31.8 }),
    );
    render(<CartaoDaNoite plugin={p} agora={() => agora} />);
    expect(await screen.findByText("90 %")).toBeTruthy();
    expect(screen.getByText("50.0 Hz")).toBeTruthy();
    expect(screen.getByText("31.8 °C")).toBeTruthy();
  });

  it("taxa recusada sem nenhuma epoca vira alerta, e nao uma noite vazia silenciosa", async () => {
    const p = plugin(estado({ ativa: true, rodando: true, inicioUtcMs: INICIO, recusadasPorTaxa: 4 }));
    render(<CartaoDaNoite plugin={p} agora={() => INICIO + 200_000} />);
    expect((await screen.findByRole("alert")).textContent).toMatch(/40 a 60 Hz/);
  });

  it("sem a isencao de bateria, oferece o pedido", async () => {
    const p = plugin(estado({ isentoDeBateria: false }));
    render(<CartaoDaNoite plugin={p} agora={() => INICIO} />);
    const pedir = await screen.findByRole("button", { name: /economia de bateria/i });
    await act(async () => fireEvent.click(pedir));
    expect(p.pedirIsencaoDeBateria).toHaveBeenCalledTimes(1);
  });

  it("ativa sem o servico rodando e noite interrompida: avisa e oferece retomar", async () => {
    const p = plugin(estado({ ativa: true, rodando: false, inicioUtcMs: INICIO, epocasGravadas: 40 }));
    render(<CartaoDaNoite plugin={p} agora={() => INICIO + 3_600_000} />);
    expect((await screen.findByRole("alert")).textContent).toMatch(/interrompido/);
    const iniciar = screen.getByRole("button", { name: /iniciar a noite/i });
    await act(async () => fireEvent.click(iniciar));
    expect(p.iniciar).toHaveBeenCalledTimes(1);
  });
});
