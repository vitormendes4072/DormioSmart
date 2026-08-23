import { useLayoutEffect, useRef } from "react";

import {
  CLASSE_ARMADO,
  CLASSE_VISIVEL,
  OPCOES_DO_OBSERVADOR,
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
 */
export function useRevelacao<T extends HTMLElement>(atrasoEmMs = 0, ativo = true) {
  const ref = useRef<T>(null);

  useLayoutEffect(() => {
    const elemento = ref.current;
    if (!elemento || !ativo) return;

    // Sem condicoes de animar, o elemento fica como o CSS o deixou: visivel.
    if (!podeAnimarRevelacao()) return;

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
    return () => observador.disconnect();
  }, [atrasoEmMs, ativo]);

  return ref;
}
