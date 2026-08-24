import { describe, expect, it } from "vitest";

import { montarConsultaDeHistorico } from "./api";

describe("montarConsultaDeHistorico", () => {
  it("sem filtro, pede a rota nua — o comportamento de antes do DASH-05", () => {
    expect(montarConsultaDeHistorico()).toBe("/api/sleep-history");
    expect(montarConsultaDeHistorico({})).toBe("/api/sleep-history");
  });

  it("recorta por dispositivo", () => {
    expect(montarConsultaDeHistorico({ dispositivo: "abc" })).toBe(
      "/api/sleep-history?device=abc",
    );
  });

  it("omite o que veio nulo em vez de mandar string vazia", () => {
    // `?device=` faria o backend receber um parametro presente e vazio.
    expect(montarConsultaDeHistorico({ dispositivo: null, desde: null, limite: null })).toBe(
      "/api/sleep-history",
    );
  });

  it("aceita limite zero como valor legitimo do chamador", () => {
    // Zero e falsy — se o teste do codigo usasse `if (filtro.limite)`, sumiria.
    expect(montarConsultaDeHistorico({ limite: 0 })).toBe("/api/sleep-history?limite=0");
  });

  it("monta a janela completa", () => {
    const url = montarConsultaDeHistorico({
      dispositivo: "abc",
      desde: "2026-08-22T00:00:00Z",
      ate: "2026-08-23T00:00:00Z",
      limite: 480,
    });
    expect(url).toContain("device=abc");
    expect(url).toContain("limite=480");
    expect(url.startsWith("/api/sleep-history?")).toBe(true);
  });

  it("escapa caracteres especiais em vez de montar url quebrada", () => {
    const url = montarConsultaDeHistorico({ dispositivo: "a b&c=d" });
    expect(url).not.toContain("a b");
    expect(url).toContain("device=a+b%26c%3Dd");
  });
});
