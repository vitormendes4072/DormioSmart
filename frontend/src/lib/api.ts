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
/**
 * Quantas leituras o painel pede (DASH-13).
 *
 * ── O DEFEITO QUE ISTO CONSERTA ─────────────────────────────────────────
 *
 * O frontend nunca mandava `limite`, e o backend assume 20 (`LIMITE_PADRAO`
 * em `consulta.py`). Toda a maquina de cobertura, lacuna e sessao operava
 * sobre, no maximo, as 20 linhas mais recentes — **dez minutos de celular**.
 *
 * Nao era erro de matematica: era a tela nao ter os dados para os quais ela
 * foi feita. O card "Medido · N% de <janela>" e o seletor "Ver todas (N
 * sessoes)" descreviam esse recorte de dez minutos como se fosse a captacao
 * inteira, e nenhuma captura de tela de uma noite real era possivel.
 *
 * ── POR QUE 2000 ────────────────────────────────────────────────────────
 *
 * E o teto do backend (`LIMITE_MAXIMO`), e a conta fecha: uma noite de 8 h
 * agregada em epocas de 60 s da ~480 linhas; em epocas de 30 s, ~960. 2000
 * cobre a noite mais recente com folga para a anterior, que e o que o
 * seletor de sessao precisa para existir.
 *
 * Pedir mais exigiria paginacao — e paginar antes de haver uma noite real
 * gravada seria resolver um problema que ainda nao aconteceu.
 */
export const LIMITE_DO_PAINEL = 2000;

export type FiltroDeHistorico = {
  /** Recorta por instrumento. Ausente = todos os dispositivos do usuario. */
  dispositivo?: string | null;
  desde?: string | null;
  ate?: string | null;
  limite?: number | null;
};

/** Monta a query string, omitindo o que nao foi pedido.
 *
 * Exportada para teste: montar parametro errado e o tipo de bug que so
 * aparece em producao, como uma tela vazia sem explicacao.
 */
export function montarConsultaDeHistorico(filtro: FiltroDeHistorico = {}): string {
  const parametros = new URLSearchParams();
  if (filtro.dispositivo) parametros.set("device", filtro.dispositivo);
  if (filtro.desde) parametros.set("desde", filtro.desde);
  if (filtro.ate) parametros.set("ate", filtro.ate);
  if (filtro.limite != null) parametros.set("limite", String(filtro.limite));
  const query = parametros.toString();
  return query ? `/api/sleep-history?${query}` : "/api/sleep-history";
}

export async function buscarHistorico(filtro: FiltroDeHistorico = {}): Promise<LeituraSono[]> {
  const dados = await requisitarJson<unknown>(montarConsultaDeHistorico(filtro));
  return Array.isArray(dados) ? (dados as LeituraSono[]) : [];
}
