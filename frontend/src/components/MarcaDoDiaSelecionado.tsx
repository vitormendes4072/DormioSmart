/**
 * O dia escolhido (UI-46/UI-47), igual no calendário e no gráfico: um anel grosso na cor primária,
 * afastado do conteúdo. Distinto do anel fino de "hoje" e do fundo cheio da sequência (UI-48).
 * Vai dentro de um elemento `relative`, que o anel contorna.
 */
export function MarcaDoDiaSelecionado({ justa = false }: {
  /** No rótulo do gráfico, onde a coluna é estreita: o anel encosta no texto, sem a folga de 4 px. */
  justa?: boolean;
}) {
  return <span aria-hidden="true" data-marca-dia className={`pointer-events-none absolute ${justa ? "-inset-0.5" : "-inset-1"} rounded-full ring-2 ring-primary ring-offset-1 ring-offset-card`} />;
}
