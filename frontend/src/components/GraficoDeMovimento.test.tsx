// @vitest-environment jsdom
// UI-43 (etapa 1): o gráfico próprio faz o que o do recharts fazia.
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { MAX_MARCAS, geometria, indiceNaPosicao } from "../lib/geometriaDoGrafico";
import type { PontoDaSerie } from "../lib/metricas";
import { GraficoDeMovimento } from "./GraficoDeMovimento";

afterEach(cleanup);

// O jsdom não tem PointerEvent: sem isto, o evento chega sem `clientX`.
if (typeof window.PointerEvent === "undefined") {
  (window as unknown as { PointerEvent: typeof MouseEvent }).PointerEvent = class extends MouseEvent {} as typeof MouseEvent;
}

const LIMITE = 1.2;
const p = (hora: string, intensidade: number | null, movimento = false): PontoDaSerie =>
  ({ hora, intensidade, movimento, lacuna: false });
const lacuna = (ms?: number): PontoDaSerie =>
  ({ hora: "sem dados", intensidade: null, movimento: false, lacuna: true, duracaoDaLacunaMs: ms });

const NOITE = [p("23:00:00", 0.2), p("23:00:30", 1.8, true), p("23:01:00", 0.3), lacuna(2 * 3600_000),
  p("01:01:00", 0.1), p("01:01:30", 2.4, true)];

describe("a geometria", () => {
  it("cada ponto no centro da sua faixa, como o eixo categórico", () => {
    const g = geometria([p("1", 1), p("2", 1), p("3", 1), p("4", 1)], LIMITE, 400, 100);
    expect(g.xs).toEqual([50, 150, 250, 350]);
  });

  it("a linha quebra na lacuna, e a área também", () => {
    const g = geometria(NOITE, LIMITE);
    expect(g.linhas).toHaveLength(2);
    expect(g.areas).toHaveLength(2);
    expect(g.linhas[0].match(/[ML]/g)).toHaveLength(3);
  });

  it("o limite aparece mesmo com tudo abaixo dele (DASH-07)", () => {
    const g = geometria([p("1", 0.1), p("2", 0.2)], LIMITE, 600, 200);
    expect(g.yDoLimite).toBeGreaterThan(0);
    expect(g.yDoLimite).toBeLessThan(200);
    for (const d of g.linhas) for (const y of d.match(/ (\d+(\.\d+)?)/g)!.map(Number)) expect(y).toBeGreaterThan(g.yDoLimite);
  });

  it("o ponto mais alto fica abaixo do topo, com folga", () => {
    const g = geometria([p("1", 3), p("2", 0)], LIMITE, 600, 200);
    const ys = g.linhas[0].match(/ (\d+(\.\d+)?)/g)!.map(Number);
    expect(Math.min(...ys)).toBeGreaterThan(0);
  });

  it("marcador só nos pontos com movimento; coluna só nas lacunas", () => {
    const g = geometria(NOITE, LIMITE);
    expect(g.pontosDeMovimento).toHaveLength(2);
    expect(g.lacunas).toHaveLength(1);
  });

  it("uma marca por minuto, mesmo com dois pontos no mesmo minuto", () => {
    const g = geometria([p("23:00:00", 0.1), p("23:00:30", 0.1), p("23:01:00", 0.1)], LIMITE);
    expect(g.marcas.map((m) => m.rotulo)).toEqual(["23:00", "23:01"]);
  });

  it("as horas do eixo saem só de pontos com hora, no máximo seis, em HH:MM", () => {
    const longa = Array.from({ length: 50 }, (_, i) => p(`${String(i % 24).padStart(2, "0")}:00:00`, 0.1));
    const g = geometria([...longa, lacuna()], LIMITE);
    expect(g.marcas.length).toBeLessThanOrEqual(MAX_MARCAS);
    expect(g.marcas.every((m) => /^\d\d:\d\d$/.test(m.rotulo))).toBe(true);
  });

  it("a posição do dedo vira o índice da faixa, sem sair da série", () => {
    expect(indiceNaPosicao(0, 4)).toBe(0);
    expect(indiceNaPosicao(0.49, 4)).toBe(1);
    expect(indiceNaPosicao(1, 4)).toBe(3);
    expect(indiceNaPosicao(-0.2, 4)).toBe(0);
    expect(indiceNaPosicao(0.5, 0)).toBeNull();
  });
});

describe("o gráfico na tela", () => {
  function montar(serie = NOITE) {
    const r = render(<GraficoDeMovimento serie={serie} limite={LIMITE} />);
    const area = screen.getByLabelText("Percorrer os registros do gráfico com as setas");
    area.getBoundingClientRect = () => ({ left: 0, width: 600, top: 0, height: 200, right: 600, bottom: 200, x: 0, y: 0, toJSON() {} });
    return { ...r, area };
  }

  it("desenha a linha do limite, os trechos, os marcadores e a lacuna", () => {
    const { container } = montar();
    expect(container.querySelectorAll("[data-limite]")).toHaveLength(1);
    expect(container.querySelectorAll("[data-linha]")).toHaveLength(2);
    expect(container.querySelectorAll("[data-movimento]")).toHaveLength(2);
    expect(container.querySelectorAll("[data-lacuna]")).toHaveLength(1);
    expect(screen.getByRole("img").getAttribute("aria-label")).toContain("2 com movimento");
  });

  it("passar o dedo diz o horário e Movimento ou Repouso, por escrito", () => {
    const { area } = montar();
    fireEvent.pointerMove(area, { clientX: 150 }); // índice 1
    expect(screen.getByRole("status").textContent).toBe("23:00:30Movimento");
    fireEvent.pointerMove(area, { clientX: 20 }); // índice 0
    expect(screen.getByRole("status").textContent).toBe("23:00:00Repouso");
    fireEvent.pointerLeave(area);
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("na lacuna, diz que não há registro e por quanto tempo", () => {
    const { area } = montar();
    fireEvent.pointerMove(area, { clientX: 350 }); // índice 3
    expect(screen.getByRole("status").textContent).toBe("Sem registro2h 0m sem registro");
  });

  it("as setas percorrem os pontos", () => {
    const { area } = montar();
    fireEvent.keyDown(area, { key: "ArrowRight" });
    expect(screen.getByRole("status").textContent).toContain("23:00:00");
    fireEvent.keyDown(area, { key: "ArrowRight" });
    expect(screen.getByRole("status").textContent).toContain("23:00:30");
    fireEvent.keyDown(area, { key: "ArrowLeft" });
    expect(screen.getByRole("status").textContent).toContain("23:00:00");
  });

  it("as horas do eixo aparecem", () => {
    montar();
    expect(screen.getByText("23:00")).toBeTruthy();
    expect(screen.queryByText("sem dados")).toBeNull();
    // A lacuna não vira rótulo, nem cortada ("sem d").
    expect(geometria(NOITE, LIMITE).marcas.every((m) => /^\d\d:\d\d$/.test(m.rotulo))).toBe(true);
  });
});
