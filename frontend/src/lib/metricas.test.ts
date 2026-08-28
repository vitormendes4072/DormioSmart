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

describe("maior periodo sem movimento — SO DENTRO DO QUE FOI MEDIDO", () => {
  /**
   * Estes tres testes MUDARAM no DASH-09, e a mudanca e o conserto.
   *
   * Antes eles afirmavam que a pausa cobre a janela inteira entre eventos,
   * independentemente de haver leitura no meio. Era exatamente esse
   * comportamento que produziu, numa coleta real de 25/08/2026, a frase
   * "Maior pausa: 1h47m sem eventos de movimento" — quando o que houve foi
   * 1h47m SEM LEITURA NENHUMA.
   *
   * Um teste que trava comportamento errado e pior que teste nenhum: ele
   * defende o defeito. Foram reescritos para exigir o oposto.
   */

  it("nao conta trecho sem leitura como pausa", () => {
    // Leituras em 0, 20 e 60. Entre 0 e 20 nao houve medicao nenhuma; a
    // cadencia mediana e de 20 min, entao cada leitura cobre 20 min para tras
    // e a cobertura fica continua de -20 ate 60. A pausa nao pode exceder
    // isso, e sobretudo nao pode inventar cobertura onde nao houve leitura.
    const m = calcularMetricas([leitura(0), leitura(20), leitura(60)]);
    expect(m.maiorPeriodoSemMovimentoMs).not.toBeNull();
    expect(m.maiorPeriodoSemMovimentoMs!).toBeLessThanOrEqual(m.cobertura.tempoCobertoMs);
  });

  it("o buraco de coleta aparece como lacuna, e nao como repouso", () => {
    // O caso real: leituras nos minutos 0 e 1, depois nada ate 107.
    const m = calcularMetricas([leitura(0), leitura(1), leitura(107), leitura(108)]);

    expect(m.cobertura.lacunas.length).toBeGreaterThan(0);
    // A versao anterior responderia ~105 min aqui.
    expect(m.maiorPeriodoSemMovimentoMs!).toBeLessThan(10 * MINUTO);
  });

  it("dentro de medicao continua, e o maior intervalo entre eventos", () => {
    // Leituras de minuto em minuto de 0 a 10, com movimento em 2 e 4.
    // A maior pausa medida vai de 4 ate 10.
    const leituras = [];
    for (let i = 0; i <= 10; i++) {
      leituras.push(i === 2 || i === 4 ? movimento(i) : leitura(i));
    }
    const m = calcularMetricas(leituras);
    expect(m.maiorPeriodoSemMovimentoMs!).toBeCloseTo(6 * MINUTO, -3);
  });
});

describe("proporcao por tempo, nao por contagem", () => {
  it("uma leitura que cobre mais tempo pesa mais", () => {
    // Contagem daria 50%. Por tempo medido, o movimento de 10 s pesa muito
    // menos que o repouso de 300 s.
    const curta = { ...movimento(0), epoca_segundos: 10 };
    const longa = { ...leitura(5), epoca_segundos: 300 };
    const m = calcularMetricas([curta, longa]);
    expect(m.fracaoEmMovimento!).toBeLessThan(0.1);
  });

  it("sem leitura nenhuma, a proporcao e null e nao zero", () => {
    // Zero afirmaria "voce nao se mexeu"; a ausencia de medicao nao afirma.
    expect(calcularMetricas([]).fracaoEmMovimento).toBeNull();
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

// --- media do repouso (DASH-07) -----------------------------------------
//
// O card do painel diz "media do desvio do repouso", mas a media incluia os
// eventos de movimento. Com um evento a diferenca e pequena; numa noite real,
// com dezenas, o numero vira uma mistura que nao e nem linha de base nem
// medida de movimento.

describe("intensidadeMedia considera apenas o repouso", () => {
  /** Leitura com a intensidade pedida, acima ou abaixo do repouso. */
  function leitura(minuto: number, desvio: number, status: string): LeituraSono {
    return {
      created_at: `2026-08-24T17:${String(minuto).padStart(2, "0")}:00Z`,
      movimento_total: GRAVIDADE + desvio,
      temp: 21,
      status,
    };
  }

  it("um evento de movimento nao levanta a linha de base", () => {
    // Numeros da primeira coleta com hardware real (2026-08-24): repouso em
    // ~0,85 por causa do vies do sensor, e um evento em 2,51.
    const leituras = [
      leitura(1, 0.85, "Repouso"),
      leitura(2, 0.85, "Repouso"),
      leitura(3, 0.85, "Repouso"),
      leitura(4, 2.51, "Movimento"),
    ];
    // Media de tudo daria 1,26 — acima do proprio limiar, o que seria absurdo
    // para um numero rotulado como "repouso".
    expect(calcularMetricas(leituras).intensidadeMedia).toBeCloseTo(0.85, 2);
  });

  it("sem nenhuma leitura de repouso, devolve null em vez de zero", () => {
    // Zero afirmaria uma linha de base que nunca foi medida.
    const so = [leitura(1, 2.5, "Movimento"), leitura(2, 3.1, "Movimento")];
    expect(calcularMetricas(so).intensidadeMedia).toBeNull();
  });

  it("le o rotulo do dispositivo, nao recalcula o limiar", () => {
    // Intensidade acima de 1,2 mas rotulada como Repouso pelo aparelho: o
    // painel obedece o rotulo (contrato, secao 2.2).
    const leituras = [leitura(1, 0.5, "Repouso"), leitura(2, 2.0, "Repouso")];
    expect(calcularMetricas(leituras).intensidadeMedia).toBeCloseTo(1.25, 2);
  });

  it("aceita o rotulo legado de movimento", () => {
    const leituras = [
      leitura(1, 0.85, "Repouso"),
      leitura(2, 5.0, "Movimento Detectado!"),
    ];
    expect(calcularMetricas(leituras).intensidadeMedia).toBeCloseTo(0.85, 2);
  });
});

// --- lacunas na serie do grafico (DASH-09) -------------------------------
//
// O eixo do grafico e categorico: cada leitura ocupa a mesma largura,
// independentemente do tempo entre elas. Um buraco de duas horas ficava
// visualmente identico a dez segundos — foi assim que a tela deixou de
// mostrar que a coleta tinha caido.

describe("prepararSerie marca onde faltou medicao", () => {
  it("sem cobertura, comporta-se como antes", () => {
    // A demo gera serie continua e nao passa cobertura.
    const s = prepararSerie([leitura(0), leitura(1), leitura(2)]);
    expect(s).toHaveLength(3);
    expect(s.every((p) => !p.lacuna)).toBe(true);
  });

  it("insere um ponto sintetico no buraco", () => {
    const leituras = [leitura(0), leitura(1), leitura(107), leitura(108)];
    const m = calcularMetricas(leituras);
    const s = prepararSerie(leituras, m.cobertura);

    const lacunas = s.filter((p) => p.lacuna);
    expect(lacunas).toHaveLength(1);
    expect(lacunas[0].intensidade).toBeNull();
    expect(lacunas[0].duracaoDaLacunaMs!).toBeGreaterThan(60 * MINUTO);
  });

  it("a lacuna fica ENTRE as leituras que a cercam, e nao no fim", () => {
    const leituras = [leitura(0), leitura(1), leitura(107), leitura(108)];
    const m = calcularMetricas(leituras);
    const s = prepararSerie(leituras, m.cobertura);

    const i = s.findIndex((p) => p.lacuna);
    expect(i).toBeGreaterThan(0);
    expect(i).toBeLessThan(s.length - 1);
  });

  it("medicao continua nao ganha lacuna nenhuma", () => {
    const leituras = [];
    for (let i = 0; i <= 6; i++) leituras.push(leitura(i));
    const m = calcularMetricas(leituras);
    expect(prepararSerie(leituras, m.cobertura).some((p) => p.lacuna)).toBe(false);
  });
});
