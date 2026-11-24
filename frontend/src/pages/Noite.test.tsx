// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, expect, it, vi } from "vitest";

import { Noite } from "./Noite";

vi.mock("../contexts/PerfilContext", () => ({
  usePerfil: () => ({ perfil: null, recarregar: vi.fn() }),
}));

vi.mock("../hooks/useEnvioDoCelular", () => ({
  useEnvioDoCelular: () => undefined,
}));

afterEach(() => {
  cleanup();
  vi.unstubAllEnvs();
});

const CENARIOS = [
  { valor: "parada", papel: "region", cartao: "Registrar a noite inteira", botao: "Iniciar a noite" },
  { valor: "gravando", papel: "group", cartao: /^Registrando desde \d{2}:\d{2}$/, botao: "Encerrar a noite" },
  { valor: "interrompida", papel: "region", cartao: "Noite interrompida", botao: "Retomar" },
  { valor: "encerrada", papel: "group", cartao: "Última noite", botao: "Iniciar a noite" },
  { valor: "bateria", papel: "region", cartao: "Economia de bateria", botao: "Iniciar a noite" },
  { valor: "lista", papel: "article", cartao: undefined, botao: "Iniciar a noite" },
] as const;

function abrir() {
  render(<MemoryRouter initialEntries={["/noite?demo=1"]}><Noite /></MemoryRouter>);
}

async function escolher(valor: string) {
  vi.stubEnv("DEV", true);
  abrir();
  fireEvent.change(await screen.findByRole("combobox", { name: "Cenário da demonstração" }), {
    target: { value: valor },
  });
}

it("em produção, ?demo=1 mostra a Noite do site sem montar o plugin falso", () => {
  vi.stubEnv("DEV", false);
  abrir();
  expect(screen.getByText(/só funciona no app Android/)).toBeTruthy();
  expect(screen.queryByRole("combobox")).toBeNull();
  expect(screen.queryByTestId("cartao-da-noite")).toBeNull();
});

it.each(CENARIOS)("mostra o cartão certo no cenário $valor", async ({ valor, papel, cartao }) => {
  await escolher(valor);
  if (valor === "lista") {
    const artigos = await screen.findAllByRole(papel);
    expect(artigos).toHaveLength(3);
    for (const etiqueta of ["Enviada", "Em andamento", "Teste · só neste aparelho"]) {
      expect(artigos.some((artigo) => within(artigo).queryByText(etiqueta, { exact: true }))).toBe(true);
    }
    return;
  }
  const painel = await screen.findByRole(papel, { name: cartao });
  if (valor === "parada") {
    expect(within(painel).getByRole("radio", { name: "Dentro da fronha" })).toBeTruthy();
    expect(within(painel).getByRole("checkbox", { name: /Gravação de teste/ })).toBeTruthy();
  }
  if (valor === "gravando" || valor === "encerrada") {
    expect(within(painel).getByText(/\d+h \d+m/)).toBeTruthy();
    const metricas = screen.getByRole("list", { name: "Métricas da noite" });
    expect(within(metricas).getByText("Registros no aparelho")).toBeTruthy();
    expect(within(metricas).getByText("Do período foi registrado")).toBeTruthy();
  }
  if (valor === "interrompida") {
    expect(within(painel).getByRole("alert").textContent).toContain("foi interrompido");
  }
  if (valor === "bateria") {
    expect(within(painel).getByRole("button", { name: /economia de bateria/ })).toBeTruthy();
  }
});

it.each(CENARIOS)("destaca o botão principal certo no cenário $valor", async ({ valor, botao }) => {
  await escolher(valor);
  const alvo = await screen.findByRole("button", { name: botao });
  const todos = within(screen.getByTestId("cartao-da-noite")).getAllByRole("button");
  expect(todos.filter((botaoDaTela) => botaoDaTela.classList.contains("bg-primary"))).toEqual([alvo]);
  expect(alvo.classList.contains("w-full")).toBe(true);
});
