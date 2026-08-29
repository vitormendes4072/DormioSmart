/**
 * Metricas derivadas das leituras do sensor.
 *
 * Tudo aqui e calculado a partir do que o dispositivo REALMENTE mede: instante
 * da leitura, magnitude da aceleracao e o rotulo repouso/movimento. Nao ha
 * estagio de sono, nao ha pontuacao, nao ha duracao de sono — o escopo do
 * projeto nao afirma nenhuma dessas coisas (ver ROADMAP.md).
 */
import {
  calcularCobertura,
  fracaoEmMovimento,
  maiorPausaCobertaMs,
  trechosDeMovimento,
  type Cobertura,
} from "./cobertura";
import { ehMovimento, intensidade, type LeituraSono } from "../types/sleep";

export type Janela = { inicio: Date; fim: Date };

export type Metricas = {
  /** Quantas leituras chegaram na janela. */
  totalLeituras: number;
  /** Quantas foram classificadas como movimento PELO DISPOSITIVO. */
  eventosDeMovimento: number;
  /** Primeiro e ultimo instante captado. Null quando nao ha leitura valida. */
  janela: Janela | null;
  /** Duracao da janela de captacao, em ms. */
  duracaoDaJanelaMs: number;
  /**
   * Maior intervalo continuo sem movimento **dentro do que foi medido**.
   *
   * E o indicador mais proximo de "repouso" que este dispositivo consegue
   * sustentar: ausencia prolongada de movimento. NAO e "tempo dormindo".
   *
   * ── CORRIGIDO NO DASH-09 ─────────────────────────────────────────────
   *
   * Ate aqui esta conta usava so os instantes de movimento e as bordas da
   * janela — nao sabia se houve LEITURA no meio. Numa coleta real de
   * 25/08/2026 isso pintou na tela "maior pausa: 1h47m sem eventos de
   * movimento", quando o que houve foi 1h47m sem leitura nenhuma. Num app de
   * sono o defeito e fatal: a noite em que o sensor caiu vira sono perfeito.
   *
   * Agora so conta trecho coberto. Ver `lib/cobertura.ts`.
   */
  maiorPeriodoSemMovimentoMs: number | null;
  /** Onde houve medicao, e onde nao houve (DASH-09). */
  cobertura: Cobertura;
  /**
   * Fracao do tempo MEDIDO em que houve movimento, de 0 a 1.
   *
   * Por tempo, e nao por contagem de amostra: com amostragem irregular, "9
   * eventos em 20 leituras = 45%" nao significa nada — as 20 leituras podiam
   * cobrir tres minutos de uma janela de duas horas.
   */
  fracaoEmMovimento: number | null;
  /**
   * Media da intensidade das leituras EM REPOUSO. Null se nenhuma houver.
   *
   * So repouso, de proposito (DASH-07). Ate aqui a media incluia os eventos
   * de movimento, embora o painel a rotulasse como "media do desvio do
   * repouso". Com um evento a diferenca e pequena; numa noite real, com
   * dezenas, o numero vira uma mistura que nao e nem linha de base nem medida
   * de movimento — nao serve para nada.
   *
   * Separado, ele e a LINHA DE BASE do aparelho: com um sensor perfeito
   * ficaria perto de zero. O que sobra acima de zero e o vies de calibracao
   * daquela unidade (CALC-02) — na bancada de 2026-08-24 deu 0,85.
   */
  intensidadeMedia: number | null;
};

/** Uma leitura com o instante ja convertido e valido. */
type LeituraDatada = { leitura: LeituraSono; instante: Date };

function comInstanteValido(leituras: LeituraSono[]): LeituraDatada[] {
  return leituras
    // `new Date(null)` NAO da NaN: da 1970, e uma linha assim arrastaria a
    // janela por decadas passando ilesa pelo filtro de NaN abaixo.
    .filter((leitura) => typeof leitura.created_at === "string" && leitura.created_at !== "")
    .map((leitura) => ({ leitura, instante: new Date(leitura.created_at) }))
    // `new Date("lixo")` produz Invalid Date, cujo getTime() e NaN. Descartar
    // aqui evita que uma linha corrompida envenene todas as contas abaixo.
    .filter(({ instante }) => !Number.isNaN(instante.getTime()))
    .sort((a, b) => a.instante.getTime() - b.instante.getTime());
}

export function calcularMetricas(leituras: LeituraSono[]): Metricas {
  const datadas = comInstanteValido(leituras);

  if (datadas.length === 0) {
    return {
      totalLeituras: 0,
      eventosDeMovimento: 0,
      janela: null,
      duracaoDaJanelaMs: 0,
      maiorPeriodoSemMovimentoMs: null,
      intensidadeMedia: null,
      cobertura: calcularCobertura([]),
      fracaoEmMovimento: null,
    };
  }

  const inicio = datadas[0].instante;
  const fim = datadas[datadas.length - 1].instante;

  const eventosDeMovimento = datadas.filter(({ leitura }) =>
    ehMovimento(leitura.status),
  ).length;

  // So as leituras que o DISPOSITIVO rotulou como repouso. Quem classifica
  // continua sendo ele; aqui apenas lemos o rotulo (contrato, secao 2.2).
  const cobertura = calcularCobertura(leituras);
  // Movimento como INTERVALO, nao como instante (DASH-11): a leitura resume um
  // periodo, e a pausa se mede entre periodos. Calculado uma vez e reusado
  // pelas duas metricas, para que numerador e denominador nunca divirjam.
  const movimento = trechosDeMovimento(leituras, ehMovimento);

  const intensidadesEmRepouso = datadas
    .filter(({ leitura }) => !ehMovimento(leitura.status))
    .map(({ leitura }) => intensidade(leitura))
    .filter((v): v is number => v !== null);

  return {
    totalLeituras: datadas.length,
    eventosDeMovimento,
    janela: { inicio, fim },
    duracaoDaJanelaMs: fim.getTime() - inicio.getTime(),
    maiorPeriodoSemMovimentoMs: maiorPausaCobertaMs(cobertura, movimento),
    cobertura,
    fracaoEmMovimento: fracaoEmMovimento(cobertura, movimento),
    intensidadeMedia:
      intensidadesEmRepouso.length > 0
        ? intensidadesEmRepouso.reduce((soma, v) => soma + v, 0) /
          intensidadesEmRepouso.length
        : null,
  };
}


/** Duracao legivel: "8h 15m", "45m", "2m 30s", "12s". */
export function formatarDuracao(ms: number | null): string {
  if (ms == null || ms < 0) return "--";

  const totalSegundos = Math.floor(ms / 1000);
  const horas = Math.floor(totalSegundos / 3600);
  const minutos = Math.floor((totalSegundos % 3600) / 60);
  const segundos = totalSegundos % 60;

  if (horas > 0) return `${horas}h ${minutos}m`;
  if (minutos > 0) return `${minutos}m ${segundos}s`;
  return `${segundos}s`;
}

/** Hora local no formato HH:MM:SS. */
export function formatarHora(data: Date): string {
  return data.toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export type PontoDaSerie = {
  hora: string;
  intensidade: number | null;
  movimento: boolean;
  /**
   * Ponto sintetico marcando AUSENCIA DE MEDICAO (DASH-09).
   *
   * O eixo do grafico e categorico: cada leitura ocupa a mesma largura,
   * independentemente do tempo entre elas. Sem marcar, um buraco de duas horas
   * fica visualmente idêntico a dez segundos — foi assim que a tela deixou de
   * mostrar que a coleta tinha caido.
   */
  lacuna: boolean;
  /** Duracao da lacuna, so nos pontos sinteticos. */
  duracaoDaLacunaMs?: number;
};

/**
 * Serie temporal para o grafico, do mais antigo ao mais recente.
 *
 * Com `cobertura`, insere um ponto sintetico onde faltou medicao. Sem ela,
 * comporta-se como antes — util para a demo, que gera serie continua.
 */
export function prepararSerie(
  leituras: LeituraSono[],
  cobertura?: Cobertura,
): PontoDaSerie[] {
  const pontos = comInstanteValido(leituras);
  const serie: PontoDaSerie[] = [];

  for (let i = 0; i < pontos.length; i++) {
    const { leitura, instante } = pontos[i];

    // Antes de desenhar este ponto: houve lacuna entre o anterior e ele?
    if (i > 0 && cobertura) {
      const anterior = pontos[i - 1].instante.getTime();
      const atual = instante.getTime();
      // So INTERRUPCAO — o aparelho ter parado de mandar. Jitter de rede de
      // decimos de segundo nao e buraco de coleta, e desenhar uma coluna cinza
      // para cada um picotava o grafico de uma captacao inteira em centenas de
      // colunas "sem dados" (DASH-11).
      const dentro = cobertura.interrupcoes.find(
        (l) => l.inicio >= anterior && l.fim <= atual && l.fim > l.inicio,
      );
      if (dentro) {
        serie.push({
          hora: "sem dados",
          intensidade: null,
          movimento: false,
          lacuna: true,
          duracaoDaLacunaMs: dentro.fim - dentro.inicio,
        });
      }
    }

    serie.push({
      hora: formatarHora(instante),
      intensidade: intensidade(leitura),
      movimento: ehMovimento(leitura.status),
      lacuna: false,
    });
  }

  return serie;
}
