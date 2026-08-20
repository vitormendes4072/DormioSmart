import { describe, expect, it } from "vitest";

import { descreverUltimoContato, estaAtivo, type Dispositivo } from "./dispositivos";

const base: Dispositivo = {
  id: "dev-1",
  nome: "ESP32 do quarto",
  created_at: "2026-08-20T00:00:00Z",
  last_seen_at: null,
  revoked_at: null,
};

const haMinutos = (m: number) => new Date(Date.now() - m * 60_000).toISOString();

describe("estaAtivo", () => {
  it("ativo enquanto revoked_at for nulo", () => {
    expect(estaAtivo(base)).toBe(true);
  });

  it("revogado quando ha data", () => {
    expect(estaAtivo({ ...base, revoked_at: "2026-08-20T01:00:00Z" })).toBe(false);
  });
});

describe("descreverUltimoContato", () => {
  it("distingue 'nunca enviou' de 'enviou faz tempo'", () => {
    // E a pergunta real de quem acabou de parear: funcionou ou nao?
    expect(descreverUltimoContato(base)).toContain("nunca");
  });

  it.each([
    [0, "agora mesmo"],
    [5, "há 5 min"],
    [90, "há 1h"],
    [60 * 26, "ontem"],
    [60 * 24 * 3, "há 3 dias"],
  ])("%i minutos atras -> %s", (minutos, esperado) => {
    expect(descreverUltimoContato({ ...base, last_seen_at: haMinutos(minutos) })).toBe(esperado);
  });

  it("nao quebra com data invalida", () => {
    expect(descreverUltimoContato({ ...base, last_seen_at: "nao-e-data" })).toBe(
      "data desconhecida",
    );
  });
});
