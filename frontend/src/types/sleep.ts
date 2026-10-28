/**
 * Tipos e derivacoes do dado de sensor.
 *
 * Espelha `docs/DATA-CONTRACT.md` v1.2.0. Se o contrato mudar, este arquivo
 * muda junto — e vice-versa. Divergencia entre os dois e bug.
 */

/** Referencia de repouso: a magnitude do vetor de aceleracao em repouso fica
 *  proxima da gravidade. Contrato, secao 2.1. */
export const GRAVIDADE = 9.81;

/**
 * Limiar do criterio de movimento do DISPOSITIVO, em m/s2 (DATA-02).
 *
 * ATENCAO: esta constante NAO classifica nada. Ela existe para DOCUMENTAR e
 * ILUSTRAR o criterio que roda no firmware — desenhar a faixa de limiar no
 * grafico da landing, gerar dado de demonstracao coerente. Quem decide se uma
 * leitura e movimento continua sendo o dispositivo, e a leitura chega ao app
 * ja rotulada (ver `ehMovimento` abaixo).
 *
 * Usar este valor para reclassificar leitura recriaria a segunda regua que o
 * contrato v1.1.0 eliminou.
 */
export const LIMIAR_DE_MOVIMENTO = 1.2;

/**
 * Rotulos que significam movimento.
 *
 * "Movimento" e o rotulo do contrato v1.1.0 em diante. "Movimento Detectado!"
 * e legado: continua gravado no banco em leituras antigas e e reconhecido de
 * proposito — reescrever medicao ja coletada para casar com nomenclatura nova
 * seria adulterar dado. Contrato, secao 2.2.
 */
export const ROTULOS_MOVIMENTO = ["Movimento", "Movimento Detectado!"];

/** Uma leitura como devolvida por `GET /api/sleep-history`. Os campos sao
 *  anulaveis porque o banco aceita nulo — a UI precisa lidar com isso. */
export type LeituraSono = {
  /** Instante em que a linha CHEGOU ao banco (`default now()`). Sempre
   *  presente — e o que o Postgres garante, nao o dispositivo. */
  created_at: string;
  /**
   * Instante em que a leitura foi MEDIDA, declarado pelo dispositivo (DASH-12).
   *
   * Nulo nas linhas gravadas antes de o campo entrar no `select`, e em
   * qualquer envio que nao o declare. Use `instanteDaLeitura` — nunca este
   * campo direto — para que o fallback para `created_at` seja o mesmo em
   * todo lugar.
   */
  captured_at?: string | null;
  movimento_total: number | null;
  temp: number | null;
  status: string | null;
  /** De qual dispositivo veio a leitura (DASH-05). Nulo nas linhas anteriores
   *  ao multiusuario, que nao tem dono nem dispositivo registrado. */
  device_id?: string | null;
  /**
   * Quantos segundos esta linha RESUME (contrato v2.0.0).
   *
   * Nulo = amostra instantanea, o caso do ESP32. Presente = a linha cobre uma
   * janela, o caso do celular.
   *
   * E o que permite ao painel distinguir "repouso" de "sem medicao": sem esta
   * informacao, duas horas de silencio e duas horas de repouso continuo sao
   * indistinguiveis (DASH-09).
   */
  epoca_segundos?: number | null;
};

/**
 * O instante que descreve a leitura (DASH-12).
 *
 * ── POR QUE `captured_at` VEM PRIMEIRO ──────────────────────────────────
 *
 * `created_at` e a hora de CHEGADA, gerada pelo banco. `captured_at` e a hora
 * da MEDICAO, declarada pelo dispositivo. Toda a maquina de cobertura, lacuna
 * e sessao descreve uma captacao — logo tem que usar o instante da captacao.
 *
 * Usar a chegada era incoerente com o resto do modulo: o painel ja aceita a
 * DURACAO declarada pelo dispositivo (`epoca_segundos`) como verdade, e
 * ignorava o INSTANTE declarado pelo mesmo dispositivo.
 *
 * **Consequencia hoje:** latencia de rede aparecia como irregularidade de
 * cadencia — foi a raiz de um dos defeitos do DASH-11.
 *
 * **Consequencia amanha:** o buffer offline do `HW-05` vai chegar todo
 * empilhado em poucos segundos de `created_at`, e o painel veria uma "sessao
 * de 2 segundos" com o resto da noite como lacuna. Precisava estar resolvido
 * antes do `HW-05`, e agora esta.
 *
 * O fallback para `created_at` nao e cortesia: linhas gravadas antes deste
 * campo entrar no `select` nao tem `captured_at`, e reescreve-las para casar
 * com o campo novo seria adulterar medicao ja coletada — a mesma razao pela
 * qual `ROTULOS_MOVIMENTO` ainda reconhece o rotulo legado.
 *
 * Devolve string vazia quando nao ha instante utilizavel; quem consome filtra.
 */
export function instanteDaLeitura(leitura: LeituraSono): string {
  const medido = leitura.captured_at;
  if (typeof medido === "string" && medido !== "") return medido;
  const chegada = leitura.created_at;
  return typeof chegada === "string" ? chegada : "";
}

/**
 * Intensidade do movimento: desvio absoluto em relacao ao repouso.
 *
 * Em repouso vale ~0; durante um evento, cresce. E o que o grafico exibe.
 * Devolve null quando nao ha leitura — para o grafico abrir uma lacuna em vez
 * de desenhar um zero que nunca foi medido.
 */
export function intensidade(leitura: LeituraSono | null | undefined): number | null {
  if (leitura == null || leitura.movimento_total == null) return null;
  return Math.abs(leitura.movimento_total - GRAVIDADE);
}

/**
 * Classificacao de uma leitura.
 *
 * Quem classifica e o DISPOSITIVO; aqui so lemos o rotulo que ele mandou.
 * Reclassificar no cliente criaria uma segunda regua — exatamente o defeito
 * que o contrato v1.1.0 corrigiu. Contrato, secao 2.2.
 */
export function ehMovimento(status: string | null | undefined): boolean {
  return status != null && ROTULOS_MOVIMENTO.includes(status);
}
