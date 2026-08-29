import { describe, expect, it } from "vitest";

import {
  agruparEmSessoes,
  cadenciaMedianaMs,
  calcularCobertura,
  fracaoEmMovimento,
  avaliarCobertura,
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


// --- DASH-11: duas perguntas diferentes ----------------------------------
//
// A primeira tentativa de conserto tratou "quanto foi medido?" e "o aparelho
// parou?" como uma pergunta so, e errou de tres maneiras. Cada bloco abaixo
// trava uma delas, com o cenario que a produziu na tela.

/** Serie sintetica com intervalo e epoca controlados. */
function serie(opcoes: {
  n: number;
  intervaloMs: number;
  epoca?: number | null;
  jitterMs?: number;
  movimentoEm?: (i: number) => boolean;
}): LeituraSono[] {
  const { n, intervaloMs, epoca = null, jitterMs = 0, movimentoEm = () => false } = opcoes;
  const lista: LeituraSono[] = [];
  let t = 0;
  for (let i = 0; i < n; i++) {
    // Jitter deterministico: teste que sorteia numero nao serve de regressao.
    t += intervaloMs + (jitterMs > 0 ? (i * 137) % jitterMs : 0);
    const l: LeituraSono = {
      created_at: new Date(BASE + t).toISOString(),
      movimento_total: GRAVIDADE + (movimentoEm(i) ? 5 : 0.2),
      temp: null,
      status: movimentoEm(i) ? "Movimento" : "Repouso",
    };
    if (epoca !== null) l.epoca_segundos = epoca;
    lista.push(l);
  }
  return lista;
}

describe("jitter de rede nao e o aparelho parar", () => {
  it("uma captacao de 8 h de celular com latencia e UMA sessao, nao centenas", () => {
    // O defeito: cada leitura cobre exatamente uma cadencia para tras, e a
    // cadencia e a MEDIANA — logo metade dos intervalos e maior que ela, e
    // toda diferenca virava lacuna. Cortando sessao em toda lacuna, o
    // resultado medido foi 960 leituras -> 960 "sessoes", e o painel abria
    // mostrando a ultima, com UMA leitura. Uma noite inteira medida virava
    // uma tela vazia.
    const leituras = serie({ n: 960, intervaloMs: 30_000, epoca: 30, jitterMs: 1500 });

    expect(agruparEmSessoes(leituras)).toHaveLength(1);
    expect(calcularCobertura(leituras).interrupcoes).toHaveLength(0);
  });

  it("e a maior pausa dessa noite e a noite inteira, nao 30 segundos", () => {
    // Este e o achado mais grave da segunda revisao, e ele reverte uma decisao
    // da primeira: medir a pausa sobre os trechos de COBERTURA parece o mais
    // rigoroso e produz absurdo. Com a cobertura picotada em 960 pedacos de
    // 30 s, a maior pausa POSSIVEL passa a ser 30 s — e a tela dizia
    // "Maior pausa: 30s" para 8h11m sem um unico rotulo de movimento.
    const leituras = serie({ n: 960, intervaloMs: 30_000, epoca: 30, jitterMs: 1500 });
    const pausa = pausaDe(leituras)!;

    expect(pausa).toBeGreaterThan(8 * 60 * MIN);
    // A pausa nao pode exceder a propria captacao.
    const sessao = agruparEmSessoes(leituras)[0];
    expect(pausa).toBeLessThanOrEqual(sessao.fim - sessao.inicio);
  });

  it("o mesmo vale sem epoca declarada, com a cadencia inferida", () => {
    const leituras = serie({ n: 200, intervaloMs: 10_000, jitterMs: 900 });
    expect(agruparEmSessoes(leituras)).toHaveLength(1);
  });

  it("mas o aparelho ter parado continua separando sessoes", () => {
    // A correcao nao pode desfazer o DASH-09: 105 min de silencio com
    // cadencia de 1 min sao 105 leituras perdidas.
    const leituras = [leitura(0), leitura(1), leitura(107), leitura(108)];
    expect(calcularCobertura(leituras).interrupcoes).toHaveLength(1);
    expect(agruparEmSessoes(leituras)).toHaveLength(2);
    // E a pausa nao pode atravessar o silencio.
    expect(pausaDe(leituras)!).toBeLessThan(10 * MIN);
  });

  it("tres intervalos de silencio separam; dois nao", () => {
    // O criterio: ao menos duas leituras esperadas nao chegaram. Uma leitura
    // perdida e soluco de rede — o app descarta a epoca sem amostra e nao
    // regrava envio que falhou, entao intervalo dobrado e operacao normal.
    const uma = serie({ n: 30, intervaloMs: 30_000, epoca: 30 });
    const comSoluco = [...uma];
    comSoluco.splice(15, 1); // uma leitura some -> intervalo dobra
    expect(agruparEmSessoes(comSoluco)).toHaveLength(1);

    const comParada = [...uma];
    comParada.splice(15, 3); // tres somem -> intervalo quadruplica
    expect(agruparEmSessoes(comParada)).toHaveLength(2);
  });

  it("NAO HA PENHASCO: envio a cada 2x a epoca continua sendo uma captacao", () => {
    // O filtro por TAMANHO DA LACUNA tinha um penhasco exatamente aqui: com
    // epoca de 30 s e envio a cada 60 s, cada buraco tem exatos 30 s e o
    // filtro voltava a cortar tudo — 120 leituras viravam 120 "sessoes".
    // Um segundo de diferenca separava "uma captacao" de "cento e vinte".
    for (const intervalo of [59_000, 60_000, 61_000, 90_000]) {
      const l = serie({ n: 120, intervaloMs: intervalo, epoca: 30 });
      expect(agruparEmSessoes(l)).toHaveLength(1);
    }
  });
});

describe("avaliarCobertura — a decisao de avisar", () => {
  it("PERDA SISTEMATICA APARECE, mesmo sem buraco grande nenhum", () => {
    // O segundo defeito da primeira tentativa: ela trocou o gatilho de "perda
    // real" para "tamanho dos buracos". Um dispositivo que resume 30 s e envia
    // a cada 45 s perde 33% da janela em buracos de 15 s — pequenos demais
    // para qualquer filtro de tamanho. A tela mostrava captacao limpa, sem
    // aviso, com um terco da janela nao medida.
    const l = serie({ n: 120, intervaloMs: 45_000, epoca: 30 });
    const c = calcularCobertura(l);

    expect(c.interrupcoes).toHaveLength(0);
    expect(c.tempoCobertoMs / c.janelaMs).toBeLessThan(0.7);

    const aviso = avaliarCobertura(c)!;
    expect(aviso).not.toBeNull();
    expect(aviso.perdaDistribuida).toBe(true);
    expect(aviso.interrupcoes).toHaveLength(0);
  });

  it("o tempo anunciado e a perda REAL, nao a soma dos buracos citaveis", () => {
    // A frase da tela e "Faltou medicao em X". Anunciar so o que cabe nas
    // interrupcoes subdeclarava o que faltou — afirmacao falsa na direcao que
    // a regra do projeto proibe.
    const l = serie({ n: 120, intervaloMs: 45_000, epoca: 30 });
    const c = calcularCobertura(l);
    const aviso = avaliarCobertura(c)!;

    expect(aviso.perdidoMs).toBe(c.janelaMs - c.tempoCobertoMs);
    expect(aviso.maiorInterrupcaoMs).toBe(0);
  });

  it("jitter sozinho nao dispara aviso", () => {
    // 5% de folga: arredondamento e latencia nao sao perda que mude a leitura
    // dos numeros.
    const l = serie({ n: 960, intervaloMs: 30_000, epoca: 30, jitterMs: 1500 });
    expect(avaliarCobertura(calcularCobertura(l))).toBeNull();
  });

  it("cobertura perfeita nao dispara aviso", () => {
    const l = serie({ n: 50, intervaloMs: 60_000, epoca: 60 });
    expect(avaliarCobertura(calcularCobertura(l))).toBeNull();
  });

  it("o aparelho que parou e citavel, e o aviso o cita", () => {
    const l = [leitura(0), leitura(1), leitura(107), leitura(108)];
    const aviso = avaliarCobertura(calcularCobertura(l))!;

    expect(aviso.interrupcoes).toHaveLength(1);
    expect(aviso.maiorInterrupcaoMs).toBe(105 * MIN);
    expect(aviso.perdaDistribuida).toBe(false);
  });

  it("janela de duracao zero nao produz aviso", () => {
    expect(avaliarCobertura(calcularCobertura([]))).toBeNull();
    expect(avaliarCobertura(calcularCobertura([leitura(0)]))).toBeNull();
  });
});

describe("movimento e intervalo, nao instante", () => {
  it("uma sessao 100% em movimento nao pode ter pausa do tamanho dela", () => {
    // A contradicao que a versao anterior mostrava na tela: uma unica leitura
    // de movimento com epoca de 60 s dava, ao mesmo tempo, "100% em
    // movimento" e "Maior pausa: 1m 0s" — no mesmo minuto medido. A causa era
    // tratar o movimento como um PONTO no fim do trecho que ele resume.
    const l = serie({ n: 1, intervaloMs: 0, epoca: 60, movimentoEm: () => true });
    expect(fracaoDe(l)).toBe(1);
    expect(pausaDe(l)).toBe(0);
  });

  it("a pausa desconta o periodo que a leitura de movimento resume", () => {
    // Seis leituras de 1 em 1 min, epoca de 60 s: a captacao vai de -1 min
    // (a primeira resume o minuto anterior a ela) ate 5 min. O movimento em
    // 5 min cobre [4, 5], entao a pausa medida e [-1, 4] = 5 min.
    //
    // Tratando o movimento como PONTO, como antes, ele nao descontaria nada e
    // a pausa seria a captacao inteira, 6 min.
    const l = serie({
      n: 6, intervaloMs: 60_000, epoca: 60, movimentoEm: (i) => i === 5,
    });
    expect(pausaDe(l)).toBe(5 * MIN);
    expect(pausaDe(l)!).toBeLessThan(calcularCobertura(l).janelaMs);
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
    const l: LeituraSono[] = [
      { ...leitura(0), created_at: new Date(BASE + 100_000).toISOString(), epoca_segundos: 1 },
      { ...leitura(0), created_at: new Date(BASE + 1_000_000).toISOString(), epoca_segundos: 950 },
    ];
    const c = calcularCobertura(l);
    expect(c.trechos).toHaveLength(1);
    expect(c.trechos[0].inicio).toBe(BASE + 50_000);
    expect(c.tempoCobertoMs).toBe(950_000);
  });

  it("leitura duplicada nao e contada duas vezes na fracao", () => {
    // Numerador e denominador saem da mesma uniao. Antes, o denominador
    // somava pesos brutos (90 s) e o numerador vinha da uniao (60 s): a tela
    // dizia 33% de movimento sobre 60 s medidos, com 30 s contados em dobro.
    const emT = (ms: number, mov: boolean): LeituraSono => ({
      created_at: new Date(BASE + ms).toISOString(),
      movimento_total: GRAVIDADE + (mov ? 5 : 0.2),
      temp: null,
      status: mov ? "Movimento" : "Repouso",
      epoca_segundos: 30,
    });
    const l = [emT(0, false), emT(0, true), emT(30_000, false)];
    const c = calcularCobertura(l);
    expect(c.tempoCobertoMs).toBe(60_000);
    expect(fracaoDe(l)).toBeCloseTo(0.5, 5);
  });

  it("a pausa nao muda se os trechos de movimento chegarem fora de ordem", () => {
    // `subtrair` exige entrada unida e ordenada, e as duas funcoes sao
    // exportadas. Une por dentro em vez de confiar em quem chama.
    const l = serie({
      n: 10, intervaloMs: 60_000, epoca: 60, movimentoEm: (i) => i === 3 || i === 7,
    });
    const c = calcularCobertura(l);
    const mov = trechosDeMovimento(l, ehMovimento);
    expect(maiorPausaCobertaMs(c, [...mov].reverse())).toBe(maiorPausaCobertaMs(c, mov));
  });

  it("created_at ausente e descartado, e nao vira 1970", () => {
    // `new Date(null)` da 0, nao NaN: a guarda de NaN nao pegava, e uma linha
    // assim esticava a janela por decadas.
    const podre = { ...leitura(0), created_at: null } as unknown as LeituraSono;
    const c = calcularCobertura([podre, leitura(1), leitura(2)]);
    expect(c.janelaMs).toBeLessThan(10 * MIN);
  });
});
