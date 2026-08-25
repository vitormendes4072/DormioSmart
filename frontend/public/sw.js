/*
 * Service worker do Smart Dormio (APP-07).
 *
 * ── ELE NAO GUARDA NADA EM CACHE, E ISSO E DELIBERADO ───────────────────
 *
 * Existe por um motivo so: o Chrome exige um manipulador de `fetch` para
 * oferecer a instalacao do app. Sem ele, nao aparece "Adicionar a tela
 * inicial".
 *
 * Cache de service worker e a forma classica de servir codigo velho para
 * sempre: uma versao ruim gravada no cache do usuario sobrevive a deploys, e
 * o unico conserto e ele limpar os dados do site — que ninguem faz.
 *
 * Este app depende de rede em tudo que importa: leituras vem da API, a coleta
 * envia para a API, a sessao e validada no servidor. Guardar a casca offline
 * economizaria um carregamento e traria o risco inteiro. Nao paga.
 *
 * Cache de casca fica como item separado, se um dia fizer falta de verdade.
 *
 * `skipWaiting` + `clients.claim` para que uma versao nova assuma no primeiro
 * carregamento, em vez de esperar todas as abas fecharem.
 */

self.addEventListener("install", () => self.skipWaiting());

self.addEventListener("activate", (evento) => {
  evento.waitUntil(self.clients.claim());
});

// Repassa tudo para a rede, sem tocar. Ver a nota acima.
self.addEventListener("fetch", () => {});
