import { describe, expect, it } from "vitest";

import {
  agruparEmSessoes,
  cadenciaMedianaMs,
  calcularCobertura,
  fracaoEmMovimento,
  maiorPausaCobertaMs,
  trechosDeMovimento,
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

/** Atalhos: as duas metricas partem sempre da mesma cobertura e do mesmo
 *  conjunto de trechos de movimento — e o ponto do DASH-11. */
function pausaDe(leituras: LeituraSono[]) {
  return maiorPausaCobertaMs(
    calcularCobertura(leituras),
    trechosDeMovimento(leituras, ehMovimento),
  );
}
function fracaoDe(leituras: LeituraSono[]) {
  return fracaoEmMovimento(
    calcularCobertura(leituras),
    trechosDeMovimento(leituras, ehMovimento),
  );
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
    const pausa = pausaDe(leituras);

    expect(pausa).not.toBeNull();
    expect(pausa!).toBeLessThan(5 * MIN);
    expect(pausa!).toBeLessThan(105 * MIN);
  });

  it("conta a pausa dentro do trecho medido", () => {
    // Medicao continua de 0 a 10, com movimento em 2 e em 4.
    // A maior pausa coberta e de 4 ate 10.
    const leituras = [];
    for (let m = 0; m <= 10; m++) leituras.push(leitura(m, { movimento: m === 2 || m === 4 }));

    const pausa = pausaDe(leituras);
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
    const f = fracaoDe(l)!;
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
    expect(fracaoDe(l)).toBeCloseTo(0.25, 5);
  });

  it("sessao vazia devolve null", () => {
    expect(fracaoDe([])).toBeNull();
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

// --- DASH-11: o remedio nao pode ser pior que a doenca -------------------

/** Leitura em instante arbitrario (ms desde BASE), para simular jitter. */
function em(ms: number, opcoes: { movimento?: boolean; epoca?: number | null } = {}) {
  const { movimento = false, epoca = null } = opcoes;
  const l: LeituraSono = {
    created_at: new Date(BASE + ms).toISOString(),
    movimento_total: GRAVIDADE + (movimento ? 5 : 0.2),
    temp: null,
    status: movimento ? "Movimento" : "Repouso",
  };
  if (epoca !== null) l.epoca_segundos = epoca;
  return l;
}

describe("lacuna material — jitter de rede nao e buraco de coleta", () => {
  it("uma captacao de 8 h de celular com latencia e UMA sessao, nao centenas", () => {
    // O defeito: cada leitura cobre exatamente uma cadencia para tras, e a
    // cadencia e a MEDIANA — logo metade dos intervalos e maior que ela, e
    // toda diferenca virava lacuna. `agruparEmSessoes` cortava em cada uma.
    // Resultado medido antes da correcao: 960 leituras -> 476 "sessoes", e o
    // painel abria mostrando a ultima, com DUAS leituras. Uma noite inteira
    // medida virava uma tela vazia.
    const leituras: LeituraSono[] = [];
    let t = 0;
    for (let i = 0; i < 960; i++) {
      t += 30_000 + ((i * 137) % 1500); // jitter deterministico de 0 a 1,5 s
      leituras.push(em(t, { epoca: 30 }));
    }

    expect(agruparEmSessoes(leituras)).toHaveLength(1);
    expect(calcularCobertura(leituras).lacunasMateriais).toHaveLength(0);
  });

  it("o mesmo vale sem epoca declarada, com a cadencia inferida", () => {
    // O caso do ESP32: cadencia de 10 s com variacao de +-5%.
    const leituras: LeituraSono[] = [];
    let t = 0;
    for (let i = 0; i < 200; i++) {
      t += 10_000 + ((i * 91) % 900) - 450;
      leituras.push(em(t));
    }
    expect(agruparEmSessoes(leituras)).toHaveLength(1);
  });

  it("mas a leitura que de fato faltou continua sendo lacuna", () => {
    // Criterio: cabe ao menos uma cobertura tipica dentro do buraco. Aqui
    // faltam tres leituras seguidas, e isso PRECISA aparecer.
    const leituras: LeituraSono[] = [];
    let t = 0;
    for (let i = 0; i < 40; i++) {
      t += i === 20 ? 4 * 30_000 : 30_000;
      leituras.push(em(t, { epoca: 30 }));
    }

    const c = calcularCobertura(leituras);
    expect(c.lacunasMateriais).toHaveLength(1);
    expect(c.lacunasMateriais[0].fim - c.lacunasMateriais[0].inicio).toBe(3 * 30_000);
    expect(agruparEmSessoes(leituras)).toHaveLength(2);
  });

  it("a lacuna real de 25/08 continua separando sessoes", () => {
    // A correcao nao pode desfazer o DASH-09: 105 min de silencio com
    // cadencia de 1 min sao 105 leituras perdidas.
    const leituras = [leitura(0), leitura(1), leitura(107), leitura(108)];
    expect(calcularCobertura(leituras).lacunasMateriais).toHaveLength(1);
    expect(agruparEmSessoes(leituras)).toHaveLength(2);
  });
});

describe("movimento e intervalo, nao instante", () => {
  it("uma sessao 100% em movimento nao pode ter pausa do tamanho dela", () => {
    // A contradicao que a versao anterior mostrava na tela: uma unica leitura
    // de movimento com epoca de 60 s dava, ao mesmo tempo, "100% em
    // movimento" e "Maior pausa: 1m 0s" — no mesmo minuto medido. A causa era
    // tratar o movimento como um PONTO no fim do trecho que ele resume.
    const l = [em(0, { movimento: true, epoca: 60 })];
    expect(fracaoDe(l)).toBe(1);
    expect(pausaDe(l)).toBe(0);
  });

  it("a pausa desconta o periodo que a leitura de movimento resume", () => {
    // Seis leituras de 1 em 1 min, epoca de 60 s: a cobertura vai de -1 min
    // (a primeira resume o minuto anterior a ela) ate 5 min. O movimento em
    // 5 min cobre [4, 5], entao a pausa medida e [-1, 4] = 5 min.
    //
    // Tratando o movimento como PONTO, como antes, ele nao descontaria nada e
    // a pausa seria a cobertura inteira, 6 min.
    const l = [
      em(0, { epoca: 60 }),
      em(60_000, { epoca: 60 }),
      em(2 * MIN, { epoca: 60 }),
      em(3 * MIN, { epoca: 60 }),
      em(4 * MIN, { epoca: 60 }),
      em(5 * MIN, { movimento: true, epoca: 60 }),
    ];
    expect(pausaDe(l)).toBe(5 * MIN);
    expect(pausaDe(l)!).toBeLessThan(calcularCobertura(l).tempoCobertoMs);
  });
});

describe("guardas que a versao anterior nao tinha", () => {
  it("uma leitura sozinha sem epoca nao mede nada — pausa e null, nao zero", () => {
    // Sem segunda leitura nao ha cadencia a inferir, entao o trecho tem
    // duracao zero: ele EXISTE na lista mas nao cobre nada. A guarda antiga
    // olhava `trechos.length === 0` e devolvia 0 — a tela imprimia
    // "Maior pausa: 0s", que afirma nao ter havido pausa nenhuma.
    const l = [leitura(0)];
    const c = calcularCobertura(l);
    expect(c.trechos).toHaveLength(1);
    expect(c.tempoCobertoMs).toBe(0);
    expect(pausaDe(l)).toBeNull();
    expect(fracaoDe(l)).toBeNull();
  });

  it("basta UMA leitura sem epoca para a tela dizer que inferiu", () => {
    // Serie mista celular + ESP32. O `some` invertido da versao anterior
    // silenciava o aviso justamente aqui.
    const l = [
      leitura(0, { epoca: 30 }), leitura(1, { epoca: 30 }),
      leitura(2), leitura(3), leitura(4),
    ];
    expect(calcularCobertura(l).cadenciaInferida).toBe(true);
  });

  it("epoca variavel nao subestima a cobertura", () => {
    // Trechos ordenados pelo FIM podiam comecar fora de ordem, e a uniao
    // ingenua descartava o pedaco inicial do trecho mais longo.
    const c = calcularCobertura([
      em(100_000, { epoca: 1 }),
      em(1_000_000, { epoca: 950 }),
    ]);
    expect(c.trechos).toHaveLength(1);
    expect(c.trechos[0].inicio).toBe(BASE + 50_000);
    expect(c.tempoCobertoMs).toBe(950_000);
  });

  it("leitura duplicada nao e contada duas vezes na fracao", () => {
    // Numerador e denominador saem da mesma uniao. Antes, o denominador
    // somava pesos brutos (90 s) e o numerador vinha da uniao (60 s): a tela
    // dizia 33% de movimento sobre 60 s medidos, com 30 s contados em dobro.
    const l = [
      em(0, { epoca: 30 }),
      em(0, { movimento: true, epoca: 30 }),
      em(30_000, { epoca: 30 }),
    ];
    const c = calcularCobertura(l);
    expect(c.tempoCobertoMs).toBe(60_000);
    expect(fracaoDe(l)).toBeCloseTo(30_000 / 60_000, 5);
  });

  it("created_at ausente e descartado, e nao vira 1970", () => {
    // `new Date(null)` da 0, nao NaN: a guarda de NaN nao pegava, e uma linha
    // assim esticava a janela por decadas.
    const podre = { ...leitura(0), created_at: null } as unknown as LeituraSono;
    const c = calcularCobertura([podre, leitura(1), leitura(2)]);
    expect(c.janelaMs).toBeLessThan(10 * MIN);
  });
});
