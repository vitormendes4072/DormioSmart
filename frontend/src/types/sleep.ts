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
  created_at: string;
  movimento_total: number | null;
  temp: number | null;
  status: string | null;
  /** De qual dispositivo veio a leitura (DASH-05). Nulo nas linhas anteriores
   *  ao multiusuario, que nao tem dono nem dispositivo registrado. */
  device_id?: string | null;
};

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
