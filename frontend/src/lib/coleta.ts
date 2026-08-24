import type { PayloadDeLeitura } from "./acelerometro";

/**
 * Envio da leitura coletada pelo celular (APP-01).
 *
 * ── POR QUE ISTO NAO USA `requisitarJson` ───────────────────────────────
 *
 * O cliente de API em `api.ts` carrega o JWT do usuario e trata 401 como
 * sessao expirada. A ingestao e o OUTRO caminho de autenticacao: token de
 * dispositivo em `X-Device-Token`, sem sessao. Sao credenciais deliberadamente
 * diferentes (ver DATA-CONTRACT secao 1), e misturar os dois clientes seria
 * apagar essa fronteira — um 401 de token de dispositivo derrubaria a sessao
 * do usuario, que nao tem nada a ver com isso.
 *
 * ── ONDE O TOKEN FICA ───────────────────────────────────────────────────
 *
 * Em `sessionStorage`, e nao em `localStorage`: some ao fechar a aba. O token
 * de dispositivo da DIREITO DE ESCRITA na conta, e num navegador nao existe
 * equivalente ao Keystore do Android. Reduzir a janela de exposicao e o que da
 * para fazer aqui; guardar em claro para sempre nao e. O armazenamento seguro
 * de verdade e o APP-03, e depende de app nativo.
 */

export const CHAVE_DO_TOKEN = "dormio.coleta.token";

export class ErroDeIngestao extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ErroDeIngestao";
  }
}

export function lerTokenGuardado(): string | null {
  try {
    return sessionStorage.getItem(CHAVE_DO_TOKEN);
  } catch {
    // Navegador com armazenamento bloqueado. A coleta ainda funciona: o
    // usuario cola o token a cada sessao.
    return null;
  }
}

export function guardarToken(token: string): void {
  try {
    sessionStorage.setItem(CHAVE_DO_TOKEN, token);
  } catch {
    /* sem armazenamento: segue sem persistir */
  }
}

export function esquecerToken(): void {
  try {
    sessionStorage.removeItem(CHAVE_DO_TOKEN);
  } catch {
    /* nada a fazer */
  }
}

/**
 * Mensagem para o usuario a partir do status da ingestao.
 *
 * Separada do envio para ser testavel, e porque 401 aqui significa uma coisa
 * bem especifica que merece texto proprio: o token esta errado ou foi
 * revogado — nao "sua sessao expirou".
 */
export function mensagemDeFalha(status: number): string {
  if (status === 401) return "Token do dispositivo invalido ou revogado.";
  if (status === 400) return "O servidor recusou a leitura como invalida.";
  if (status === 503) return "Servidor indisponivel. A leitura nao foi gravada.";
  if (status === 0) return "Sem conexao. A leitura nao foi gravada.";
  return `Falha ao enviar (erro ${status}).`;
}

/** Envia uma leitura. Lanca `ErroDeIngestao` em qualquer resposta que nao seja 201. */
export async function enviarLeitura(
  payload: PayloadDeLeitura,
  token: string,
): Promise<void> {
  let resposta: Response;
  try {
    resposta = await fetch("/api/data", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Device-Token": token,
      },
      body: JSON.stringify(payload),
    });
  } catch {
    throw new ErroDeIngestao(mensagemDeFalha(0), 0);
  }

  if (resposta.status !== 201) {
    throw new ErroDeIngestao(mensagemDeFalha(resposta.status), resposta.status);
  }
}
