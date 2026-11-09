import { describe, expect, it } from "vitest";

import {
  ANTECEDENCIA_DA_ORIGEM_MS,
  ATRASO_DE_FECHAMENTO_MS,
  type EstadoDaNoite,
  coberturaDaNoite,
  noiteInterrompida,
  noiteNativaDisponivel,
} from "./noiteNativa";

const INICIO = 1_794_096_000_000;

function estado(parcial: Partial<EstadoDaNoite>): EstadoDaNoite {
  return {
    ativa: true,
    rodando: true,
    inicioUtcMs: INICIO,
    epocasGravadas: 0,
    recusadas: 0,
    recusadasPorTaxa: 0,
    semFeatures: 0,
    amostras: 0,
    taxaHz: 0,
    retomadas: 0,
    ultimaEpocaUtcMs: 0,
    isentoDeBateria: false,
    ...parcial,
  };
}

/** O instante em que a época `n` (0, 1, ...) já deveria ter fechado. */
function quandoFecha(n: number) {
  return INICIO + ANTECEDENCIA_DA_ORIGEM_MS + ATRASO_DE_FECHAMENTO_MS + (n + 1) * 30_000;
}

describe("noiteNativaDisponivel (APP-02)", () => {
  it("no site (navegador) nao aparece", () => {
    expect(noiteNativaDisponivel({ isNativePlatform: () => false, isPluginAvailable: () => true })).toBe(false);
  });

  it("no app sem o plugin nativo nao aparece", () => {
    expect(noiteNativaDisponivel({ isNativePlatform: () => true, isPluginAvailable: () => false })).toBe(false);
  });

  it("no app com o plugin aparece", () => {
    expect(noiteNativaDisponivel({ isNativePlatform: () => true, isPluginAvailable: (n) => n === "Noite" })).toBe(true);
  });
});

describe("coberturaDaNoite (APP-02)", () => {
  it("antes de a primeira epoca poder fechar nao ha cobertura", () => {
    expect(coberturaDaNoite(estado({}), quandoFecha(0) - 1)).toBeNull();
    expect(coberturaDaNoite(estado({ inicioUtcMs: 0 }), quandoFecha(10))).toBeNull();
  });

  it("todas as epocas gravadas e 100 %", () => {
    expect(coberturaDaNoite(estado({ epocasGravadas: 10 }), quandoFecha(9))).toBe(1);
  });

  it("um servico morto de madrugada aparece como cobertura baixa", () => {
    // 8 h de noite, e o sistema matou o app depois de 2 h: 240 de 960.
    expect(coberturaDaNoite(estado({ epocasGravadas: 240 }), quandoFecha(959))).toBeCloseTo(0.25, 6);
  });

  it("nunca passa de 100 %, nem com o relogio adiantado", () => {
    expect(coberturaDaNoite(estado({ epocasGravadas: 12 }), quandoFecha(9))).toBe(1);
  });
});

describe("noiteInterrompida (APP-02)", () => {
  it("ativa e rodando nao e interrompida", () => {
    expect(noiteInterrompida(estado({}))).toBe(false);
  });

  it("ativa no arquivo sem o servico rodando e interrompida", () => {
    expect(noiteInterrompida(estado({ rodando: false }))).toBe(true);
  });

  it("encerrada nao e interrompida", () => {
    expect(noiteInterrompida(estado({ ativa: false, rodando: false }))).toBe(false);
  });
});
