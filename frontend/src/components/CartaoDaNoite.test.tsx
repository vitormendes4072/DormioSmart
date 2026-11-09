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

function plugin(
  inicial: EstadoDaNoite,
  gravadas = 0,
): PluginNoite & { atual: EstadoDaNoite; enviadas: number } {
  const p = {
    atual: inicial,
    enviadas: 0,
    noites: vi.fn(async () => ({
      noites: gravadas > 0 ? [{ arquivo: "noite-1.jsonl", epocas: gravadas, enviadas: p.enviadas }] : [],
    })),
    lerEpocas: vi.fn(async ({ de }: { arquivo: string; de: number }) => ({
      epocas: Array.from({ length: Math.max(0, Math.min(gravadas, de + 60) - de) }, (_, k) =>
        JSON.stringify({ epoca: de + k }),
      ),
    })),
    marcarEnviadas: vi.fn(async ({ ate }: { arquivo: string; ate: number }) => {
      p.enviadas = Math.min(gravadas, Math.max(p.enviadas, ate));
      return { enviadas: p.enviadas };
    }),
    iniciar: vi.fn(async () => {
      p.atual = { ...p.atual, ativa: true, rodando: true, inicioUtcMs: INICIO };
      return { notificacoes: true };
    }),
    encerrar: vi.fn(async () => {
      p.atual = { ...p.atual, ativa: false, rodando: false };
    }),
    estado: vi.fn(async () => p.atual),
    pedirIsencaoDeBateria: vi.fn(async () => ({ isentoDeBateria: false })),
    salvarNotas: vi.fn(async ({ notas }: { arquivo: string; notas: object }) => notas),
  };
  return p;
}

afterEach(() => cleanup());

describe("CartaoDaNoite (APP-02)", () => {
  it("inicia e encerra o servico pelo plugin", async () => {
    const p = plugin(estado());
    render(<CartaoDaNoite plugin={p} agora={() => INICIO} />);
    const iniciar = await screen.findByRole("button", { name: /iniciar a noite/i });
    fireEvent.click(screen.getByLabelText(/dentro da fronha/i));
    await waitFor(() => expect((iniciar as HTMLButtonElement).disabled).toBe(false));
    await act(async () => fireEvent.click(iniciar));
    expect(p.iniciar).toHaveBeenCalledTimes(1);
    expect(p.iniciar).toHaveBeenCalledWith({ posicao: "fronha" });
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

  it("ao abrir com epocas esperando e sem noite em curso, envia sozinho", async () => {
    const p = plugin(estado({ ativa: false, rodando: false }), 70);
    const enviar = vi.fn(async (l: object[]) => ({ aceitas: l.map((_, i) => i), rejeitadas: [], pendentes: [] }));
    render(<CartaoDaNoite plugin={p} agora={() => INICIO} enviar={enviar} />);
    expect((await screen.findByRole("status")).textContent).toMatch(/70 épocas enviadas/);
    expect(enviar).toHaveBeenCalledTimes(2);
    expect(p.enviadas).toBe(70);
  });

  it("durante a noite nao envia nada", async () => {
    const p = plugin(estado({ ativa: true, rodando: true, inicioUtcMs: INICIO }), 30);
    const enviar = vi.fn();
    render(<CartaoDaNoite plugin={p} agora={() => INICIO + 900_000} enviar={enviar} />);
    await screen.findByRole("button", { name: /encerrar a noite/i });
    expect(enviar).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: /enviar agora/i })).toBeNull();
  });

  it("ao encerrar, a noite vai para a conta", async () => {
    const p = plugin(estado({ ativa: true, rodando: true, inicioUtcMs: INICIO }), 12);
    const enviar = vi.fn(async (l: object[]) => ({ aceitas: l.map((_, i) => i), rejeitadas: [], pendentes: [] }));
    render(<CartaoDaNoite plugin={p} agora={() => INICIO} enviar={enviar} />);
    const encerrar = await screen.findByRole("button", { name: /encerrar a noite/i });
    await act(async () => fireEvent.click(encerrar));
    expect(p.encerrar).toHaveBeenCalledTimes(1);
    expect(enviar).toHaveBeenCalledTimes(1);
    expect((await screen.findByRole("status")).textContent).toMatch(/12 épocas enviadas/);
  });

  it("falha de envio fica na tela, e as epocas esperam o proximo toque", async () => {
    const p = plugin(estado({ ativa: false, rodando: false }), 5);
    const enviar = vi.fn(async () => {
      throw new Error("Sem conexao. A leitura nao foi gravada.");
    });
    render(<CartaoDaNoite plugin={p} agora={() => INICIO} enviar={enviar} />);
    expect((await screen.findByRole("status")).textContent).toMatch(/Sem conexao/);
    expect(await screen.findByText(/5 épocas aguardando envio/)).toBeTruthy();
    expect(p.enviadas).toBe(0);
  });

  it("sem o envio disponivel (sem dispositivo ou sessao), nada e mandado", async () => {
    const p = plugin(estado({ ativa: false, rodando: false }), 5);
    render(<CartaoDaNoite plugin={p} agora={() => INICIO} />);
    await screen.findByRole("button", { name: /iniciar a noite/i });
    expect(p.lerEpocas).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: /enviar agora/i })).toBeNull();
  });

  it("sem posicao escolhida, a noite nao comeca (etapa 4)", async () => {
    const p = plugin(estado());
    render(<CartaoDaNoite plugin={p} agora={() => INICIO} />);
    const iniciar = (await screen.findByRole("button", { name: /iniciar a noite/i })) as HTMLButtonElement;
    await waitFor(() => expect(p.estado).toHaveBeenCalled());
    expect(iniciar.disabled).toBe(true);
    fireEvent.click(screen.getByLabelText(/sobre o colch/i));
    await waitFor(() => expect(iniciar.disabled).toBe(false));
    await act(async () => fireEvent.click(iniciar));
    expect(p.iniciar).toHaveBeenCalledWith({ posicao: "colchao" });
  });

  it("o aviso de nao carregar dentro da fronha esta antes do botao (etapa 4)", async () => {
    render(<CartaoDaNoite plugin={plugin(estado())} agora={() => INICIO} />);
    expect(await screen.findByText(/não deixe o celular carregando/i)).toBeTruthy();
  });
});
