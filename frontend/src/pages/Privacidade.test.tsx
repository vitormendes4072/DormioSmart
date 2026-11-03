// @vitest-environment jsdom
/**
 * LGPD-01 (b): a página /privacidade mostra a política renderizada, com o aviso
 * de versão preliminar, e sem o controlador cru quando a variável falta.
 */
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it } from "vitest";

import { NAO_INFORMADO } from "../lib/politica";
import Privacidade from "./Privacidade";

afterEach(() => {
  cleanup();
});

function abrir() {
  render(
    <MemoryRouter>
      <Privacidade />
    </MemoryRouter>,
  );
}

describe("página da política de privacidade", () => {
  it("renderiza o título e as seções como títulos, não como texto cru", () => {
    abrir();
    expect(screen.getByRole("heading", { level: 1, name: /Política de Privacidade/ })).toBeTruthy();
    expect(screen.getByRole("heading", { level: 2, name: /Quem trata os seus dados/ })).toBeTruthy();
    expect(screen.getByRole("heading", { level: 2, name: /Alterações nesta política/ })).toBeTruthy();
    expect(document.body.textContent).not.toContain("## ");
  });

  it("avisa que é versão preliminar", () => {
    abrir();
    expect(screen.getByRole("note").textContent).toContain("Versão preliminar");
  });

  it("sem a variável de build, não mostra o marcador cru", () => {
    abrir();
    expect(document.body.textContent).not.toContain("[CONTROLADOR]");
    expect(document.body.textContent).not.toContain("[CONTATO]");
    expect(document.body.textContent).toContain(NAO_INFORMADO);
  });

  it("as tabelas da política viram tabela (remark-gfm)", () => {
    abrir();
    expect(document.querySelectorAll("table").length).toBeGreaterThan(0);
  });
});
