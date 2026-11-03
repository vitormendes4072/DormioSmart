// @vitest-environment jsdom
/**
 * LGPD-05: o cadastro só segue com a declaração de ter 18 anos ou mais.
 *
 * O que estes testes travam: sem a caixa marcada, nenhum `signUp` chega ao
 * Supabase e a pessoa vê o motivo; com ela, a data da declaração vai junto, nos
 * metadados da conta. A tela é a REAL; só o cliente do Supabase é falso.
 */
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { signUp } = vi.hoisted(() => ({
  signUp: vi.fn(() => Promise.resolve({ data: { session: null }, error: null })),
}));

vi.mock("../lib/supabase", () => ({
  problemaDeConfiguracao: () => null,
  obterSupabase: () => ({ auth: { signUp } }),
}));

import { FALTA_DECLARAR_MAIORIDADE } from "../lib/autenticacao";
import { Register } from "./Register";

function preencher() {
  render(
    <MemoryRouter>
      <Register />
    </MemoryRouter>,
  );
  fireEvent.change(screen.getByLabelText("Nome completo"), { target: { value: "Ana" } });
  fireEvent.change(screen.getByLabelText("E-mail"), { target: { value: "ana@exemplo.com" } });
  fireEvent.change(screen.getByLabelText("Senha"), { target: { value: "senha-bem-longa" } });
}

beforeEach(() => {
  signUp.mockClear();
});

afterEach(() => {
  cleanup();
});

describe("cadastro só para maiores de 18 (LGPD-05)", () => {
  it("sem a declaração, não chama o Supabase e diz por quê", async () => {
    preencher();
    fireEvent.click(screen.getByRole("button", { name: "Criar conta" }));
    expect(await screen.findByRole("alert")).toHaveProperty("textContent", FALTA_DECLARAR_MAIORIDADE);
    expect(signUp).not.toHaveBeenCalled();
  });

  it("com a declaração, cadastra e registra a data dela nos metadados", async () => {
    preencher();
    fireEvent.click(screen.getByLabelText(/Declaro que tenho 18 anos ou mais/));
    fireEvent.click(screen.getByRole("button", { name: "Criar conta" }));
    await waitFor(() => expect(signUp).toHaveBeenCalledTimes(1));
    const argumento = (signUp.mock.calls[0] as unknown as [{ options: { data: Record<string, string> } }])[0];
    expect(argumento.options.data.nome).toBe("Ana");
    expect(Number.isNaN(Date.parse(argumento.options.data.maior_de_18_declarado_em))).toBe(false);
  });

  it("o cadastro leva à Política de Privacidade (LGPD-01 (b))", () => {
    preencher();
    const link = screen.getByRole("link", { name: "Política de Privacidade" });
    expect(link.getAttribute("href")).toBe("/privacidade");
  });

  it("a caixa começa desmarcada", () => {
    preencher();
    expect((screen.getByLabelText(/Declaro que tenho 18 anos ou mais/) as HTMLInputElement).checked).toBe(false);
  });
});
