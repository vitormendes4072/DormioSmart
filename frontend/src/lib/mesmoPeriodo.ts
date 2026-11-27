/**
 * Sessões de aparelhos diferentes gravadas no mesmo período (UI-56).
 *
 * Quando o celular e o travesseiro gravam juntos (o protocolo do `VIA-02`), o Histórico
 * mostrava duas sessões soltas, e parecia que eram dias diferentes. Aqui elas viram um
 * grupo, para a tela mostrar os dois lado a lado. Nada é somado nem tirado a média: os
 * dois aparelhos medem de formas diferentes (na primeira noite do `VIA-02`, com o mesmo
 * limite, o celular marcou 0,7% do tempo com movimento e o travesseiro 8,6%), e o limite
 * do celular ainda está em aberto (`DATA-06`).
 *
 * A regra: duas sessões de aparelhos DIFERENTES ficam juntas quando se sobrepõem em pelo
 * menos 30% da mais curta. Um teste de bancada à tarde não entra na noite; duas sessões do
 * mesmo aparelho nunca se juntam por aqui (a pausa dentro de uma sessão é do agrupamento
 * por sessão, `cobertura.ts`). A ligação é transitiva: o grupo é o componente conexo.
 *
 * O grupo não se chama "noite": afirmar que o dado é sono é o `ESC-01`, em aberto.
 */
const SOBREPOSICAO_MINIMA = 0.3;

type Intervalo = { inicio: number; fim: number };

function sobreposicao(a: Intervalo, b: Intervalo) {
  return Math.max(0, Math.min(a.fim, b.fim) - Math.max(a.inicio, b.inicio));
}

export function agruparMesmoPeriodo<T extends Intervalo & { aparelho?: string | null }>(
  sessoes: readonly T[],
  minimo = SOBREPOSICAO_MINIMA,
): T[][] {
  const pai = sessoes.map((_, i) => i);
  const raiz = (i: number): number => (pai[i] === i ? i : (pai[i] = raiz(pai[i])));
  for (let i = 0; i < sessoes.length; i++) {
    for (let j = i + 1; j < sessoes.length; j++) {
      const a = sessoes[i];
      const b = sessoes[j];
      if ((a.aparelho ?? null) === (b.aparelho ?? null)) continue;
      const curta = Math.min(a.fim - a.inicio, b.fim - b.inicio);
      if (curta > 0 && sobreposicao(a, b) >= minimo * curta) pai[raiz(j)] = raiz(i);
    }
  }
  const grupos = new Map<number, T[]>();
  sessoes.forEach((sessao, i) => {
    const r = raiz(i);
    const grupo = grupos.get(r);
    if (grupo) grupo.push(sessao);
    else grupos.set(r, [sessao]);
  });
  // Dentro do grupo, na ordem em que começaram; os grupos, do mais recente ao mais antigo,
  // como a lista do Histórico.
  return [...grupos.values()]
    .map((grupo) => grupo.sort((a, b) => a.inicio - b.inicio))
    .sort((a, b) => b[0].inicio - a[0].inicio);
}

/** A duração da união de intervalos: o tempo em que pelo menos um deles valia. */
export function duracaoDaUniao(intervalos: readonly Intervalo[]) {
  const ordem = [...intervalos].filter((x) => x.fim > x.inicio).sort((a, b) => a.inicio - b.inicio);
  let total = 0;
  let inicio = -Infinity;
  let fim = -Infinity;
  for (const x of ordem) {
    if (x.inicio > fim) {
      if (fim > inicio) total += fim - inicio;
      inicio = x.inicio;
      fim = x.fim;
    } else {
      fim = Math.max(fim, x.fim);
    }
  }
  if (fim > inicio) total += fim - inicio;
  return total;
}
