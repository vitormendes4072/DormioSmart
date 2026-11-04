// @vitest-environment jsdom
/**
 * DEMO-02: o modo demonstração passa pelo guarda de rotas — e só no build de
 * desenvolvimento.
 *
 * O `DEMO-01` (19/08) criou `/dashboard?demo=1` para capturar o painel sem
 * conta; o guarda (`AUTH-04`, 20/08) passou a mandar quem não tem sessão para o
 * login antes de o parâmetro ser lido. Ficou quebrado dois meses e meio porque
 * nenhum teste passava pelo guarda. Estes passam.
 *
 * A rota e o guarda são os REAIS; só a sessão é falsa (ninguém logado).
 */
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("../contexts/AuthContext", () => ({
  useAuth: () => ({ sessao: null, carregando: false }),
}));

import { RotaProtegida } from "./Guardas";

afterEach(() => {
  cleanup();
  vi.unstubAllEnvs();
});

function abrir(caminho: string) {
  render(
    <MemoryRouter initialEntries={[caminho]}>
      <Routes>
        <Route path="/login" element={<p>tela de login</p>} />
        <Route element={<RotaProtegida />}>
          <Route path="/dashboard" element={<p>painel montado</p>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe("RotaProtegida e o modo demonstração (DEMO-02)", () => {
  it("em desenvolvimento, /dashboard?demo=1 monta o painel sem sessão", () => {
    vi.stubEnv("DEV", true);
    abrir("/dashboard?demo=1");
    expect(screen.queryByText("painel montado")).not.toBeNull();
    expect(screen.queryByText("tela de login")).toBeNull();
  });

  it("sem o parâmetro, quem não tem sessão vai ao login", () => {
    vi.stubEnv("DEV", true);
    abrir("/dashboard");
    expect(screen.queryByText("tela de login")).not.toBeNull();
  });

  it("?demo=0 não é demonstração: vai ao login", () => {
    vi.stubEnv("DEV", true);
    abrir("/dashboard?demo=0");
    expect(screen.queryByText("tela de login")).not.toBeNull();
  });

  it("fora do build de desenvolvimento (a produção), ?demo=1 vai ao login", () => {
    vi.stubEnv("DEV", false);
    abrir("/dashboard?demo=1");
    expect(screen.queryByText("tela de login")).not.toBeNull();
    expect(screen.queryByText("painel montado")).toBeNull();
  });
});
