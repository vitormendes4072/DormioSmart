import { describe, expect, it } from "vitest";

import {
  EPOCA_PADRAO_S,
  METODO,
  agregar,
  classificar,
  desvio,
  magnitude,
  montarPayload,
} from "./acelerometro";
import { GRAVIDADE, LIMIAR_DE_MOVIMENTO } from "../types/sleep";

const REPOUSO = { ax: 0, ay: 0, az: GRAVIDADE };
const FIM = Date.UTC(2026, 7, 24, 3, 0, 0);

describe("magnitude e desvio", () => {
  it("em repouso a magnitude e a gravidade e o desvio e zero", () => {
    expect(magnitude(REPOUSO)).toBeCloseTo(GRAVIDADE, 5);
    expect(desvio(REPOUSO)).toBeCloseTo(0, 5);
  });

  it("nao depende de qual eixo carrega a gravidade", () => {
    // O celular pode estar em qualquer orientacao na cama.
    expect(magnitude({ ax: GRAVIDADE, ay: 0, az: 0 })).toBeCloseTo(GRAVIDADE, 5);
    expect(magnitude({ ax: 0, ay: GRAVIDADE, az: 0 })).toBeCloseTo(GRAVIDADE, 5);
  });

  it("desvio e absoluto — cair e subir contam igual", () => {
    expect(desvio({ ax: 0, ay: 0, az: GRAVIDADE + 2 })).toBeCloseTo(2, 5);
    expect(desvio({ ax: 0, ay: 0, az: GRAVIDADE - 2 })).toBeCloseTo(2, 5);
  });
});

describe("classificar", () => {
  it("usa o mesmo limiar do firmware", () => {
    expect(classificar(REPOUSO)).toBe("Repouso");
    expect(classificar({ ax: 0, ay: 0, az: GRAVIDADE + LIMIAR_DE_MOVIMENTO + 0.1 })).toBe(
      "Movimento",
    );
  });

  it("o limiar e estritamente maior — exatamente 1,2 ainda e repouso", () => {
    // Mesma regra do contrato: `intensidade > 1,2`, nao `>=`.
    expect(classificar({ ax: 0, ay: 0, az: GRAVIDADE + LIMIAR_DE_MOVIMENTO })).toBe("Repouso");
  });
});

describe("agregar", () => {
  it("lote vazio nao vira leitura", () => {
    // Acontece de verdade: o navegador suspende `devicemotion` com a aba no
    // fundo. Inventar uma linha de "repouso" ai seria fabricar medicao.
    expect(agregar([], EPOCA_PADRAO_S, FIM)).toBeNull();
  });

  it("escolhe a amostra de maior desvio, nao a de maior magnitude", () => {
    // Uma queda abaixo de 9,81 e movimento tanto quanto uma subida acima.
    const queda = { ax: 0, ay: 0, az: GRAVIDADE - 4 };
    const subida = { ax: 0, ay: 0, az: GRAVIDADE + 1 };
    const agregado = agregar([REPOUSO, subida, queda], EPOCA_PADRAO_S, FIM);
    expect(agregado?.az).toBeCloseTo(GRAVIDADE - 4, 1);
  });

  it("conta todas as amostras, nao so a de pico", () => {
    const agregado = agregar([REPOUSO, REPOUSO, REPOUSO], EPOCA_PADRAO_S, FIM);
    expect(agregado?.amostras).toBe(3);
  });

  it("mantem a coerencia que o backend confere", () => {
    // O backend recusa |total − √(ax²+ay²+az²)| > 0,5. Enviar os eixos da
    // amostra de pico e o que faz essa checagem continuar valendo.
    const agregado = agregar(
      [{ ax: 1.5, ay: -2.5, az: 9.0 }, REPOUSO],
      EPOCA_PADRAO_S,
      FIM,
    )!;
    const esperado = Math.sqrt(
      agregado.ax ** 2 + agregado.ay ** 2 + agregado.az ** 2,
    );
    expect(Math.abs(agregado.total - esperado)).toBeLessThan(0.5);
  });

  it("arredonda para duas casas, como o firmware transmite", () => {
    const agregado = agregar([{ ax: 0.123456, ay: 0, az: 9.876543 }], EPOCA_PADRAO_S, FIM)!;
    expect(agregado.ax).toBe(0.12);
    expect(agregado.az).toBe(9.88);
  });
});

describe("montarPayload", () => {
  const agregado = agregar([{ ax: 0, ay: 0, az: GRAVIDADE + 3 }], 60, FIM)!;
  const payload = montarPayload(agregado);

  it("declara a epoca e o metodo", () => {
    // Sem isso o backend recusa: leitura que resume 60 s tem que dizer como.
    expect(payload.epoca_s).toBe(60);
    expect(payload.metodo).toBe(METODO);
  });

  it("carimba o instante da medicao em ISO com fuso", () => {
    expect(payload.ts).toBe(new Date(FIM).toISOString());
    expect(payload.ts.endsWith("Z")).toBe(true);
  });

  it("nao inventa temperatura nem giroscopio", () => {
    // Celular nao tem temperatura do chip do MPU6050 nem sempre tem giro.
    // O contrato v2.0.0 tornou os dois opcionais exatamente para isto.
    expect(payload).not.toHaveProperty("t");
    expect(payload).not.toHaveProperty("gx");
  });

  it("classifica no proprio dispositivo, como manda o contrato", () => {
    expect(payload.status).toBe("Movimento");
  });

  it("um agregado de repouso vira Repouso", () => {
    expect(montarPayload(agregar([REPOUSO], 30, FIM)!).status).toBe("Repouso");
  });
});
