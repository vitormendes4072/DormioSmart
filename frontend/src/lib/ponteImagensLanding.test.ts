// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";
import { iniciarPonteImagensLanding } from "./ponteImagensLanding";
const caminho = `/midia/landing/${"a".repeat(64)}.webp`;
let encerrar: (() => void) | undefined;
afterEach(() => { encerrar?.(); vi.restoreAllMocks(); document.body.innerHTML = ""; });
function preparar() {
  const iframe = document.createElement("iframe"); document.body.appendChild(iframe);
  const filho = iframe.contentWindow!;
  const enviar = vi.spyOn(filho, "postMessage").mockImplementation(() => undefined);
  const buscar = vi.fn().mockResolvedValue({ ok: true, headers: new Headers({ "content-type": "image/webp" }), arrayBuffer: async () => new Uint8Array([1, 2, 3]).buffer });
  encerrar = iniciarPonteImagensLanding(iframe, buscar as unknown as typeof fetch);
  return { filho, enviar, buscar };
}
describe("ponte de imagens da landing", () => {
  it("busca imagem pública solicitada pelo próprio iframe", async () => {
    const { filho, enviar, buscar } = preparar();
    window.dispatchEvent(new MessageEvent("message", { source: filho, data: { tipo: "dormio-imagem-pedido", id: 1, caminho } }));
    await vi.waitFor(() => expect(enviar).toHaveBeenCalledOnce());
    expect(buscar).toHaveBeenCalledWith(caminho, { credentials: "same-origin" });
    expect(enviar).toHaveBeenCalledWith(expect.objectContaining({ tipo: "dormio-imagem-resposta", id: 1, mime: "image/webp" }), "*");
  });
  it("recusa remetente desconhecido e caminhos que não são imagens permitidas", async () => {
    const { filho, enviar, buscar } = preparar();
    window.dispatchEvent(new MessageEvent("message", { source: window, data: { tipo: "dormio-imagem-pedido", id: 1, caminho } }));
    for (const invalido of ["/api/sleep-history", "https://outro.exemplo/icone-192.png", "/midia/landing/../segredo.webp", caminho + "?x=1"]) {
      window.dispatchEvent(new MessageEvent("message", { source: filho, data: { tipo: "dormio-imagem-pedido", id: 2, caminho: invalido } }));
    }
    await Promise.resolve(); expect(buscar).not.toHaveBeenCalled(); expect(enviar).not.toHaveBeenCalled();
  });
  it("recusa arquivos acima do limite permitido", async () => {
    const { filho, enviar, buscar } = preparar();
    buscar.mockResolvedValue({ ok: true, headers: new Headers({ "content-type": "image/webp" }), arrayBuffer: async () => new ArrayBuffer(256_001) });
    window.dispatchEvent(new MessageEvent("message", { source: filho, data: { tipo: "dormio-imagem-pedido", id: 4, caminho } }));
    await vi.waitFor(() => expect(buscar).toHaveBeenCalledOnce());
    await new Promise((resolve) => setTimeout(resolve, 0)); expect(enviar).not.toHaveBeenCalled();
  });
  it("recusa página de autenticação recebida no lugar da imagem", async () => {
    const { filho, enviar, buscar } = preparar();
    buscar.mockResolvedValue({ ok: true, headers: new Headers({ "content-type": "text/html" }), arrayBuffer: async () => new ArrayBuffer(3) });
    window.dispatchEvent(new MessageEvent("message", { source: filho, data: { tipo: "dormio-imagem-pedido", id: 3, caminho } }));
    await vi.waitFor(() => expect(buscar).toHaveBeenCalledOnce());
    await new Promise((resolve) => setTimeout(resolve, 0)); expect(enviar).not.toHaveBeenCalled();
  });
});
