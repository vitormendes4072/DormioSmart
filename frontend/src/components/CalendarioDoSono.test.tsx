// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { CalendarioDoSono } from "./CalendarioDoSono";

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

it("UI-46: comunica seleção e remoção sem expandir a semana compacta", async () => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date(2026, 10, 25, 12));
  const aoSelecionarDia = vi.fn();
  const dia = new Date(2026, 10, 24, 12);
  const calendario = (selecionado: Date | null) =>
    <CalendarioDoSono dispositivo={null} demo selecionado={selecionado} aoSelecionarDia={aoSelecionarDia} />;
  const { rerender } = render(calendario(null));
  await screen.findByRole("button", { name: /quarta-feira, 25 de novembro, com registro/ });
  const terca = () => screen.getByRole("button", { name: /^terça-feira, 24 de novembro/ });

  fireEvent.click(terca());
  expect(screen.getByRole("button", { name: "Expandir", expanded: false })).toBeTruthy();
  expect(aoSelecionarDia).toHaveBeenLastCalledWith(dia);

  rerender(calendario(dia));
  expect(terca().getAttribute("aria-pressed")).toBe("true");
  fireEvent.click(terca());
  expect(aoSelecionarDia).toHaveBeenLastCalledWith(null);
  fireEvent.click(screen.getByRole("button", { name: "Expandir", expanded: false }));
  expect(screen.getByRole("button", { name: "Recolher", expanded: true })).toBeTruthy();
});
