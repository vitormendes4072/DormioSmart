// @vitest-environment jsdom
/**
 * UI-52: o topo do Histórico. As contas são somas por sessão, sem o intervalo entre
 * elas; o gráfico tem uma barra por sessão e leva à sessão escolhida.
 */
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { escalaEmHoras, resumirPeriodo, rotuloVisivel, type SessaoDoPeriodo } from "../lib/resumoDoPeriodo";
import { ResumoDoPeriodo } from "./ResumoDoPeriodo";

afterEach(cleanup);

const H = 3_600_000;
const M = 60_000;

function sessao(dia: number, tempo: number, periodo: number | null): SessaoDoPeriodo {
  const inicio = new Date(2026, 10, dia, 23, 0).getTime();
  return { chave: `s${dia}`, inicio, fim: inicio + (periodo ?? tempo), tempo, periodo };
}

describe("resumirPeriodo", () => {
  it("soma as sessões, tira a média e a fração do período somado", () => {
    const r = resumirPeriodo([sessao(20, 6 * H, 8 * H), sessao(22, 7 * H, 7 * H)]);
    expect(r).toEqual({ sessoes: 2, tempoMs: 13 * H, mediaMs: 6.5 * H, fracaoRegistrada: 13 / 15 });
  });

  it("o intervalo entre as sessões não entra no período", () => {
    // Duas noites com dois dias entre elas: o denominador é 8h + 7h, e não de 20/11 a 22/11.
    const r = resumirPeriodo([sessao(20, 6 * H, 8 * H), sessao(22, 7 * H, 7 * H)]);
    expect(r.fracaoRegistrada).toBeCloseTo(0.8667, 4);
  });

  it("sessão sem período calculável entra no tempo, mas não na fração", () => {
    const r = resumirPeriodo([sessao(20, 6 * H, 8 * H), sessao(21, 30_000, null)]);
    expect(r.tempoMs).toBe(6 * H + 30_000);
    expect(r.fracaoRegistrada).toBe(0.75);
  });

  it("sem sessões não inventa média nem porcentagem", () => {
    expect(resumirPeriodo([])).toEqual({ sessoes: 0, tempoMs: 0, mediaMs: null, fracaoRegistrada: null });
  });
});

describe("a escala e os rótulos", () => {
  it("a escala cabe a maior barra em três divisões de horas inteiras", () => {
    expect(escalaEmHoras(8 * H)).toEqual({ topoMs: 9 * H, ticks: [9, 6, 3, 0] });
    expect(escalaEmHoras(10 * M)).toEqual({ topoMs: 3 * H, ticks: [3, 2, 1, 0] });
  });

  it("até 10 barras, todos os rótulos; com 30, uns 8 e sempre o último", () => {
    expect(Array.from({ length: 10 }, (_, i) => rotuloVisivel(i, 10)).every(Boolean)).toBe(true);
    const visiveis = Array.from({ length: 30 }, (_, i) => i).filter((i) => rotuloVisivel(i, 30));
    expect(visiveis.at(-1)).toBe(29);
    expect(visiveis.length).toBeGreaterThanOrEqual(7);
    expect(visiveis.length).toBeLessThanOrEqual(9);
  });
});

describe("ResumoDoPeriodo (UI-52)", () => {
  const sessoes = [sessao(22, 7 * H, 7 * H), sessao(20, 6 * H, 8 * H)];

  it("mostra os quatro números do período", () => {
    render(<ResumoDoPeriodo sessoes={sessoes} />);
    const numeros = within(screen.getByRole("list", { name: "Números do período" })).getAllByRole("listitem");
    expect(numeros.map((n) => n.textContent)).toEqual([
      "2Sessões", "13h 0mTempo registrado", "6h 30mMédia por sessão", "87%Do período foi registrado",
    ]);
  });

  it("uma barra por sessão, da mais antiga à mais recente, e a parte sem registro só onde falta", () => {
    const { container } = render(<ResumoDoPeriodo sessoes={sessoes} />);
    const barras = Array.from(container.querySelectorAll("[data-barra]"));
    expect(barras.map((b) => b.getAttribute("data-barra"))).toEqual(["s20", "s22"]);
    expect(barras[0].querySelector("[data-sem-registro]")).not.toBeNull();
    expect(barras[1].querySelector("[data-sem-registro]")).toBeNull();
    expect(container.querySelector("[data-media]")).not.toBeNull();
  });

  it("cada barra diz por escrito a data e o tempo, e leva à sessão", () => {
    const aoEscolher = vi.fn();
    render(<ResumoDoPeriodo sessoes={sessoes} aoEscolherSessao={aoEscolher} />);
    const barra = screen.getByRole("button", { name: /^20 de nov\., 23:00, 6h 0m registrados de 8h 0m$/ });
    fireEvent.click(barra);
    expect(aoEscolher).toHaveBeenCalledWith("s20");
  });

  it("com uma sessão só, não desenha a média", () => {
    const { container } = render(<ResumoDoPeriodo sessoes={[sessoes[0]]} />);
    expect(container.querySelector("[data-media]")).toBeNull();
    expect(screen.getByRole("list", { name: "Números do período" }).textContent).toContain("1Sessão");
  });

  it("com a série de movimento, o gráfico é o de movimento das últimas 24 horas", () => {
    const serie = [0, 1, 2].map((i) => ({ hora: `0${i}:00`, intensidade: 0.1, movimento: false, lacuna: false }));
    render(<ResumoDoPeriodo sessoes={[sessoes[0]]} movimento={serie} />);
    expect(screen.getByRole("heading", { name: "Movimento nas últimas 24 horas" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: /registrados/ })).toBeNull();
  });

  it("período incompleto aparece escrito", () => {
    render(<ResumoDoPeriodo sessoes={sessoes} parcial />);
    expect(screen.getByRole("status").textContent).toContain("Período incompleto");
  });
});
