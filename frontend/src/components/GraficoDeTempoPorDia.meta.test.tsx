// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";

import { GraficoDeTempoPorDia } from "./GraficoDeTempoPorDia";

afterEach(cleanup);
const hoje = new Date(2026, 10, 26, 12);
const segunda = new Date(2026, 10, 23, 12);
const terca = new Date(2026, 10, 24, 12);
const props = {
  referencia: hoje, hoje, selecionado: null, aoSelecionarDia: () => {},
  carregando: false, falhou: false, parcial: false, recarregar: () => {},
  registros: new Map([[segunda.getTime(), 7 * 3_600_000], [terca.getTime(), 5 * 3_600_000]]),
};

it("UI-61: mostra a mesma média, o número de dias, a projeção e a linha distinta quando há meta", () => {
  const { container, rerender } = render(<GraficoDeTempoPorDia {...props} />);
  expect(screen.queryByText("Sua meta", { exact: true })).toBeNull();
  expect(container.querySelector("[data-linha-da-meta]")).toBeNull();
  rerender(<GraficoDeTempoPorDia {...props} meta={480} />);
  expect(screen.getByText(/Média dos dias com registro: 6 h \(em 2 dias\)/)).toBeTruthy();
  expect(screen.getByText("Sua meta: 8 h")).toBeTruthy();
  expect(screen.getByText(/Nos 4 dias que restam, cerca de 9 h/)).toBeTruthy();
  expect(container.querySelector("[data-linha-da-meta]")?.getAttribute("stroke-dasharray")).toBe("9 4");
});

it("UI-61: exibe a meta em semana parcial ou vazia, sem projetar", () => {
  const { rerender } = render(<GraficoDeTempoPorDia {...props} meta={480} parcial />);
  expect(screen.getByText(/A semana está incompleta/)).toBeTruthy();
  expect(screen.getByText("Sua meta: 8 h")).toBeTruthy();
  expect(screen.queryByText(/dias que restam/)).toBeNull();
  rerender(<GraficoDeTempoPorDia {...props} meta={480} registros={new Map()} />);
  expect(screen.getByText(/Sem média nesta semana/)).toBeTruthy();
  expect(screen.getByText("Sua meta: 8 h")).toBeTruthy();
});
