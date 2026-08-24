import { describe, expect, it, vi } from "vitest";

import {
  ESPERA_DE_SINAL_MS,
  MENSAGEM_SEM_SINAL,
  suportaAcelerometro,
} from "./useColeta";

describe("por que a sonda de sinal existe (APP-06)", () => {
  it("a API de acelerometro EXISTE em navegador de desktop sem sensor", () => {
    // Este e o teste que documenta o defeito. `suportaAcelerometro` responde
    // true num computador — a API esta la, os eventos e que nunca chegam.
    // Sem a sonda, comecar a coletar num desktop iniciava, mostrava
    // "0 amostras" e nao produzia leitura nenhuma, para sempre, sem dizer
    // por que.
    vi.stubGlobal("window", { DeviceMotionEvent: function () {} });
    expect(suportaAcelerometro()).toBe(true);
    vi.unstubAllGlobals();
  });

  it("sem a API, o suporte e negado", () => {
    vi.stubGlobal("window", {});
    expect(suportaAcelerometro()).toBe(false);
    vi.unstubAllGlobals();
  });

  it("a espera cabe num gesto do usuario, sem ser instantanea", () => {
    // Curta demais correria o risco de cortar um aparelho lento; longa demais
    // deixa o usuario olhando "0 amostras" sem saber se quebrou.
    expect(ESPERA_DE_SINAL_MS).toBeGreaterThanOrEqual(1000);
    expect(ESPERA_DE_SINAL_MS).toBeLessThanOrEqual(5000);
  });

  it("a mensagem diz o que fazer, e nao so o que falhou", () => {
    expect(MENSAGEM_SEM_SINAL.toLowerCase()).toContain("celular");
  });
});

describe("guarda: a sonda nao pode ser removida sem intencao", () => {
  it("o hook arma um temporizador com a espera e cai em erro", async () => {
    // O comportamento vive num hook, que esta suite (ambiente node, sem DOM)
    // nao monta. Foi verificado no navegador: sem eventos, o estado vira
    // "erro" em ~2,5 s; com eventos sinteticos a 50 Hz, segue coletando.
    // Esta guarda existe para que apagar a sonda quebre um teste, e nao so o
    // aparelho de alguem.
    const { readFileSync } = await import("node:fs");
    const fonte = readFileSync(new URL("./useColeta.ts", import.meta.url), "utf-8");

    expect(fonte).toContain("setTimeout");
    expect(fonte).toContain("ESPERA_DE_SINAL_MS");
    expect(fonte).toContain("MENSAGEM_SEM_SINAL");
    // A sonda so pode desistir quando NAO houver amostra.
    expect(fonte).toContain("if (buffer.current.length > 0) return;");
  });
});
