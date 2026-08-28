import { describe, expect, it } from "vitest";

import {
  agruparEmSessoes,
  cadenciaMedianaMs,
  calcularCobertura,
  fracaoEmMovimento,
  maiorPausaCobertaMs,
} from "./cobertura";
import { GRAVIDADE, ehMovimento, type LeituraSono } from "../types/sleep";

const BASE = Date.UTC(2026, 7, 25, 14, 0, 0);
const MIN = 60_000;

function leitura(minuto: number, opcoes: { movimento?: boolean; epoca?: number | null } = {}) {
  const { movimento = false, epoca = null } = opcoes;
  const l: LeituraSono = {
    created_at: new Date(BASE + minuto * MIN).toISOString(),
    movimento_total: GRAVIDADE + (movimento ? 5 : 0.2),
    temp: null,
    status: movimento ? "Movimento" : "Repouso",
  };
  if (epoca !== null) l.epoca_segundos = epoca;
  return l;
}

describe("cadenciaMedianaMs", () => {
  it("mediana, e nao media — um buraco nao pode virar cadencia normal", () => {
    // Leituras de minuto em minuto, com um buraco de 2 horas no meio.
    // Media daria ~24 min e o buraco pareceria cobertura normal.
    const leituras = [
      leitura(0), leitura(1), leitura(2), leitura(3), leitura(4),
      leitura(124), leitura(125), leitura(126),
    ];
    expect(cadenciaMedianaMs(leituras)).toBe(1 * MIN);
  });

  it("sem duas leituras nao ha intervalo a medir", () => {
    // Inventar uma cadencia aqui seria a mesma classe de erro que este
    // modulo existe para corrigir.
    expect(cadenciaMedianaMs([])).toBeNull();
    expect(cadenciaMedianaMs([leitura(0)])).toBeNull();
  });
});

describe("calcularCobertura", () => {
  it("epoca declarada tem precedencia sobre inferencia", () => {
    // O dispositivo dizendo "resumo 30 s" e informacao, nao suposicao.
    const c = calcularCobertura([leitura(0, { epoca: 30 }), leitura(1, { epoca: 30 })]);
    expect(c.cadenciaInferida).toBe(false);
    expect(c.tempoCobertoMs).toBe(60_000); // dois trechos de 30 s
  });

  it("sem epoca, infere e AVISA que inferiu", () => {
    const c = calcularCobertura([leitura(0), leitura(1), leitura(2)]);
    expect(c.cadenciaInferida).toBe(true);
  });

  it("encontra a lacuna real da coleta de 25/08", () => {
    // O caso que produziu "Maior pausa: 1h47m" na tela.
    const leituras = [leitura(0), leitura(1), leitura(107), leitura(108)];
    const c = calcularCobertura(leituras);

    expect(c.lacunas).toHaveLength(1);
    const lacuna = c.lacunas[0];
    expect(lacuna.fim - lacuna.inicio).toBe(105 * MIN);
  });

  it("une trechos que se tocam", () => {
    const c = calcularCobertura([
      leitura(0, { epoca: 60 }), leitura(1, { epoca: 60 }), leitura(2, { epoca: 60 }),
    ]);
    expect(c.trechos).toHaveLength(1);
    expect(c.lacunas).toHaveLength(0);
  });

  it("sessao vazia nao inventa cobertura", () => {
    const c = calcularCobertura([]);
    expect(c.trechos).toEqual([]);
    expect(c.tempoCobertoMs).toBe(0);
  });
});

describe("maiorPausaCobertaMs — o defeito central", () => {
  it("BURACO DE COLETA NAO E PAUSA", () => {
    // Este e o teste que existe por causa do defeito real. Leituras nos
    // minutos 0-1 e 107-108, sem nada no meio. A versao anterior respondia
    // 105 min de "pausa"; a resposta certa e ~1 min, que e o maior trecho
    // MEDIDO sem movimento.
    const leituras = [leitura(0), leitura(1), leitura(107), leitura(108)];
    const c = calcularCobertura(leituras);
    const pausa = maiorPausaCobertaMs(c, []);

    expect(pausa).not.toBeNull();
    expect(pausa!).toBeLessThan(5 * MIN);
    expect(pausa!).toBeLessThan(105 * MIN);
  });

  it("conta a pausa dentro do trecho medido", () => {
    // Medicao continua de 0 a 10, com movimento em 2 e em 4.
    // A maior pausa coberta e de 4 ate 10.
    const leituras = [];
    for (let m = 0; m <= 10; m++) leituras.push(leitura(m, { movimento: m === 2 || m === 4 }));

    const c = calcularCobertura(leituras);
    const movimentos = leituras
      .filter((l) => ehMovimento(l.status))
      .map((l) => new Date(l.created_at).getTime());

    const pausa = maiorPausaCobertaMs(c, movimentos);
    expect(pausa).toBeCloseTo(6 * MIN, -3);
  });

  it("sem cobertura devolve null, e nao zero", () => {
    // Zero afirmaria "voce nao teve pausa nenhuma", que e uma medida.
    // Ausencia de medicao nao e.
    expect(maiorPausaCobertaMs(calcularCobertura([]), [])).toBeNull();
  });
});

describe("fracaoEmMovimento — por tempo, nao por amostra", () => {
  it("uma leitura longa pesa mais que uma curta", () => {
    // Duas leituras: 10 s em movimento e 300 s em repouso.
    // Por contagem daria 50%. Por tempo, 3,2%.
    const l = [
      { ...leitura(0, { movimento: true }), epoca_segundos: 10 },
      { ...leitura(5), epoca_segundos: 300 },
    ];
    const f = fracaoEmMovimento(l, ehMovimento)!;
    expect(f).toBeCloseTo(10 / 310, 3);
    expect(f).toBeLessThan(0.5);
  });

  it("com epocas iguais, coincide com a contagem", () => {
    const l = [
      leitura(0, { movimento: true, epoca: 30 }),
      leitura(1, { epoca: 30 }),
      leitura(2, { epoca: 30 }),
      leitura(3, { epoca: 30 }),
    ];
    expect(fracaoEmMovimento(l, ehMovimento)).toBeCloseTo(0.25, 5);
  });

  it("sessao vazia devolve null", () => {
    expect(fracaoEmMovimento([], ehMovimento)).toBeNull();
  });
});

// --- sessoes de captacao (DASH-10) ---------------------------------------

describe("agruparEmSessoes", () => {
  it("medicao continua e UMA sessao", () => {
    const l = [];
    for (let m = 0; m <= 10; m++) l.push(leitura(m));
    expect(agruparEmSessoes(l)).toHaveLength(1);
  });

  it("o buraco separa sessoes", () => {
    // O caso real de 25/08: leituras em 0-1, buraco, leituras em 107-108.
    // O painel mostrava isso como uma janela unica "das 14h as 16h".
    const s = agruparEmSessoes([leitura(0), leitura(1), leitura(107), leitura(108)]);
    expect(s).toHaveLength(2);
    expect(s[0].leituras).toHaveLength(2);
    expect(s[1].leituras).toHaveLength(2);
  });

  it("as sessoes vem em ordem, da mais antiga para a mais recente", () => {
    const s = agruparEmSessoes([leitura(0), leitura(1), leitura(107), leitura(108)]);
    expect(s[0].fim).toBeLessThan(s[1].inicio);
  });

  it("cada leitura cai em exatamente uma sessao", () => {
    const leituras = [leitura(0), leitura(1), leitura(107), leitura(108)];
    const s = agruparEmSessoes(leituras);
    const total = s.reduce((n, x) => n + x.leituras.length, 0);
    expect(total).toBe(leituras.length);
  });

  it("sem leitura nenhuma, nao ha sessao", () => {
    // E nao "uma sessao vazia", que produziria metricas de nada.
    expect(agruparEmSessoes([])).toEqual([]);
  });

  it("uma leitura sozinha ainda e uma sessao", () => {
    expect(agruparEmSessoes([leitura(0)])).toHaveLength(1);
  });
});

describe("o recorte muda o que o painel afirma", () => {
  it("a ultima sessao tem janela propria, e nao a soma de tudo", () => {
    // O caso real: o painel dizia "14:08 — 16:06", 1h57m de "captacao",
    // quando as leituras eram dois punhados de ~1 min separados por um
    // buraco de 105 min. A ultima sessao dura ~1 min, e e isso que a tela
    // deve mostrar por padrao.
    const leituras = [leitura(0), leitura(1), leitura(107), leitura(108)];
    const sessoes = agruparEmSessoes(leituras);
    const ultima = sessoes[sessoes.length - 1];

    const janelaDaUltima = ultima.fim - ultima.inicio;
    const janelaDeTudo = calcularCobertura(leituras).janelaMs;

    expect(janelaDeTudo).toBeGreaterThan(100 * 60_000);
    expect(janelaDaUltima).toBeLessThan(10 * 60_000);
  });

  it("dentro de uma sessao nao ha lacuna", () => {
    // E a definicao: sessao E trecho coberto. Se sobrasse lacuna dentro,
    // o agrupamento estaria errado.
    const leituras = [leitura(0), leitura(1), leitura(107), leitura(108)];
    for (const s of agruparEmSessoes(leituras)) {
      expect(calcularCobertura(s.leituras).lacunas).toHaveLength(0);
    }
  });
});
