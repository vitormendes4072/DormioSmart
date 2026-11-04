// @vitest-environment jsdom
/**
 * UI-23: a página inicial não descreve a arquitetura abandonada.
 *
 * Até 03/11 ela dizia que o microcontrolador "dorme em Deep Sleep e acorda ao
 * detectar movimento" e que transmite "a cada evento" — o desenho que o
 * `ARQ-01` trocou em 30/10 por sono leve com a FIFO a 50 Hz e envio em lote.
 * É o endereço que vai no perfil, no devlog e no texto do TCC: o primeiro
 * documento que alguém de fora lê, e o que menos gente relê.
 *
 * Confere o texto RENDERIZADO, não o código-fonte (o comentário de
 * `Landing.tsx` cita os termos antigos ao contar a correção).
 */
import { cleanup, render } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../contexts/AuthContext", () => ({
  useAuth: () => ({ sessao: null, carregando: false }),
}));

import { Landing } from "./Landing";

beforeEach(() => {
  // O jsdom não implementa `matchMedia` nem `IntersectionObserver`, que a
  // animação de entrada (`Revelar`) e o traçado do hero usam.
  vi.stubGlobal("matchMedia", (consulta: string) => ({
    matches: false,
    media: consulta,
    addEventListener: () => {},
    removeEventListener: () => {},
  }));
  vi.stubGlobal(
    "IntersectionObserver",
    class {
      observe() {}
      unobserve() {}
      disconnect() {}
    },
  );
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function textoDaPagina(): string {
  render(
    <MemoryRouter>
      <Landing />
    </MemoryRouter>,
  );
  return document.body.textContent ?? "";
}

describe("página inicial x arquitetura de captação (UI-23)", () => {
  it.each(["Deep Sleep", "Wake-on-Motion", "a cada evento", "acorda ao detectar movimento"])(
    "não descreve a arquitetura abandonada: %s",
    (termo) => {
      expect(textoDaPagina().toLowerCase()).not.toContain(termo.toLowerCase());
    },
  );

  it("descreve a arquitetura C2: sono leve, FIFO a 50 Hz, envio em lote", () => {
    const texto = textoDaPagina();
    expect(texto).toContain("sono leve");
    expect(texto).toContain("50 Hz");
    expect(texto).toContain("A cada 10 minutos");
  });
});
