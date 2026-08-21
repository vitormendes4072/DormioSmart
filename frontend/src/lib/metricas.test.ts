import { describe, expect, it } from "vitest";

import { GRAVIDADE, type LeituraSono } from "../types/sleep";
import { calcularMetricas, formatarDuracao, prepararSerie } from "./metricas";

const MINUTO = 60_000;

function leitura(
  minutosDoInicio: number,
  opcoes: { total?: number | null; status?: string | null } = {},
): LeituraSono {
  return {
    created_at: new Date(Date.UTC(2026, 7, 19, 3, 0, 0) + minutosDoInicio * MINUTO).toISOString(),
    // `??` nao serve aqui: ele converteria um `total: null` explicito de volta
    // para GRAVIDADE, e o caso "leitura sem magnitude" nunca seria testado.
    movimento_total: opcoes.total === undefined ? GRAVIDADE : opcoes.total,
    temp: 32,
    status: opcoes.status === undefined ? "Repouso" : opcoes.status,
  };
}

const movimento = (min: number, total = GRAVIDADE + 2) =>
  leitura(min, { total, status: "Movimento" });

describe("calcularMetricas — sem dados", () => {
  it("nao inventa numero quando a lista esta vazia", () => {
    const m = calcularMetricas([]);
    expect(m.totalLeituras).toBe(0);
    expect(m.eventosDeMovimento).toBe(0);
    expect(m.janela).toBeNull();
    expect(m.maiorPeriodoSemMovimentoMs).toBeNull();
    expect(m.intensidadeMedia).toBeNull();
  });

  it("descarta leitura com created_at invalido em vez de propagar NaN", () => {
    const corrompida: LeituraSono = {
      created_at: "nao-e-data",
      movimento_total: 9.8,
      temp: 32,
      status: "Repouso",
    };
    const m = calcularMetricas([corrompida, leitura(0), leitura(10)]);
    expect(m.totalLeituras).toBe(2);
    expect(Number.isNaN(m.duracaoDaJanelaMs)).toBe(false);
  });
});

describe("janela de captacao", () => {
  it("vai da leitura mais antiga a mais recente, independente da ordem de entrada", () => {
    const m = calcularMetricas([leitura(30), leitura(0), leitura(15)]);
    expect(m.duracaoDaJanelaMs).toBe(30 * MINUTO);
    expect(m.janela!.inicio.getTime()).toBeLessThan(m.janela!.fim.getTime());
  });
});

describe("eventos de movimento", () => {
  it("conta pelo rotulo do dispositivo, nao recalculando o limiar", () => {
    // Intensidade alta, mas o dispositivo rotulou como repouso: manda o rotulo.
    const contraditoria = leitura(5, { total: GRAVIDADE + 5, status: "Repouso" });
    const m = calcularMetricas([leitura(0), contraditoria, movimento(10)]);
    expect(m.eventosDeMovimento).toBe(1);
  });

  it("reconhece o rotulo legado ja gravado no banco", () => {
    const legado = leitura(5, { status: "Movimento Detectado!" });
    expect(calcularMetricas([leitura(0), legado]).eventosDeMovimento).toBe(1);
  });
});

describe("maior periodo sem movimento", () => {
  it("sem nenhum evento, e a janela inteira", () => {
    const m = calcularMetricas([leitura(0), leitura(20), leitura(60)]);
    expect(m.maiorPeriodoSemMovimentoMs).toBe(60 * MINUTO);
  });

  it("e o maior intervalo entre eventos consecutivos", () => {
    // eventos em 10 e 50 -> intervalos: 0-10, 10-50, 50-60. Maior = 40min.
    const m = calcularMetricas([leitura(0), movimento(10), movimento(50), leitura(60)]);
    expect(m.maiorPeriodoSemMovimentoMs).toBe(40 * MINUTO);
  });

  it("conta as bordas da janela, nao so os intervalos do meio", () => {
    // unico evento no minuto 55: a borda inicial (0-55) e maior que a final.
    const m = calcularMetricas([leitura(0), movimento(55), leitura(60)]);
    expect(m.maiorPeriodoSemMovimentoMs).toBe(55 * MINUTO);
  });
});

describe("intensidade media", () => {
  it("e zero quando tudo esta exatamente em repouso", () => {
    expect(calcularMetricas([leitura(0), leitura(1)]).intensidadeMedia).toBeCloseTo(0, 10);
  });

  it("ignora leitura sem magnitude em vez de contar como zero", () => {
    // Uma leitura de intensidade 2 e uma sem magnitude: media = 2, nao 1.
    const semMagnitude = leitura(1, { total: null });
    const m = calcularMetricas([leitura(0, { total: GRAVIDADE + 2 }), semMagnitude]);
    expect(m.intensidadeMedia).toBeCloseTo(2, 10);
  });

  it("devolve null se nenhuma leitura tem magnitude", () => {
    const m = calcularMetricas([leitura(0, { total: null }), leitura(1, { total: null })]);
    expect(m.intensidadeMedia).toBeNull();
  });
});

describe("formatarDuracao", () => {
  it.each([
    [0, "0s"],
    [12_000, "12s"],
    [150_000, "2m 30s"],
    [45 * MINUTO, "45m 0s"],
    [8 * 3600_000 + 15 * MINUTO, "8h 15m"],
  ])("%i ms -> %s", (ms, esperado) => {
    expect(formatarDuracao(ms)).toBe(esperado);
  });

  it("mostra travessao para ausencia, nunca zero", () => {
    expect(formatarDuracao(null)).toBe("--");
  });
});

describe("prepararSerie", () => {
  it("ordena do mais antigo ao mais recente", () => {
    const serie = prepararSerie([leitura(20), leitura(0), leitura(10)]);
    expect(serie).toHaveLength(3);
    expect(serie[0].hora <= serie[1].hora).toBe(true);
  });

  it("marca o ponto como movimento conforme o rotulo do dispositivo", () => {
    const serie = prepararSerie([leitura(0), movimento(1)]);
    expect(serie[0].movimento).toBe(false);
    expect(serie[1].movimento).toBe(true);
  });

  it("preserva null de intensidade para o grafico abrir lacuna", () => {
    const serie = prepararSerie([leitura(0, { total: null })]);
    expect(serie[0].intensidade).toBeNull();
  });
});
