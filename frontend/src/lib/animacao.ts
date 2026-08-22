/**
 * Regras de movimento da interface (UI-15).
 *
 * As decisoes ficam aqui, fora do React, pelo mesmo motivo de `rotas.ts`:
 * o que da para testar como funcao pura nao deveria precisar de DOM montado.
 *
 * ── FALHA ABERTA, NUNCA FECHADA ─────────────────────────────────────────
 *
 * O estado inicial de um elemento revelado no scroll e "escondido". Se o JS
 * que o revela nao rodar, o conteudo some — e uma pagina publica que depende
 * de animacao para exibir texto e uma pagina quebrada.
 *
 * Por isso a ordem e invertida: o CSS deixa tudo visivel por padrao, e e o JS
 * que ADICIONA a classe que esconde, imediatamente antes de observar. Sem JS,
 * sem IntersectionObserver, ou com o observador falhando, o resultado e a
 * pagina inteira legivel — apenas sem a entrada suave.
 */

export const CONSULTA_MENOS_MOVIMENTO = "(prefers-reduced-motion: reduce)";

/** Aplicada pelo JS para esconder antes de revelar. Ver nota acima. */
export const CLASSE_ARMADO = "revelar-armado";
/** Aplicada quando o elemento entra na janela. Dispara a transicao. */
export const CLASSE_VISIVEL = "revelar-visivel";

type ConsultaDeMidia = { matches: boolean };
type AlvoComMatchMedia = { matchMedia?: (consulta: string) => ConsultaDeMidia };

/**
 * O usuario pediu menos movimento no sistema operacional?
 *
 * Nao e preferencia estetica: movimento na tela provoca enjoo e enxaqueca em
 * quem tem disturbio vestibular. Quando isso e verdade, nada anima — o hook
 * nem chega a armar os elementos, e o CSS ainda anula tudo por redundancia.
 *
 * Na duvida (ambiente sem `matchMedia`, como o Node dos testes), responde
 * `false`: a ausencia da API nao e um pedido de reducao.
 */
export function prefereMenosMovimento(alvo?: AlvoComMatchMedia): boolean {
  const janela = alvo ?? (globalThis as AlvoComMatchMedia);
  if (typeof janela?.matchMedia !== "function") return false;
  return janela.matchMedia(CONSULTA_MENOS_MOVIMENTO).matches === true;
}

/**
 * Quando considerar que o elemento "entrou".
 *
 * `rootMargin` inferior negativo espera o elemento subir um pouco alem da
 * borda antes de revelar: revelar exatamente no limite faz a animacao
 * acontecer fora do campo de atencao e o usuario so ve o resultado.
 */
export const OPCOES_DO_OBSERVADOR: IntersectionObserverInit = {
  rootMargin: "0px 0px -12% 0px",
  threshold: 0.05,
};

/**
 * A revelacao pode ser armada neste ambiente?
 *
 * Separado do hook para ser testavel sem DOM. Reune as duas condicoes que
 * impedem armar: preferencia por menos movimento e ausencia da API.
 */
export function podeAnimarRevelacao(alvo?: AlvoComMatchMedia & { IntersectionObserver?: unknown }): boolean {
  const janela = alvo ?? (globalThis as AlvoComMatchMedia & { IntersectionObserver?: unknown });
  if (prefereMenosMovimento(janela)) return false;
  return typeof janela?.IntersectionObserver === "function";
}
