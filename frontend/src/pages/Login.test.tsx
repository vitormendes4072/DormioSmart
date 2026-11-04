// @vitest-environment jsdom
/**
 * SEC-16: depois de entrar, o login só leva a um caminho INTERNO.
 *
 * A tela é a REAL, e a navegação também (`MemoryRouter` com as rotas); só o
 * cliente do Supabase é falso. O destino chega pelo `state` da navegação, que é
 * por onde o guarda de rotas o manda.
 */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("../lib/supabase", () => ({
  problemaDeConfiguracao: () => null,
  obterSupabase: () => ({
    auth: { signInWithPassword: () => Promise.resolve({ data: {}, error: null }) },
  }),
}));

import { Login } from "./Login";

afterEach(() => {
  cleanup();
});

function Onde() {
  const local = useLocation();
  return <p data-testid="onde">{local.pathname + local.search}</p>;
}

async function entrarVindoDe(de: unknown) {
  render(
    <MemoryRouter initialEntries={[{ pathname: "/login", state: { de } }]}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="*" element={<Onde />} />
      </Routes>
    </MemoryRouter>,
  );
  fireEvent.change(screen.getByLabelText("E-mail"), { target: { value: "a@exemplo.com" } });
  fireEvent.change(screen.getByLabelText("Senha"), { target: { value: "senha-qualquer" } });
  fireEvent.click(screen.getByRole("button", { name: "Entrar" }));
  return (await screen.findByTestId("onde")).textContent;
}

describe("destino pós-login (SEC-16)", () => {
  it("volta para a página interna que a pessoa tentava abrir", async () => {
    expect(await entrarVindoDe("/configuracoes?aba=conta")).toBe("/configuracoes?aba=conta");
  });

  it("caminho que sairia do site vai para o painel", async () => {
    expect(await entrarVindoDe("//evil.example")).toBe("/dashboard");
  });

  it("sem destino, vai para o painel", async () => {
    expect(await entrarVindoDe(undefined)).toBe("/dashboard");
  });
});
