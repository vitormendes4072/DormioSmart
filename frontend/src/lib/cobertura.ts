import type { LeituraSono } from "../types/sleep";

/**
 * Onde houve medicao, e onde o aparelho parou (DASH-09, refeito no DASH-11).
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
 * ── DUAS PERGUNTAS DIFERENTES, QUE FORAM CONFUNDIDAS ────────────────────
 *
 * A primeira tentativa de conserto tratou as duas como uma so, e foi por isso
 * que ela falhou de tres maneiras. Elas sao:
 *
 * **1. Quanto tempo foi medido?** Responde `trechos` / `tempoCobertoMs`. Sai
 * da duracao que cada leitura cobre: `epoca_segundos` quando o dispositivo
 * declara ("eu resumo 30 segundos"), senao a MEDIANA dos intervalos — mediana,
 * e nao media, porque um unico buraco de duas horas puxaria a media e faria o
 * buraco parecer cadencia normal. Aqui nao se arredonda a favor: todo instante
 * sem leitura conta como nao medido, inclusive os decimos de segundo.
 *
 * **2. O aparelho parou de medir?** Responde `blocos` / `interrupcoes`. Sai do
 * INTERVALO ENTRE CHEGADAS, nao da cobertura. Uma leitura atrasada 1,5 s nao
 * significa que o aparelho parou; uma hora de silencio significa.
 *
 * Confundir as duas produziu, em medicao real:
 *
 * - **Uma noite virava centenas de "sessoes".** Cada leitura cobre uma
 *   cadencia para tras, e a cadencia e a mediana — logo metade dos intervalos
 *   e maior que ela, e virava "lacuna". Cortando sessao em toda lacuna, 960
 *   leituras de 8 h de celular com jitter normal de rede davam **960 sessoes,
 *   a ultima com 1 leitura**. O painel abria a noite inteira com uma amostra.
 *
 * - **Filtrar a lacuna por tamanho cegava o painel para perda sistematica.**
 *   Um dispositivo que resume 30 s mas so envia a cada 45 s deixa 33% do tempo
 *   sem medicao — em buracos de 15 s, pequenos demais para o filtro. A tela
 *   mostrava uma captacao limpa, sem aviso, com 1/3 da janela nao medida.
 *
 * - **E havia um penhasco.** Com envio a cada 60 s e epoca de 30 s, cada
 *   buraco tem exatamente 30 s e o filtro voltava a cortar tudo: 120 leituras,
 *   120 "sessoes". Um segundo de diferenca separava "uma captacao" de "cento e
 *   vinte".
 *
 * Separadas, cada pergunta usa o sinal que de fato a responde.
 *
 * ── QUANDO SE DIZ QUE O APARELHO PAROU ──────────────────────────────────
 *
 * Quando o intervalo passa de `FATOR_DE_INTERRUPCAO` vezes o intervalo tipico
 * — ou seja, quando ao menos duas leituras esperadas nao chegaram. Uma que
 * falhou e soluco; tres intervalos de silencio e parada. O criterio e sobre
 * CHEGADA, entao a duty cycle do dispositivo (resumir 30 s a cada 60 s) nao
 * conta como parada: ele nunca parou, so mede menos do que o tempo que passa.
 * Isso e perda de cobertura, e aparece como perda de cobertura.
 *
 * ── UMA PERGUNTA QUE ESTE MODULO NAO RESOLVE ────────────────────────────
 *
 * Para um ESP32 com Wake-on-Motion (`HW-03`, ainda nao construido), o silencio
 * teria significado oposto: dormir sem acordar E a evidencia de repouso, e o
 * intervalo entre chegadas seria disperso por natureza — nenhum "intervalo
 * tipico" descreveria o aparelho. Aqui o silencio e tratado como ausencia de
 * informacao, que e o correto para amostragem regular, que e como os dois
 * dispositivos funcionam hoje.
 *
 * Quando o wake-on-motion existir, isto precisa ser revisto junto com o
 * `DATA-02` (modelo de amostragem), que segue em aberto.
 *
 * ── E UMA QUE ELE ESCONDE ───────────────────────────────────────────────
 *
 * Tudo aqui usa `created_at`, que o banco gera na CHEGADA. O dispositivo
 * tambem manda o instante em que mediu (`captured_at`), e esse e que descreve
 * a captacao — mas ele nao vem no `select` do painel hoje. Enquanto for assim,
 * latencia de rede aparece como irregularidade de cadencia, e o buffer offline
 * do `HW-05` chegara todo empilhado em poucos segundos. Trocar a base de tempo
 * e o `DASH-12`.
 */

/** Um intervalo continuo, em milissegundos desde a epoca. */
export type Trecho = { inicio: number; fim: number };

/**
 * Quantas vezes o intervalo tipico caracteriza uma parada.
 *
 * Tres: ao menos duas leituras esperadas nao chegaram. Uma leitura perdida e
 * soluco de rede — o proprio app descarta a epoca sem amostra
 * (`useColeta.ts`) e nao regrava envio que falhou, entao o intervalo dobrado
 * e esperado em operacao normal.
 */
const FATOR_DE_INTERRUPCAO = 3;

export type Cobertura = {
  /** Trechos em que houve medicao, em ordem e sem sobreposicao. */
  trechos: Trecho[];
  /** Soma da duracao dos trechos cobertos. */
  tempoCobertoMs: number;
  /** Do inicio da primeira leitura ao fim da ultima. */
  janelaMs: number;
  /** TODO instante sem medicao dentro da janela, inclusive jitter. */
  lacunas: Trecho[];
  /** Periodos em que o aparelho esteve operando, sem parar. */
  blocos: Trecho[];
  /** Silencios entre blocos: o aparelho parou de mandar. */
  interrupcoes: Trecho[];
  /** Mediana do intervalo entre chegadas. `null` com menos de duas leituras. */
  intervaloTipicoMs: number | null;
  /** `true` quando ALGUMA leitura teve a cadencia inferida, nao declarada. */
  cadenciaInferida: boolean;
};

/** Leitura com instante ja convertido, em ordem crescente. */
type Datada = { leitura: LeituraSono; t: number };

function datadas(leituras: LeituraSono[]): Datada[] {
  return leituras
    .filter((leitura) => typeof leitura.created_at === "string" && leitura.created_at !== "")
    .map((leitura) => ({ leitura, t: new Date(leitura.created_at).getTime() }))
    // `new Date("lixo")` produz Invalid Date, cujo getTime() e NaN. O filtro
    // acima cuida de `null`/`undefined`/vazio, que NAO produzem NaN — viram
    // 1970 e arrastariam a janela por decadas.
    .filter(({ t }) => !Number.isNaN(t))
    .sort((a, b) => a.t - b.t);
}

function mediana(valores: number[]): number | null {
  if (valores.length === 0) return null;
  const ordenados = [...valores].sort((a, b) => a - b);
  const meio = Math.floor(ordenados.length / 2);
  return ordenados.length % 2 === 1
    ? ordenados[meio]
    : (ordenados[meio - 1] + ordenados[meio]) / 2;
}

/**
 * Une trechos que se tocam ou se sobrepoem.
 *
 * Ordena por INICIO antes de unir. Ordenar pelo fim (que e o instante da
 * leitura) nao basta: com `epoca_segundos` variavel, um trecho posterior pode
 * comecar antes do anterior, e a uniao ingenua descartaria o pedaco inicial —
 * subestimando a cobertura sem que nada sinalizasse.
 */
function unir(brutos: Trecho[]): Trecho[] {
  const ordenados = [...brutos].sort((a, b) => a.inicio - b.inicio || a.fim - b.fim);
  const unidos: Trecho[] = [];
  for (const bruto of ordenados) {
    const ultimo = unidos[unidos.length - 1];
    if (ultimo && bruto.inicio <= ultimo.fim) {
      ultimo.fim = Math.max(ultimo.fim, bruto.fim);
    } else {
      unidos.push({ ...bruto });
    }
  }
  return unidos;
}

function duracaoTotal(trechos: Trecho[]): number {
  return trechos.reduce((soma, t) => soma + (t.fim - t.inicio), 0);
}

/** `base` menos `remover`. Ambos sao unidos e ordenados antes, por seguranca. */
function subtrair(base: Trecho[], remover: Trecho[]): Trecho[] {
  const alvo = unir(base);
  const buracos = unir(remover);
  const restante: Trecho[] = [];
  for (const trecho of alvo) {
    let cursor = trecho.inicio;
    for (const buraco of buracos) {
      if (buraco.fim <= cursor) continue;
      if (buraco.inicio >= trecho.fim) break;
      if (buraco.inicio > cursor) restante.push({ inicio: cursor, fim: buraco.inicio });
      cursor = Math.max(cursor, buraco.fim);
    }
    if (cursor < trecho.fim) restante.push({ inicio: cursor, fim: trecho.fim });
  }
  return restante;
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
  return mediana(intervalos);
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

/** Os trechos que cada leitura cobre, antes de unir. */
function brutosDe(lista: Datada[], cadencia: number | null): Trecho[] {
  return lista.map(({ leitura, t }) => {
    const dura = coberturaDaLeitura(leitura, cadencia);
    return { inicio: t - dura, fim: t };
  });
}

/**
 * Onde houve medicao, e quando o aparelho esteve operando.
 *
 * Cada leitura cobre o intervalo que TERMINA no seu instante — a leitura
 * resume o periodo anterior a ela, nao o posterior.
 */
export function calcularCobertura(leituras: LeituraSono[]): Cobertura {
  const lista = datadas(leituras);
  const vazio: Cobertura = {
    trechos: [], tempoCobertoMs: 0, janelaMs: 0, lacunas: [], blocos: [],
    interrupcoes: [], intervaloTipicoMs: null, cadenciaInferida: false,
  };
  if (lista.length === 0) return vazio;

  const cadencia = cadenciaMedianaMs(leituras);
  // `some` sobre quem NAO declara: basta uma leitura sem `epoca_segundos` para
  // que parte da cobertura na tela seja inferida — e a tela tem que dizer
  // isso. A versao anterior so avisava quando NENHUMA declarava, o que
  // silenciava justamente a serie mista (celular + ESP32).
  const algumaInfere = lista.some(
    ({ leitura }) => !(typeof leitura.epoca_segundos === "number" && leitura.epoca_segundos > 0),
  );

  const brutos = brutosDe(lista, cadencia);
  const trechos = unir(brutos);

  const janelaInicio = trechos[0].inicio;
  const janelaFim = trechos[trechos.length - 1].fim;

  const lacunas: Trecho[] = [];
  for (let i = 1; i < trechos.length; i++) {
    lacunas.push({ inicio: trechos[i - 1].fim, fim: trechos[i].inicio });
  }

  // Blocos de operacao: quebram no intervalo entre CHEGADAS, nao na cobertura.
  const limite = cadencia == null ? Infinity : cadencia * FATOR_DE_INTERRUPCAO;
  const blocos: Trecho[] = [];
  for (let i = 0; i < lista.length; i++) {
    const abreBloco = i === 0 || lista[i].t - lista[i - 1].t > limite;
    if (abreBloco) blocos.push({ inicio: brutos[i].inicio, fim: lista[i].t });
    else blocos[blocos.length - 1].fim = Math.max(blocos[blocos.length - 1].fim, lista[i].t);
  }

  const interrupcoes: Trecho[] = [];
  for (let i = 1; i < blocos.length; i++) {
    interrupcoes.push({ inicio: blocos[i - 1].fim, fim: blocos[i].inicio });
  }

  return {
    trechos,
    tempoCobertoMs: duracaoTotal(trechos),
    janelaMs: janelaFim - janelaInicio,
    lacunas,
    blocos,
    interrupcoes,
    intervaloTipicoMs: cadencia,
    cadenciaInferida: algumaInfere && cadencia !== null,
  };
}

/**
 * Os trechos em que o DISPOSITIVO rotulou movimento, unidos.
 *
 * Movimento e intervalo, nao instante: uma leitura com `epoca_segundos: 30`
 * diz "houve movimento nestes 30 segundos", nao "houve movimento neste ponto".
 * Tratar como ponto produzia a contradicao de uma sessao com uma unica leitura
 * de movimento aparecer como 100% em movimento E com uma pausa do tamanho da
 * sessao inteira.
 */
export function trechosDeMovimento(
  leituras: LeituraSono[],
  ehMovimento: (status: string | null | undefined) => boolean,
): Trecho[] {
  const lista = datadas(leituras);
  if (lista.length === 0) return [];
  const cadencia = cadenciaMedianaMs(leituras);
  const brutos = brutosDe(lista, cadencia).filter(
    (_, i) => ehMovimento(lista[i].leitura.status),
  );
  return unir(brutos);
}

/**
 * Maior periodo sem movimento registrado, **dentro de uma captacao**.
 *
 * ── POR QUE SOBRE `blocos`, E NAO SOBRE `trechos` ───────────────────────
 *
 * Esta e a correcao mais importante do DASH-11, e ela reverte uma decisao da
 * primeira tentativa. Medir a pausa sobre os trechos de COBERTURA parece o
 * mais rigoroso — so conta onde houve medicao — e produz absurdo: com jitter
 * de rede, a cobertura de uma noite fica picotada em 960 pedacos de 30 s, e a
 * maior pausa possivel passa a ser 30 s. Medido, numa noite de 8h11m com ZERO
 * leituras de movimento, a tela dizia **"Maior pausa: 30s"**. Erro de ~980x,
 * no card mais visivel do painel.
 *
 * O que o dado sustenta e: entre duas leituras seguidas, ambas rotuladas
 * repouso, o aparelho estava operando e nao registrou movimento. Isso e uma
 * afirmacao sobre o REGISTRO, nao sobre o mundo — por isso o rotulo na tela e
 * "sem movimento registrado". O que nao se pode fazer e atravessar uma
 * interrupcao: ali o aparelho parou, e o `DASH-09` existe por causa disso.
 *
 * Devolve `null` quando nao houve medicao — e nao zero. Zero afirmaria "voce
 * nao teve pausa nenhuma", que e uma medida; a ausencia de medicao nao e. A
 * guarda e sobre TEMPO COBERTO, nao sobre existir bloco: uma leitura solta sem
 * `epoca_segundos` produz um bloco de duracao zero, que existe e nao mede nada.
 */
export function maiorPausaCobertaMs(
  cobertura: Cobertura,
  movimento: Trecho[],
): number | null {
  if (cobertura.tempoCobertoMs <= 0) return null;
  const semMovimento = subtrair(cobertura.blocos, movimento);
  // Lista vazia aqui e uma medida de verdade: todo o tempo da captacao teve
  // movimento registrado, logo a maior pausa foi zero.
  return semMovimento.reduce((maior, t) => Math.max(maior, t.fim - t.inicio), 0);
}

/**
 * Fracao do tempo MEDIDO em que houve movimento, de 0 a 1.
 *
 * Por tempo, e nao por contagem de amostra. Com amostragem irregular, "9
 * eventos em 20 leituras = 45%" nao significa nada: as 20 leituras podiam
 * cobrir tres minutos de uma janela de duas horas.
 *
 * Aqui o denominador e a COBERTURA, e nao o bloco: a pergunta e "do que foi
 * medido, quanto foi movimento?". Numerador e denominador saem da mesma
 * uniao — a versao anterior somava os pesos brutos no denominador e a
 * cobertura unida no numerador, e leitura duplicada era contada duas vezes.
 */
export function fracaoEmMovimento(
  cobertura: Cobertura,
  movimento: Trecho[],
): number | null {
  if (cobertura.tempoCobertoMs <= 0) return null;
  const dentro = subtrair(movimento, subtrair(movimento, cobertura.trechos));
  return duracaoTotal(dentro) / cobertura.tempoCobertoMs;
}

/**
 * O que dizer sobre o que faltou medir (DASH-09, refeito no DASH-11).
 *
 * Devolve `null` quando nao ha o que avisar. Existe como funcao pura, fora do
 * componente, porque a decisao "avisa ou nao avisa" e exatamente onde a
 * primeira tentativa errou — e nao havia teste nenhum sobre ela.
 *
 * O gatilho e a PERDA REAL (`janela - coberto`), nao o tamanho dos buracos. Foi
 * essa troca que cegou o painel: um dispositivo que resume 30 s e envia a cada
 * 45 s perde 33% da janela em buracos de 15 s, pequenos demais para qualquer
 * filtro de tamanho, e a tela mostrava uma captacao limpa.
 */
export type AvisoDeCobertura = {
  /** Tempo da janela sem medicao nenhuma. */
  perdidoMs: number;
  /** Silencios em que o aparelho parou. Pode ser vazio. */
  interrupcoes: Trecho[];
  /** Maior interrupcao, ou 0 se nao houve. */
  maiorInterrupcaoMs: number;
  /**
   * `true` quando a perda nao esta nas interrupcoes, e sim espalhada: o
   * aparelho nunca parou, so resume menos tempo do que o intervalo entre
   * envios. E uma causa diferente, e a frase na tela precisa ser outra.
   */
  perdaDistribuida: boolean;
  cadenciaInferida: boolean;
};

/** Acima disto a perda muda a leitura dos numeros. Folgado de proposito. */
const PERDA_TOLERAVEL = 0.05;

export function avaliarCobertura(cobertura: Cobertura): AvisoDeCobertura | null {
  if (cobertura.janelaMs <= 0) return null;

  const perdidoMs = cobertura.janelaMs - cobertura.tempoCobertoMs;
  if (perdidoMs <= 0) return null;
  if (perdidoMs / cobertura.janelaMs < PERDA_TOLERAVEL) return null;

  const emInterrupcoes = duracaoTotal(cobertura.interrupcoes);

  return {
    perdidoMs,
    interrupcoes: cobertura.interrupcoes,
    maiorInterrupcaoMs: cobertura.interrupcoes.reduce(
      (m, l) => Math.max(m, l.fim - l.inicio), 0,
    ),
    // Mais da metade da perda esta fora das interrupcoes.
    perdaDistribuida: emInterrupcoes < perdidoMs / 2,
    cadenciaInferida: cobertura.cadenciaInferida,
  };
}

/**
 * Uma sessao de captacao: um periodo em que o aparelho esteve operando.
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
 * de fato esteve medindo. Se um dia o projeto decidir afirmar noites, isso
 * vira decisao de escopo (e depende do `DATA-02`), nao de tela.
 *
 * O corte e a INTERRUPCAO — o aparelho parar de mandar —, e nao qualquer
 * descontinuidade de cobertura. Ver o cabecalho deste arquivo.
 */
export type Sessao = {
  inicio: number;
  fim: number;
  leituras: LeituraSono[];
};

export function agruparEmSessoes(leituras: LeituraSono[]): Sessao[] {
  const cobertura = calcularCobertura(leituras);
  if (cobertura.blocos.length === 0) return [];

  const lista = datadas(leituras);

  return cobertura.blocos
    .map((bloco) => ({
      inicio: bloco.inicio,
      fim: bloco.fim,
      leituras: lista
        .filter(({ t }) => t >= bloco.inicio && t <= bloco.fim)
        .map(({ leitura }) => leitura),
    }))
    // Bloco sem leitura nao e sessao. Nao deveria acontecer — os blocos sao
    // construidos A PARTIR das leituras — mas uma sessao vazia produziria
    // metricas de nada, que e o defeito que o DASH-09 corrigiu.
    .filter((s) => s.leituras.length > 0);
}
