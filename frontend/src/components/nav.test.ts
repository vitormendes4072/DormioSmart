import { describe, expect, it } from "vitest";

import { itensDeNavegacao } from "./nav";

describe("destinos da navegação (UI-41)", () => {
  it("mantém Coletar no site", () => {
    expect(itensDeNavegacao(false).map(({ label, to }) => [label, to])).toEqual([
      ["Início", "/dashboard"], ["Coletar", "/coletar"], ["Histórico", "/historico"],
      ["Dispositivos", "/dispositivos"], ["Configurações", "/configuracoes"],
    ]);
  });

  it("oferece Noite no app", () => {
    expect(itensDeNavegacao(true).map(({ label, to }) => [label, to])).toEqual([
      ["Noite", "/noite"], ["Início", "/dashboard"], ["Histórico", "/historico"],
      ["Dispositivos", "/dispositivos"], ["Configurações", "/configuracoes"],
    ]);
  });
});
