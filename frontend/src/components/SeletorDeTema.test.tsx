// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";

import { SeletorDeTema } from "./SeletorDeTema";
import { salvarPreferencia } from "../lib/tema";

afterEach(() => {
  cleanup();
  localStorage.clear();
  delete document.documentElement.dataset.theme;
  vi.unstubAllGlobals();
});

it("entra no tema selecionado com Tab e muda a seleção com as setas", async () => {
  vi.stubGlobal("matchMedia", vi.fn(() => ({ matches: false })));
  // O jsdom não fornece CSS.escape, usado pelo user-event para achar o grupo.
  vi.stubGlobal("CSS", { escape: (nome: string) => nome.replace(/[^\w-]/g, "\\$&") });
  salvarPreferencia(localStorage, "escuro");
  const usuario = userEvent.setup();
  render(<><SeletorDeTema /><button>Próximo controle</button></>);

  await usuario.tab();
  expect(document.activeElement).toBe(screen.getByRole("radio", { name: "Escuro" }));
  await usuario.keyboard("{ArrowLeft}");
  const claro = screen.getByRole("radio", { name: "Claro", checked: true });
  expect(document.activeElement).toBe(claro);
  expect(document.documentElement.dataset.theme).toBe("light");

  await usuario.tab();
  expect(document.activeElement).toBe(screen.getByRole("button", { name: "Próximo controle" }));
});
