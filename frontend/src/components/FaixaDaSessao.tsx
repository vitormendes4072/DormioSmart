import type { Trecho } from "../lib/cobertura";
import { posicaoNaRegua, type Regua } from "../lib/faixaDaSessao";
import { formatarDuracao } from "../lib/metricas";

const HORA = new Intl.DateTimeFormat("pt-BR", { hour: "2-digit", minute: "2-digit" });

/**
 * A sessão numa faixa (UI-53): onde houve registro, onde faltou e onde houve movimento,
 * na régua de horário comum a todas as linhas do Histórico.
 *
 * Cinza claro é o período da sessão; por cima, em azul claro, os trechos com registro.
 * O que ficou cinza dentro da sessão é tempo sem registro. Os traços escuros são os
 * registros com movimento. A cor não é o único sinal: o rótulo diz tudo por escrito.
 */
export function FaixaDaSessao({ regua, inicio, fim, trechos, movimentos, tempo }: {
  regua: Regua;
  inicio: number;
  fim: number;
  trechos: readonly Trecho[];
  /** Instantes dos registros com movimento. */
  movimentos: readonly number[];
  tempo: number;
}) {
  const x = (ms: number) => posicaoNaRegua(regua, inicio, ms) * 100;
  const largura = (de: number, ate: number) => Math.max(0.4, x(ate) - x(de));
  const rotulo = `Das ${HORA.format(inicio)} às ${HORA.format(fim)}: ${formatarDuracao(tempo)} com registro, `
    + `${movimentos.length} ${movimentos.length === 1 ? "registro" : "registros"} com movimento.`;

  return (
    <svg data-faixa-da-sessao role="img" aria-label={rotulo} viewBox="0 0 100 12" preserveAspectRatio="none"
      className="block h-3.5 w-full min-w-24 overflow-visible">
      <rect x="0" y="5.5" width="100" height="1" className="fill-border" />
      <rect data-periodo x={x(inicio)} y="3" width={largura(inicio, fim)} height="6" rx="1" className="fill-muted-foreground/25" />
      {trechos.map((trecho) => (
        <rect key={trecho.inicio} data-registro x={x(trecho.inicio)} y="3" width={largura(trecho.inicio, trecho.fim)} height="6"
          className="fill-primary/35" />
      ))}
      {movimentos.map((instante) => (
        <rect key={instante} data-movimento x={x(instante)} y="1" width="0.5" height="10" className="fill-primary" />
      ))}
    </svg>
  );
}
