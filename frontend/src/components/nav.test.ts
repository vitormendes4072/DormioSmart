import { describe, expect, it } from "vitest";

import { ITENS_NAV, ITEM_NOITE, itensDeNavegacao } from "./nav";

describe("navegacao (APP-02, etapa 4)", () => {
  it("no site, a navegacao e a de sempre, sem a noite", () => {
    expect(itensDeNavegacao(false)).toEqual(ITENS_NAV);
    expect(itensDeNavegacao(false).some((i) => i.to === "/noite")).toBe(false);
  });

  it("no app, a noite vem primeiro", () => {
    const itens = itensDeNavegacao(true);
    expect(itens[0]).toBe(ITEM_NOITE);
    expect(itens.slice(1)).toEqual(ITENS_NAV);
  });
});
