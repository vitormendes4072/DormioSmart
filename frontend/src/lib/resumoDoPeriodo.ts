/**
 * Os números do topo do Histórico (UI-52): o período escolhido, somado sessão a sessão.
 *
 * Só soma o que cada sessão já calcula (`calcularCobertura`): o tempo registrado e o
 * período do primeiro ao último registro. O intervalo entre uma sessão e outra não entra
 * em nada, como no Início (UI-40): a tarde entre duas noites não é o aparelho parando.
 */
export type SessaoDoPeriodo = {
  chave: string;
  inicio: number;
  fim: number;
  /** Tempo registrado da sessão. */
  tempo: number;
  /** Do primeiro ao último registro; `null` quando não dá para calcular. */
  periodo: number | null;
};

export function resumirPeriodo(sessoes: readonly SessaoDoPeriodo[]) {
  const tempoMs = sessoes.reduce((soma, sessao) => soma + sessao.tempo, 0);
  const comPeriodo = sessoes.filter((sessao) => sessao.periodo !== null && sessao.periodo > 0);
  const periodoMs = comPeriodo.reduce((soma, sessao) => soma + sessao.periodo!, 0);
  const registradoNoPeriodoMs = comPeriodo.reduce((soma, sessao) => soma + Math.min(sessao.tempo, sessao.periodo!), 0);
  return {
    sessoes: sessoes.length,
    tempoMs,
    mediaMs: sessoes.length > 0 ? tempoMs / sessoes.length : null,
    /** Fração do período (somado) que tem registro; `null` sem período calculável. */
    fracaoRegistrada: periodoMs > 0 ? registradoNoPeriodoMs / periodoMs : null,
  };
}

/**
 * A escala do gráfico em horas inteiras, como o "Tempo registrado por dia" do Início:
 * três divisões iguais, e a maior barra (o período, que inclui o sem registro) cabe.
 */
export function escalaEmHoras(maiorMs: number) {
  const HORA = 3_600_000;
  const passo = Math.max(1, Math.ceil(maiorMs / (3 * HORA)));
  return { topoMs: passo * 3 * HORA, ticks: [3 * passo, 2 * passo, passo, 0] };
}

/** Quais rótulos do eixo aparecem: todos até 10 barras; depois, cerca de 8, sempre com a última. */
export function rotuloVisivel(indice: number, total: number) {
  if (total <= 10) return true;
  const passo = Math.ceil(total / 8);
  return indice === total - 1 || (indice % passo === 0 && total - 1 - indice >= passo / 2);
}
