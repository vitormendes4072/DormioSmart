import { describe, expect, it } from "vitest";

import {
  TODOS_OS_DISPOSITIVOS,
  type Dispositivo,
  nomeDoDispositivo,
  precisaEscolherDispositivo,
  serieMisturaInstrumentos,
} from "./dispositivos";

function dispositivo(id: string, nome: string, revogado = false): Dispositivo {
  return {
    id,
    nome,
    created_at: "2026-08-01T00:00:00Z",
    last_seen_at: null,
    revoked_at: revogado ? "2026-08-10T00:00:00Z" : null,
  };
}

const TRAVESSEIRO = dispositivo("a", "Travesseiro");
const CELULAR = dispositivo("b", "Celular");

describe("precisaEscolherDispositivo", () => {
  it("nao mostra seletor sem dispositivo nenhum", () => {
    expect(precisaEscolherDispositivo([])).toBe(false);
  });

  it("nao mostra seletor com um dispositivo so", () => {
    // Um controle com uma opcao e ruido — e e o caso de quase todo mundo hoje.
    expect(precisaEscolherDispositivo([TRAVESSEIRO])).toBe(false);
  });

  it("mostra seletor a partir de dois", () => {
    expect(precisaEscolherDispositivo([TRAVESSEIRO, CELULAR])).toBe(true);
  });
});

describe("serieMisturaInstrumentos", () => {
  it("avisa quando ha varios dispositivos e nenhum recorte", () => {
    // E o defeito que o DASH-05 conserta: travesseiro e celular medem o mesmo
    // movimento por acoplamentos diferentes. Empilhar sem dizer e desonesto.
    expect(serieMisturaInstrumentos([TRAVESSEIRO, CELULAR], null)).toBe(true);
  });

  it("nao avisa quando um dispositivo esta recortado", () => {
    expect(serieMisturaInstrumentos([TRAVESSEIRO, CELULAR], "a")).toBe(false);
  });

  it("nao avisa com um dispositivo so — nao ha o que misturar", () => {
    expect(serieMisturaInstrumentos([TRAVESSEIRO], null)).toBe(false);
  });

  it("trata o valor vazio do seletor como ausencia de recorte", () => {
    expect(serieMisturaInstrumentos([TRAVESSEIRO, CELULAR], TODOS_OS_DISPOSITIVOS)).toBe(true);
  });
});

describe("nomeDoDispositivo", () => {
  it("nomeia o dispositivo recortado", () => {
    expect(nomeDoDispositivo([TRAVESSEIRO, CELULAR], "b")).toBe("Celular");
  });

  it("sem recorte, diz que sao todos", () => {
    expect(nomeDoDispositivo([TRAVESSEIRO, CELULAR], null)).toBe("Todos os dispositivos");
  });

  it("id fora da lista nao quebra a tela", () => {
    // Acontece se o dispositivo for apagado noutra aba com o painel aberto.
    expect(nomeDoDispositivo([TRAVESSEIRO], "sumiu")).toBe("Dispositivo desconhecido");
  });
});
