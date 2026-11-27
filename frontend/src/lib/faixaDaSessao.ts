/**
 * A régua de horário das faixas do Histórico (UI-53).
 *
 * Cada sessão vira uma faixa horizontal, e todas usam a mesma régua: o horário do dia, e
 * não a data. Assim, duas noites que começaram às 23h começam no mesmo ponto, e dá para
 * comparar de olho quando cada uma começou, parou e terminou.
 *
 * O dia da régua vai de meio-dia a meio-dia: uma noite das 23h às 7h fica inteira, sem
 * partir na meia-noite. A régua começa na hora cheia antes do início mais cedo e termina
 * na hora cheia depois do fim mais tarde, e não passa de 24 horas.
 */
const HORA = 3_600_000;
const DIA = 24 * HORA;

/** O meio-dia local no começo do "dia da régua" do instante (o meio-dia anterior, ou o próprio). */
function meioDiaAntes(ms: number) {
  const d = new Date(ms);
  const meioDia = new Date(d.getFullYear(), d.getMonth(), d.getDate(), 12).getTime();
  return ms >= meioDia ? meioDia : new Date(d.getFullYear(), d.getMonth(), d.getDate() - 1, 12).getTime();
}

export type Regua = {
  /** Deslocamento, a partir do meio-dia, do começo e do fim da régua. */
  deMs: number;
  ateMs: number;
};

export function reguaDoHorario(sessoes: ReadonlyArray<{ inicio: number; fim: number }>): Regua {
  if (sessoes.length === 0) return { deMs: 10 * HORA, ateMs: 20 * HORA };
  let menor = Infinity;
  let maior = -Infinity;
  for (const { inicio, fim } of sessoes) {
    const deslocamento = inicio - meioDiaAntes(inicio);
    menor = Math.min(menor, deslocamento);
    maior = Math.max(maior, deslocamento + Math.max(0, fim - inicio));
  }
  const deMs = Math.floor(menor / HORA) * HORA;
  const ateMs = Math.min(deMs + DIA, Math.max(deMs + HORA, Math.ceil(maior / HORA) * HORA));
  return { deMs, ateMs };
}

/**
 * Onde um instante da sessão cai na régua, de 0 a 1. O instante é medido a partir do
 * início da sessão, para a faixa inteira ficar do mesmo lado da meia-noite.
 */
export function posicaoNaRegua(regua: Regua, inicioDaSessao: number, instante: number) {
  const deslocamento = inicioDaSessao - meioDiaAntes(inicioDaSessao) + (instante - inicioDaSessao);
  const fracao = (deslocamento - regua.deMs) / (regua.ateMs - regua.deMs);
  return Math.min(1, Math.max(0, fracao));
}

/** As horas cheias da régua, para o cabeçalho: "22h", "0h", "2h"… (no máximo 7 marcas). */
export function marcasDaRegua(regua: Regua) {
  const horas = (regua.ateMs - regua.deMs) / HORA;
  const passo = Math.max(1, Math.ceil(horas / 6));
  const marcas: Array<{ fracao: number; rotulo: string }> = [];
  for (let h = 0; h <= horas; h += passo) {
    const hora = (12 + (regua.deMs / HORA) + h) % 24;
    marcas.push({ fracao: h / horas, rotulo: `${hora}h` });
  }
  return marcas;
}
