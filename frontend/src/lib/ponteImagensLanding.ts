/** Recupera apenas imagens públicas da landing para o iframe de origem opaca.
 * Em previews protegidos, o iframe sem allow-same-origin não envia o cookie
 * SameSite ao buscar sub-recursos; o documento pai pode buscá-los com sessão.
 */
const CAMINHO_PERMITIDO = /^\/(?:icone-192\.png|midia\/landing\/[a-f0-9]{64}\.webp)$/;
const TAMANHO_MAXIMO = 256_000;

type Pedido = { tipo?: unknown; id?: unknown; caminho?: unknown };

export function iniciarPonteImagensLanding(
  iframe: HTMLIFrameElement,
  buscar: typeof fetch = fetch,
): () => void {
  let ativa = true;
  const cache = new Map<string, Promise<{ bytes: ArrayBuffer; mime: string } | null>>();

  function carregar(caminho: string) {
    let pendente = cache.get(caminho);
    if (!pendente) {
      pendente = (async () => {
        try {
          const resposta = await buscar(caminho, { credentials: "same-origin" });
          const mime = resposta.headers.get("content-type")?.split(";")[0].trim().toLowerCase();
          if (!resposta.ok || (mime !== "image/webp" && mime !== "image/png")) return null;
          const bytes = await resposta.arrayBuffer();
          if (!bytes.byteLength || bytes.byteLength > TAMANHO_MAXIMO) return null;
          return { bytes, mime };
        } catch {
          return null;
        }
      })().then((imagem) => {
        if (!imagem) cache.delete(caminho);
        return imagem;
      });
      cache.set(caminho, pendente);
    }
    return pendente;
  }

  const receber = (evento: MessageEvent<Pedido>) => {
    const janela = iframe.contentWindow;
    const pedido = evento.data;
    if (!janela || evento.source !== janela || !pedido || pedido.tipo !== "dormio-imagem-pedido" ||
        typeof pedido.id !== "number" || !Number.isSafeInteger(pedido.id) || pedido.id < 1 ||
        typeof pedido.caminho !== "string" || !CAMINHO_PERMITIDO.test(pedido.caminho)) return;
    const id = pedido.id;
    void carregar(pedido.caminho).then((imagem) => {
      if (ativa && imagem && iframe.contentWindow === janela) {
        janela.postMessage({ tipo: "dormio-imagem-resposta", id, ...imagem }, "*");
      }
    });
  };
  window.addEventListener("message", receber);
  return () => { ativa = false; window.removeEventListener("message", receber); };
}
