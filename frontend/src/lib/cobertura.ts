import type { LeituraSono } from "../types/sleep";

/**
 * Onde houve medicao, e onde nao houve (DASH-09).
 *
 * ── O DEFEITO QUE ISTO CONSERTA ─────────────────────────────────────────
 *
 * O painel tratava AUSENCIA DE DADO como DADO. `maiorIntervaloSemMovimento`
 * conhecia apenas os instantes de movimento e as bordas da janela — nao tinha
 * como saber se houve leitura no meio. Duas horas de silencio e duas horas de
 * repouso continuo eram identicas para ele.
 *
 * Numa coleta real de 25/08/2026 isso produziu, na tela: **"Maior pausa: 1h47m
 * sem eventos de movimento"** — quando o que houve foi 1h47m SEM LEITURA
 * NENHUMA. Num aplicativo de sono esse defeito e fatal: a noite em que o
 * sensor caiu vira sono perfeito.
 *
 * O mesmo vale para o percentual: "45% em movimento" era 9 eventos divididos
 * por 20 leituras. Com amostragem irregular, as 20 leituras cobriam ~3 minutos
 * de uma janela de 117. O numero nao significava nada.
 *
 * ── COMO SE SABE O QUE FOI COBERTO ──────────────────────────────────────
 *
 * Duas fontes, nesta ordem:
 *
 * 1. **`epoca_segundos`, quando a leitura declara.** E o caso do celular: a
 *    linha diz "eu resumo 30 segundos". Isso e informacao do dispositivo, nao
 *    suposicao nossa.
 *
 * 2. **Cadencia inferida, quando nao declara.** E o caso do ESP32 e das linhas
 *    antigas. Usamos a MEDIANA dos intervalos entre leituras consecutivas —
 *    mediana, e nao media, porque um unico buraco de duas horas puxaria a
 *    media e faria o buraco parecer cobertura normal.
 *
 * A segunda e inferencia, e a interface precisa dizer isso. O que NAO se faz e
 * assumir cobertura total no silencio.
 *
 * ── UMA PERGUNTA QUE ESTE MODULO NAO RESOLVE ────────────────────────────
 *
 * Para um ESP32 com Wake-on-Motion (`HW-03`, ainda nao construido), o silencio
 * teria significado oposto: dormir sem acordar E a evidencia de repouso. Aqui
 * o silencio e tratado como ausencia de informacao, que e o correto para
 * amostragem regular — que e como os dois dispositivos funcionam hoje.
 *
 * Quando o wake-on-motion existir, isto precisa ser revisto junto com o
 * `DATA-02` (modelo de amostragem), que segue em aberto.
 */

/** Um intervalo continuo, em milissegundos desde a epoca. */
export type Trecho = { inicio: number; fim: number };

export type Cobertura = {
  /** Trechos em que houve medicao, em ordem e sem sobreposicao. */
  trechos: Trecho[];
  /** Soma da duracao dos trechos cobertos. */
  tempoCobertoMs: number;
  /** Do inicio da primeira leitura ao fim da ultima. */
  janelaMs: number;
  /** Trechos SEM medicao dentro da janela. */
  lacunas: Trecho[];
  /** `true` quando a cadencia foi inferida, e nao declarada pelas leituras. */
  cadenciaInferida: boolean;
};

/** Leitura com instante ja convertido, em ordem crescente. */
type Datada = { leitura: LeituraSono; t: number };

function datadas(leituras: LeituraSono[]): Datada[] {
  return leituras
    .map((leitura) => ({ leitura, t: new Date(leitura.created_at).getTime() }))
    .filter(({ t }) => !Number.isNaN(t))
    .sort((a, b) => a.t - b.t);
}

/**
 * Mediana dos intervalos entre leituras consecutivas.
 *
 * Mediana, e nao media, de proposito: um buraco de duas horas no meio de
 * leituras de 10 em 10 segundos levaria a media para minutos, e o buraco
 * passaria a parecer cadencia normal. A mediana ignora o extremo.
 *
 * Devolve `null` com menos de duas leituras — nao ha intervalo a medir, e
 * inventar um seria a mesma classe de erro que este modulo existe para
 * corrigir.
 */
export function cadenciaMedianaMs(leituras: LeituraSono[]): number | null {
  const lista = datadas(leituras);
  if (lista.length < 2) return null;

  const intervalos: number[] = [];
  for (let i = 1; i < lista.length; i++) intervalos.push(lista[i].t - lista[i - 1].t);
  intervalos.sort((a, b) => a - b);

  const meio = Math.floor(intervalos.length / 2);
  return intervalos.length % 2 === 1
    ? intervalos[meio]
    : (intervalos[meio - 1] + intervalos[meio]) / 2;
}

/**
 * Quanto tempo cada leitura cobre, em ms.
 *
 * `epoca_segundos` tem precedencia: e o dispositivo dizendo quanto resumiu.
 */
function coberturaDaLeitura(leitura: LeituraSono, cadenciaMs: number | null): number {
  const epoca = leitura.epoca_segundos;
  if (typeof epoca === "number" && epoca > 0) return epoca * 1000;
  return cadenciaMs ?? 0;
}

/**
 * Onde houve medicao.
 *
 * Cada leitura cobre o intervalo que TERMINA no seu instante — a leitura
 * resume o periodo anterior a ela, nao o posterior. Trechos que se tocam sao
 * unidos.
 */
export function calcularCobertura(leituras: LeituraSono[]): Cobertura {
  const lista = datadas(leituras);
  const vazio: Cobertura = {
    trechos: [], tempoCobertoMs: 0, janelaMs: 0, lacunas: [], cadenciaInferida: false,
  };
  if (lista.length === 0) return vazio;

  const cadencia = cadenciaMedianaMs(leituras);
  const algumaDeclara = lista.some(
    ({ leitura }) => typeof leitura.epoca_segundos === "number" && leitura.epoca_segundos > 0,
  );

  const brutos: Trecho[] = lista.map(({ leitura, t }) => {
    const dura = coberturaDaLeitura(leitura, cadencia);
    return { inicio: t - dura, fim: t };
  });

  // Une o que se toca ou se sobrepoe.
  const trechos: Trecho[] = [];
  for (const bruto of brutos) {
    const ultimo = trechos[trechos.length - 1];
    if (ultimo && bruto.inicio <= ultimo.fim) {
      ultimo.fim = Math.max(ultimo.fim, bruto.fim);
    } else {
      trechos.push({ ...bruto });
    }
  }

  const janelaInicio = trechos[0].inicio;
  const janelaFim = trechos[trechos.length - 1].fim;

  const lacunas: Trecho[] = [];
  for (let i = 1; i < trechos.length; i++) {
    lacunas.push({ inicio: trechos[i - 1].fim, fim: trechos[i].inicio });
  }

  return {
    trechos,
    tempoCobertoMs: trechos.reduce((soma, t) => soma + (t.fim - t.inicio), 0),
    janelaMs: janelaFim - janelaInicio,
    lacunas,
    cadenciaInferida: !algumaDeclara && cadencia !== null,
  };
}

/**
 * Maior periodo sem movimento **dentro do que foi medido**.
 *
 * A diferenca para a versao anterior e toda aqui: um trecho so entra na conta
 * se houve medicao nele. Buraco de coleta nao vira pausa.
 *
 * Devolve `null` quando nao ha cobertura — e nao zero. Zero afirmaria "voce
 * nao teve pausa nenhuma", que e uma medida; a ausencia de medicao nao e.
 */
export function maiorPausaCobertaMs(
  cobertura: Cobertura,
  instantesDeMovimento: number[],
): number | null {
  if (cobertura.trechos.length === 0) return null;

  let maior = 0;
  for (const trecho of cobertura.trechos) {
    const dentro = instantesDeMovimento
      .filter((t) => t >= trecho.inicio && t <= trecho.fim)
      .sort((a, b) => a - b);

    const marcos = [trecho.inicio, ...dentro, trecho.fim];
    for (let i = 1; i < marcos.length; i++) {
      maior = Math.max(maior, marcos[i] - marcos[i - 1]);
    }
  }
  return maior;
}

/**
 * Fracao do tempo MEDIDO em que houve movimento, de 0 a 1.
 *
 * Por tempo, e nao por contagem de amostra. Com amostragem irregular, "9
 * eventos em 20 leituras = 45%" nao significa nada: as 20 leituras podiam
 * cobrir tres minutos de uma janela de duas horas.
 *
 * Cada leitura pesa o quanto ela cobre. `null` sem cobertura.
 */
export function fracaoEmMovimento(
  leituras: LeituraSono[],
  ehMovimento: (status: string | null | undefined) => boolean,
): number | null {
  const lista = datadas(leituras);
  if (lista.length === 0) return null;

  const cadencia = cadenciaMedianaMs(leituras);
  let total = 0;
  let movimento = 0;
  for (const { leitura } of lista) {
    const peso = coberturaDaLeitura(leitura, cadencia);
    total += peso;
    if (ehMovimento(leitura.status)) movimento += peso;
  }
  return total > 0 ? movimento / total : null;
}

/**
 * Uma sessao de captacao: um trecho continuo de medicao (DASH-10).
 *
 * ── POR QUE "SESSAO" E NAO "NOITE" ──────────────────────────────────────
 *
 * A revisao de produto apontou, com razao, que falta o conceito de recorte:
 * o painel mostrava uma janela continua "das 14h as 16h" — dado diurno,
 * espalhado, sem inicio nem fim que signifiquem algo para quem olha.
 *
 * O agrupamento natural seria "a noite de 27/08". Mas isso AFIRMA que o dado
 * e sono, e o escopo declarado do projeto diz o contrario: registra movimento
 * durante o repouso, sem estadiamento nem diagnostico. Chamar de "noite" seria
 * o mesmo tipo de afirmacao indevida que este modulo existe para eliminar.
 *
 * "Sessao de captacao" e neutro e verdadeiro: e o periodo em que o aparelho
 * de fato mediu. Se um dia o projeto decidir afirmar noites, isso vira decisao
 * de escopo (e depende do `DATA-02`), nao de tela.
 *
 * O criterio e o mesmo da cobertura: um buraco separa sessoes. Nao ha
 * heuristica nova aqui — a sessao E o trecho coberto.
 */
export type Sessao = {
  inicio: number;
  fim: number;
  leituras: LeituraSono[];
};

export function agruparEmSessoes(leituras: LeituraSono[]): Sessao[] {
  const cobertura = calcularCobertura(leituras);
  if (cobertura.trechos.length === 0) return [];

  const lista = datadas(leituras);

  return cobertura.trechos
    .map((trecho) => ({
      inicio: trecho.inicio,
      fim: trecho.fim,
      leituras: lista
        .filter(({ t }) => t >= trecho.inicio && t <= trecho.fim)
        .map(({ leitura }) => leitura),
    }))
    // Trecho sem leitura nao e sessao. Nao deveria acontecer — os trechos sao
    // construidos A PARTIR das leituras — mas uma sessao vazia produziria
    // metricas de nada, que e o defeito que o DASH-09 corrigiu.
    .filter((s) => s.leituras.length > 0);
}
