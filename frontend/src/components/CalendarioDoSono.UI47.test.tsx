// @vitest-environment jsdom
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { CalendarioDoSono } from "./CalendarioDoSono";
import { useHistoricoPaginado } from "../hooks/useHistoricoPaginado";
import type { LeituraSono } from "../types/sleep";

vi.mock("../hooks/useHistoricoPaginado");

const data = (dia: number) => new Date(2026, 10, dia, 12);
const recarregar = vi.fn();
const leituras: LeituraSono[] = [[23, 2], [25, 4]].flatMap(([dia, horas]) =>
  Array.from({ length: horas * 120 }, (_, i) => ({
    created_at: new Date(2026, 10, dia, 2, 0, (i + 1) * 30).toISOString(),
    device_id: "p",
    epoca_segundos: 30,
    movimento_total: 9.81,
    temp: null,
    status: "Repouso",
  })),
);

function CalendarioControlado() {
  const [selecionado, setDia] = useState<Date | null>(null);
  const [ancora, setAncora] = useState(() => data(26));
  return <CalendarioDoSono dispositivo={null} demo={false} selecionado={selecionado}
    aoSelecionarDia={setDia} ancora={ancora} aoNavegar={setAncora} />;
}

const grafico = () => within(screen.getByRole("region", { name: "Tempo registrado por dia" }));
const botaoSegunda = /^segunda-feira, 23 de novembro, 2h 00m registrados$/;

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(data(26));
  vi.mocked(useHistoricoPaginado).mockReturnValue({
    dados: { leituras, truncada: false }, carregando: false, erro: null, recarregar,
  });
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.clearAllMocks();
});

it("UI-47: passar o mouse só consulta, tocar seleciona e repetir o toque limpa", async () => {
  const user = userEvent.setup();
  render(<CalendarioControlado />);
  const barra = () => grafico().getByRole("button", { name: botaoSegunda });
  await user.hover(barra());
  expect(grafico().getByRole("tooltip", { hidden: true }).textContent).toContain("2h 00m registrados");
  expect(barra().getAttribute("aria-pressed")).toBe("false");
  await user.unhover(barra());
  expect(grafico().queryByRole("tooltip", { hidden: true })).toBeNull();

  await user.pointer({ keys: "[TouchA]", target: barra() });
  expect(barra().getAttribute("aria-pressed")).toBe("true");
  expect(grafico().getByRole("tooltip", { hidden: true }).textContent).toContain("2h 00m registrados");
  const calendario = within(screen.getByRole("region", { name: "Calendário do sono" }));
  const dia = calendario.getByRole("button", { name: /^segunda-feira, 23 de novembro/, pressed: true });
  expect(dia.querySelector("[data-marca-dia]")).toBeTruthy();
  expect(barra().querySelector("[data-marca-dia]")).toBeTruthy();

  await user.pointer({ keys: "[TouchA]", target: barra() });
  expect(barra().getAttribute("aria-pressed")).toBe("false");
  expect(calendario.getByRole("button", { name: "Expandir", expanded: false })).toBeTruthy();
});

it("UI-47: Enter seleciona e Espaço limpa no mesmo controle", async () => {
  const user = userEvent.setup();
  render(<CalendarioControlado />);
  const barra = grafico().getByRole("button", { name: botaoSegunda });
  for (let i = 0; i < 20 && document.activeElement !== barra; i++) await user.tab();
  expect(document.activeElement).toBe(barra);
  await user.keyboard("{Enter}");
  expect(barra.getAttribute("aria-pressed")).toBe("true");
  expect(grafico().getByRole("tooltip", { hidden: true }).textContent).toContain("2h 00m registrados");
  await user.keyboard(" ");
  expect(barra.getAttribute("aria-pressed")).toBe("false");
});

it("UI-47: distingue dia sem registro de dia futuro no tooltip e no eixo", async () => {
  const user = userEvent.setup();
  const { container } = render(<CalendarioControlado />);
  const vazio = grafico().getByRole("button", { name: /^terça-feira, 24 de novembro, sem registro$/ });
  await user.hover(vazio);
  expect(grafico().getByRole("tooltip", { hidden: true }).textContent).toMatch(/sem registro/);
  expect(grafico().queryByRole("button", { name: /sexta-feira/ })).toBeNull();
  expect(grafico().getByText("Sex")).toBeTruthy();
  expect(container.querySelectorAll("[data-barra]")).toHaveLength(2);
});

it("UI-47: histórico parcial anuncia dados incompletos e resume só os valores conhecidos", async () => {
  const user = userEvent.setup();
  vi.mocked(useHistoricoPaginado).mockReturnValue({
    dados: { leituras, truncada: true }, carregando: false, erro: null, recarregar,
  });
  render(<CalendarioControlado />);
  expect(grafico().getByRole("status").textContent).toMatch(/semana está incompleta/i);
  const incompleto = grafico().getByRole("button", { name: /^terça-feira, 24 de novembro, dados incompletos$/ });
  await user.hover(incompleto);
  expect(grafico().getByRole("tooltip", { hidden: true }).textContent).toMatch(/dados incompletos/);
  expect(grafico().queryByRole("button", { name: /sem registro/ })).toBeNull();
  const resumo = grafico().getByRole("list", { name: "Resumo do tempo registrado" }).textContent;
  expect(resumo).toMatch(/Mais tempo: Qua · 4h 00m/);
  expect(resumo).toMatch(/Menos tempo: Seg · 2h 00m/);
  expect(resumo).toMatch(/Média dos dias com registro: 3h 00m/);
});

it("UI-47: mostra carregamento, nova tentativa e semana vazia", async () => {
  const user = userEvent.setup();
  vi.mocked(useHistoricoPaginado).mockReturnValue({ dados: undefined, carregando: true, erro: null, recarregar });
  const { rerender } = render(<CalendarioControlado />);
  expect(grafico().getByRole("status").textContent).toMatch(/Carregando/);

  vi.mocked(useHistoricoPaginado).mockReturnValue({ dados: null, carregando: false, erro: "falha", recarregar });
  rerender(<CalendarioControlado />);
  expect(grafico().getByRole("alert")).toBeTruthy();
  await user.click(grafico().getByRole("button", { name: "Tentar novamente" }));
  expect(recarregar).toHaveBeenCalledOnce();

  vi.mocked(useHistoricoPaginado).mockReturnValue({
    dados: { leituras: [], truncada: false }, carregando: false, erro: null, recarregar,
  });
  rerender(<CalendarioControlado />);
  expect(grafico().getByText("Sem registros nesta semana")).toBeTruthy();
});
