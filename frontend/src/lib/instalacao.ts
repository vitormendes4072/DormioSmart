/**
 * Registro do service worker (APP-07).
 *
 * Ele nao guarda cache — existe so porque o Chrome exige um manipulador de
 * `fetch` para oferecer a instalacao. A razao completa esta em
 * `public/sw.js`.
 *
 * ── FALHA EM SILENCIO, DE PROPOSITO ─────────────────────────────────────
 *
 * Service worker e recurso acessorio: sem ele o app funciona igual, apenas
 * nao oferece "Adicionar a tela inicial". Navegacao privada, navegador antigo
 * ou politica corporativa podem bloquear o registro, e nada disso deveria
 * aparecer como erro para quem so quer ver o painel.
 *
 * Tambem nao registra em desenvolvimento: um service worker ativo durante o
 * desenvolvimento e a forma mais rapida de passar meia hora depurando codigo
 * que ja foi corrigido.
 */

export function registrarServiceWorker(
  ehDesenvolvimento: boolean = import.meta.env.DEV,
): void {
  if (ehDesenvolvimento) return;
  if (typeof navigator === "undefined" || !("serviceWorker" in navigator)) return;

  // Depois do `load`: registrar durante o carregamento disputa banda com o
  // proprio app.
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {
      /* acessorio — ver a nota acima */
    });
  });
}
