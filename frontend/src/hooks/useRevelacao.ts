import { useLayoutEffect, useRef } from "react";

import {
  CLASSE_ARMADO,
  CLASSE_VISIVEL,
  OPCOES_DO_OBSERVADOR,
  jaUltrapassado,
  podeAnimarRevelacao,
} from "../lib/animacao";

/**
 * Revela o elemento quando ele entra na janela (UI-15).
 *
 * `useLayoutEffect`, e nao `useEffect`, porque a classe que esconde precisa
 * estar aplicada ANTES da primeira pintura. Com `useEffect` o elemento
 * apareceria, sumiria e reapareceria — um piscar visivel no que esta acima
 * da dobra.
 *
 * Revela uma vez so. Reanimar a cada rolagem transforma leitura em desfile:
 * quem volta ao topo da pagina quer reler o texto, nao assistir de novo.
 *
 * `ativo` existe para que componentes compartilhados (a `Moldura`, usada
 * tambem fora da landing) so animem onde a animacao foi pedida. Como hook nao
 * pode ser condicional, a decisao entra por parametro.
 *
 * ── A RESTAURACAO DE ROLAGEM (UI-16) ────────────────────────────────────
 *
 * Defeito observado em producao: recarregar a pagina no meio dela deixava
 * todo o conteudo acima da janela permanentemente invisivel.
 *
 * A causa e a ordem dos eventos. Numa SPA, a pagina nasce sem altura, entao
 * o navegador so consegue restaurar a rolagem depois que o React monta. Nesse
 * instante a rolagem ainda esta em zero, e o hook arma todos os blocos. A
 * restauracao acontece em seguida e joga a janela para o meio da pagina. O
 * IntersectionObserver entrega entao a primeira leitura — ja na posicao nova —
 * e os blocos que ficaram acima simplesmente nao intersectam. Pior: eles nunca
 * mais vao gerar callback, porque rolar de 0 para 0 nao e mudanca de
 * intersecao. Ficam escondidos ate o usuario voltar ao topo.
 *
 * Duas defesas, porque as duas ordens acontecem:
 *
 * 1. Na montagem — cobre quando a rolagem JA foi restaurada antes do React
 *    montar (navegacao de volta, bfcache). Bloco acima da janela nem chega a
 *    ser armado: nasce visivel, sem transicao.
 * 2. Depois da carga E no primeiro `scroll` — cobre a ordem inversa, que e a
 *    de producao. Dois gatilhos porque nao ha garantia de quando o navegador
 *    aplica a restauracao: `load` pega o caso comum, o primeiro `scroll` pega
 *    qualquer momento. Ambos de uma vez so, nada de listener permanente.
 *
 * Nos dois casos o bloco ultrapassado aparece sem animacao, e nao com ela.
 * Quem recarrega no meio da pagina e volta ao topo esta relendo — releitura
 * nao e desfile.
 */
export function useRevelacao<T extends HTMLElement>(atrasoEmMs = 0, ativo = true) {
  const ref = useRef<T>(null);

  useLayoutEffect(() => {
    const elemento = ref.current;
    if (!elemento || !ativo) return;

    // Sem condicoes de animar, o elemento fica como o CSS o deixou: visivel.
    if (!podeAnimarRevelacao()) return;

    // Defesa 1: a rolagem ja estava restaurada quando montamos.
    if (jaUltrapassado(elemento.getBoundingClientRect())) return;

    elemento.classList.add(CLASSE_ARMADO);
    if (atrasoEmMs > 0) elemento.style.transitionDelay = `${atrasoEmMs}ms`;

    const observador = new IntersectionObserver((entradas) => {
      for (const entrada of entradas) {
        if (!entrada.isIntersecting) continue;
        entrada.target.classList.add(CLASSE_VISIVEL);
        observador.unobserve(entrada.target);
      }
    }, OPCOES_DO_OBSERVADOR);

    observador.observe(elemento);

    // Defesa 2: a rolagem foi restaurada DEPOIS de montarmos — a ordem de
    // producao. Sem transicao: o bloco ja deveria estar lido a esta altura.
    const encerrar: (() => void)[] = [];

    const conferir = () => {
      if (!jaUltrapassado(elemento.getBoundingClientRect())) return;
      elemento.style.transitionDelay = "";
      elemento.classList.remove(CLASSE_ARMADO);
      observador.unobserve(elemento);
    };

    // Dois gatilhos, porque nao ha garantia de quando o navegador aplica a
    // restauracao. `load` cobre o caso comum; o primeiro `scroll` cobre
    // qualquer momento — inclusive uma restauracao tardia. Os dois sao de uma
    // vez so, e `conferir` nao faz nada quando nao ha o que corrigir.
    const aoCarregar = () => {
      const quadro = requestAnimationFrame(conferir);
      encerrar.push(() => cancelAnimationFrame(quadro));
    };

    if (document.readyState === "complete") aoCarregar();
    else {
      window.addEventListener("load", aoCarregar, { once: true });
      encerrar.push(() => window.removeEventListener("load", aoCarregar));
    }

    window.addEventListener("scroll", conferir, { once: true, passive: true });
    encerrar.push(() => window.removeEventListener("scroll", conferir));

    return () => {
      observador.disconnect();
      for (const parar of encerrar) parar();
    };
  }, [atrasoEmMs, ativo]);

  return ref;
}
