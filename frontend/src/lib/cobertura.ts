import type { LeituraSono } from "../types/sleep";

/**
 * Onde houve medicao, e onde nao houve (DASH-09, corrigido no DASH-11).
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
 * ── LACUNA MATERIAL: O QUE O DASH-11 CORRIGIU ───────────────────────────
 *
 * A primeira versao chamava de lacuna QUALQUER intervalo descoberto, por menor
 * que fosse. Isso parece rigoroso e e, na verdade, um defeito grave: cada
 * leitura cobre exatamente uma cadencia para tras, e a cadencia e a MEDIANA
 * dos intervalos — logo, por definicao de mediana, cerca de METADE dos
 * intervalos e maior que ela. Jitter de rede de decimos de segundo virava
 * "lacuna".
 *
 * Como `agruparEmSessoes` cortava em toda lacuna, o efeito na tela era brutal:
 * numa captacao de 8h de celular com latencia normal, 960 leituras viravam
 * ~476 "sessoes", e o painel abria mostrando a ultima — com DUAS leituras.
 * Uma noite inteira medida virava uma tela vazia. O remedio tinha ficado pior
 * que a doenca.
 *
 * O criterio que resolve nao e um numero escolhido a dedo: **uma lacuna e
 * material quando cabe nela ao menos uma leitura que deveria ter chegado e nao
 * chegou** — isto e, quando dura ao menos uma cobertura tipica (a mediana das
 * coberturas individuais, `referenciaMs`). Abaixo disso, nada se perdeu: o
 * atraso da leitura seguinte descreve o mesmo tempo, so que um pouco depois.
 *
 * As duas listas coexistem de proposito:
 * - `lacunas` — todas, inclusive as de milissegundos. E o que sustenta a
 *   aritmetica de `tempoCobertoMs`, que continua sem arredondar a favor.
 * - `lacunasMateriais` — as que significam leitura perdida. E o que recorta
 *   sessoes, o que o grafico desenha e o que o aviso relata.
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
 *
 * ── E UMA QUE ELE ESCONDE ───────────────────────────────────────────────
 *
 * Tudo aqui usa `created_at`, que o banco gera na CHEGADA (contrato §
 * "Campos", `default now()`). O dispositivo tambem manda o instante em que
 * mediu (`captured_at`), e esse e que descreve a captacao — mas ele nao vem no
 * `select` do painel hoje. Enquanto for assim, latencia de rede aparece como
 * irregularidade de cadencia, e o buffer offline do `HW-05` chegara todo
 * empilhado em poucos segundos. Trocar a base de tempo e o `DASH-12`.
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
  /** TODOS os trechos sem medicao dentro da janela, inclusive jitter. */
  lacunas: Trecho[];
  /** Só as lacunas grandes o bastante para significar leitura perdida. */
  lacunasMateriais: Trecho[];
  /** Cobertura tipica de uma leitura (mediana). `null` com menos de uma. */
  referenciaMs: number | null;
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

/** `base` menos `remover`. Ambos precisam estar unidos e em ordem. */
function subtrair(base: Trecho[], remover: Trecho[]): Trecho[] {
  const restante: Trecho[] = [];
  for (const trecho of base) {
    let cursor = trecho.inicio;
    for (const buraco of remover) {
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
 * Onde houve medicao.
 *
 * Cada leitura cobre o intervalo que TERMINA no seu instante — a leitura
 * resume o periodo anterior a ela, nao o posterior. Trechos que se tocam sao
 * unidos.
 */
export function calcularCobertura(leituras: LeituraSono[]): Cobertura {
  const lista = datadas(leituras);
  const vazio: Cobertura = {
    trechos: [], tempoCobertoMs: 0, janelaMs: 0, lacunas: [], lacunasMateriais: [],
    referenciaMs: null, cadenciaInferida: false,
  };
  if (lista.length === 0) return vazio;

  const cadencia = cadenciaMedianaMs(leituras);
  // `some`, e nao `every`: basta UMA leitura sem `epoca_segundos` para que
  // parte da cobertura na tela seja inferida — e a tela tem que dizer isso.
  // A versao anterior so avisava quando NENHUMA declarava, o que silenciava
  // justamente a serie mista (celular + ESP32).
  const algumaInfere = lista.some(
    ({ leitura }) => !(typeof leitura.epoca_segundos === "number" && leitura.epoca_segundos > 0),
  );

  const brutos = brutosDe(lista, cadencia);
  const trechos = unir(brutos);

  const janelaInicio = trechos[0].inicio;
  const janelaFim = trechos[trechos.length - 1].fim;

  const referenciaMs = mediana(brutos.map((b) => b.fim - b.inicio).filter((d) => d > 0));

  const lacunas: Trecho[] = [];
  for (let i = 1; i < trechos.length; i++) {
    lacunas.push({ inicio: trechos[i - 1].fim, fim: trechos[i].inicio });
  }

  return {
    trechos,
    tempoCobertoMs: duracaoTotal(trechos),
    janelaMs: janelaFim - janelaInicio,
    lacunas,
    lacunasMateriais: lacunas.filter((l) => ehMaterial(l.fim - l.inicio, referenciaMs)),
    referenciaMs,
    cadenciaInferida: algumaInfere && cadencia !== null,
  };
}

/**
 * A lacuna representa leitura perdida, ou so atraso?
 *
 * Material quando cabe nela ao menos uma cobertura tipica. Sem referencia
 * (uma leitura so) nao ha lacuna a classificar; devolver `false` evita
 * inventar buraco onde nao se sabe medir.
 */
function ehMaterial(duracaoMs: number, referenciaMs: number | null): boolean {
  if (referenciaMs == null || referenciaMs <= 0) return false;
  return duracaoMs >= referenciaMs;
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
 * Maior periodo sem movimento **dentro do que foi medido**.
 *
 * A diferenca para a versao anterior e toda aqui: um trecho so entra na conta
 * se houve medicao nele. Buraco de coleta nao vira pausa.
 *
 * Devolve `null` quando nao ha cobertura — e nao zero. Zero afirmaria "voce
 * nao teve pausa nenhuma", que e uma medida; a ausencia de medicao nao e. A
 * guarda e sobre TEMPO COBERTO, nao sobre existir trecho: uma leitura solta
 * sem `epoca_segundos` produz um trecho de duracao zero, que existe na lista e
 * nao mede nada.
 */
export function maiorPausaCobertaMs(
  cobertura: Cobertura,
  movimento: Trecho[],
): number | null {
  if (cobertura.tempoCobertoMs <= 0) return null;
  const semMovimento = subtrair(cobertura.trechos, movimento);
  // Lista vazia aqui e uma medida de verdade: todo o tempo medido foi
  // movimento, logo a maior pausa foi zero.
  return semMovimento.reduce((maior, t) => Math.max(maior, t.fim - t.inicio), 0);
}

/**
 * Fracao do tempo MEDIDO em que houve movimento, de 0 a 1.
 *
 * Por tempo, e nao por contagem de amostra. Com amostragem irregular, "9
 * eventos em 20 leituras = 45%" nao significa nada: as 20 leituras podiam
 * cobrir tres minutos de uma janela de duas horas.
 *
 * Numerador e denominador saem da MESMA uniao de trechos. A versao anterior
 * somava os pesos brutos no denominador e a cobertura unida no numerador: com
 * leituras sobrepostas (reenvio, carimbo duplicado, epoca maior que o
 * intervalo) os dois divergiam, e a tela multiplicava um pelo outro.
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
 * O corte e a LACUNA MATERIAL, nao qualquer descontinuidade — ver o cabecalho
 * deste arquivo. Cortar em toda lacuna fazia jitter de rede picotar uma noite
 * inteira em centenas de "sessoes".
 */
export type Sessao = {
  inicio: number;
  fim: number;
  leituras: LeituraSono[];
};

export function agruparEmSessoes(leituras: LeituraSono[]): Sessao[] {
  const cobertura = calcularCobertura(leituras);
  if (cobertura.trechos.length === 0) return [];

  // Reagrupa os trechos: so a lacuna material separa sessoes.
  const blocos: Trecho[] = [];
  for (const trecho of cobertura.trechos) {
    const ultimo = blocos[blocos.length - 1];
    if (ultimo && !ehMaterial(trecho.inicio - ultimo.fim, cobertura.referenciaMs)) {
      ultimo.fim = Math.max(ultimo.fim, trecho.fim);
    } else {
      blocos.push({ ...trecho });
    }
  }

  const lista = datadas(leituras);

  return blocos
    .map((bloco) => ({
      inicio: bloco.inicio,
      fim: bloco.fim,
      leituras: lista
        .filter(({ t }) => t >= bloco.inicio && t <= bloco.fim)
        .map(({ leitura }) => leitura),
    }))
    // Trecho sem leitura nao e sessao. Nao deveria acontecer — os trechos sao
    // construidos A PARTIR das leituras — mas uma sessao vazia produziria
    // metricas de nada, que e o defeito que o DASH-09 corrigiu.
    .filter((s) => s.leituras.length > 0);
}
