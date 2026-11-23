// APP-19: o app descobre se há versão nova publicada.
//
// A versão publicada está em `public/versao-do-app.json`, servido pelo site junto com a landing:
// vai ao ar no mesmo deploy que põe o APK novo no botão de download. O app lê esse arquivo pelo
// mesmo endereço do backend (no app, o `fetch` vai pelo HTTP nativo, sem CORS) e compara com a
// própria versão. Sem internet, ou com qualquer resposta estranha, a resposta é "não sei", e o
// aviso simplesmente não aparece: nunca trava a tela.
import { urlDaApi } from "./api";

export const CAMINHO_DA_VERSAO_PUBLICADA = "/versao-do-app.json";

const FORMATO = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/;

export function versaoValida(valor: unknown): valor is string {
  return typeof valor === "string" && FORMATO.test(valor);
}

/** Negativo se `a` é mais antiga, zero se iguais, positivo se mais nova. Compara número a número. */
export function compararVersoes(a: string, b: string): number {
  const pa = FORMATO.exec(a);
  const pb = FORMATO.exec(b);
  if (!pa || !pb) throw new Error("versão fora do formato");
  for (let i = 1; i <= 3; i++) {
    const d = Number(pa[i]) - Number(pb[i]);
    if (d !== 0) return d;
  }
  return 0;
}

/** A versão publicada, ou null se não deu para saber. */
export async function buscarVersaoPublicada(buscar: typeof fetch = fetch): Promise<string | null> {
  try {
    const resposta = await buscar(urlDaApi(CAMINHO_DA_VERSAO_PUBLICADA), { cache: "no-store" });
    if (!resposta.ok) return null;
    const corpo: unknown = await resposta.json();
    const versao = (corpo as { versao?: unknown } | null)?.versao;
    return versaoValida(versao) ? versao : null;
  } catch {
    return null;
  }
}

/** A versão nova a anunciar, ou null se a instalada já é a mais nova (ou não deu para saber). */
export function versaoParaAtualizar(instalada: string, publicada: string | null): string | null {
  if (publicada === null || !versaoValida(instalada)) return null;
  return compararVersoes(publicada, instalada) > 0 ? publicada : null;
}
