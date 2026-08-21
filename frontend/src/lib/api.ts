/**
 * Cliente da API do Smart Dormio.
 *
 * Todo acesso a `/api/*` passa por aqui. Em desenvolvimento o Vite faz proxy
 * para o Flask local (ver vite.config.ts); em producao quem roteia e o
 * vercel.json (UI-08). Por isso os caminhos sao sempre relativos.
 */
import type { LeituraSono } from "../types/sleep";

/** Erro de API com o status HTTP preservado, para a UI decidir o que fazer
 *  (401 leva ao login, 503 e falha temporaria, etc.). */
export class ErroApi extends Error {
  readonly status: number;

  constructor(status: number, mensagem: string) {
    super(mensagem);
    this.name = "ErroApi";
    this.status = status;
  }

  get naoAutorizado() {
    return this.status === 401;
  }
}

/**
 * Fonte do JWT da sessao.
 *
 * Fica como funcao injetavel para que este modulo nao dependa do Supabase: o
 * AUTH-01 registra o provedor de verdade sem tocar neste arquivo. Enquanto
 * isso nao acontece, devolve null e as requisicoes seguem sem Authorization —
 * o backend responde 401, que e o comportamento correto e honesto.
 */
type ProvedorDeToken = () => string | null;

let obterToken: ProvedorDeToken = () => null;

export function definirProvedorDeToken(provedor: ProvedorDeToken) {
  obterToken = provedor;
}

/** Callback disparado em 401, registrado pelo AUTH-04 para levar ao login. */
let aoPerderSessao: (() => void) | null = null;

export function definirCallbackDeSessaoExpirada(callback: () => void) {
  aoPerderSessao = callback;
}

/**
 * Requisicao autenticada a API, com resposta JSON.
 *
 * Exportada a partir do AUTH-05: alem da leitura do historico, o app passou a
 * criar, renomear e revogar dispositivos. Toda chamada a `/api/*` passa por
 * aqui para que a injecao do JWT e o tratamento de 401 sejam automaticos.
 */
export async function requisitarJson<T>(caminho: string, opcoes: RequestInit = {}): Promise<T> {
  const cabecalhos = new Headers(opcoes.headers);
  cabecalhos.set("Accept", "application/json");
  // O backend so aceita JSON; definir aqui evita repetir em cada chamada.
  if (opcoes.body && !cabecalhos.has("Content-Type")) {
    cabecalhos.set("Content-Type", "application/json");
  }

  const token = obterToken();
  if (token) cabecalhos.set("Authorization", `Bearer ${token}`);

  let resposta: Response;
  try {
    resposta = await fetch(caminho, { ...opcoes, headers: cabecalhos });
  } catch {
    // Falha de rede nao tem status HTTP. Usamos 0 para distinguir de qualquer
    // resposta real do servidor.
    throw new ErroApi(0, "Nao foi possivel conectar ao servidor.");
  }

  if (resposta.status === 401) {
    aoPerderSessao?.();
    throw new ErroApi(401, "Sessao expirada. Entre novamente.");
  }

  if (!resposta.ok) {
    throw new ErroApi(resposta.status, await extrairMensagemDeErro(resposta));
  }

  return (await resposta.json()) as T;
}

/** O backend devolve `{"error": "..."}` nas falhas (ver contrato, secao 5).
 *  Se o corpo nao for JSON, cai para uma mensagem generica em vez de estourar. */
async function extrairMensagemDeErro(resposta: Response): Promise<string> {
  try {
    const corpo = (await resposta.json()) as { error?: string };
    if (corpo?.error) return corpo.error;
  } catch {
    // corpo vazio ou nao-JSON — segue para a mensagem generica
  }
  return `Erro ${resposta.status} ao falar com o servidor.`;
}

/**
 * Historico de leituras do usuario autenticado, mais recentes primeiro.
 *
 * O backend garante array — nunca 500 (FIX-01). Ainda assim conferimos o tipo:
 * a UI quebraria feio se viesse outra coisa, e o custo da checagem e zero.
 */
export async function buscarHistorico(): Promise<LeituraSono[]> {
  const dados = await requisitarJson<unknown>("/api/sleep-history");
  return Array.isArray(dados) ? (dados as LeituraSono[]) : [];
}
