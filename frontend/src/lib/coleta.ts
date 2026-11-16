import type { PayloadDeLeitura } from "./acelerometro";
import { requisitarJson, urlDaApi } from "./api";
import type { Dispositivo } from "./dispositivos";

/**
 * Envio da leitura coletada pelo celular (APP-08).
 *
 * ── POR QUE NAO HA TOKEN AQUI ───────────────────────────────────────────
 *
 * Ate a versao anterior desta tela, o usuario tinha que parear um dispositivo
 * em Configuracoes, copiar um token de 43 caracteres e cola-lo aqui. Isso
 * existia porque o `X-Device-Token` nasceu para o ESP32 — e o ESP32 NAO TEM
 * LOGIN. Nao ha sessao, nao ha como renovar credencial; um segredo longo no
 * `secrets.h` e o que resta.
 *
 * O celular nao tem esse problema: quem abre esta tela ja esta autenticado.
 * Exigir a colagem do token era pedir que a pessoa fizesse a mao o que o
 * navegador ja tinha feito.
 *
 * E era pior que incomodo: punha uma credencial de ESCRITA dentro do
 * navegador, onde nao existe equivalente ao Keystore do Android. O melhor
 * possivel la era `sessionStorage`, que so encurta a janela de exposicao.
 *
 * Agora a ingestao aceita a sessao (contrato v2.2.0), e **nao ha token
 * nenhum no navegador**. Nao ha o que um XSS exfiltrar.
 *
 * O que o cliente informa e apenas QUAL dos seus dispositivos esta enviando.
 * O dono sai do JWT, no servidor, e o vinculo e conferido antes de gravar.
 */

export class ErroDeIngestao extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ErroDeIngestao";
  }
}

/**
 * Dispositivo `celular` deste usuario, criando na primeira vez.
 *
 * Create-or-get no servidor: uma chamada por sessao de coleta criando um
 * dispositivo novo encheria a conta de orfaos e tornaria o painel inutil.
 * A resposta nunca traz token.
 */
export function prepararDispositivoDoCelular(): Promise<Dispositivo> {
  return requisitarJson<Dispositivo>("/api/devices/celular", { method: "POST" });
}

/**
 * Mensagem para o usuario a partir do status da ingestao.
 *
 * Separada do envio para ser testavel, e porque cada status significa uma
 * coisa bem especifica que merece texto proprio.
 */
export function mensagemDeFalha(status: number): string {
  if (status === 401) return "Sua sessao expirou. Entre de novo para continuar.";
  if (status === 404) return "O dispositivo deste aparelho nao existe mais. Recarregue a pagina.";
  if (status === 400) return "O servidor recusou a leitura como invalida.";
  if (status === 503) return "Servidor indisponivel. A leitura nao foi gravada.";
  if (status === 0) return "Sem conexao. A leitura nao foi gravada.";
  return `Falha ao enviar (erro ${status}).`;
}

/**
 * Envia uma leitura autenticada pela sessao.
 *
 * Nao usa `requisitarJson` de proposito: aquele cliente trata 401 como sessao
 * expirada e dispara o callback que derruba o usuario para o login. Durante
 * uma coleta em andamento, um 401 transitorio nao deveria descartar a sessao
 * inteira sem aviso — a tela mostra a falha e deixa a pessoa decidir.
 */
export async function enviarLeitura(
  payload: PayloadDeLeitura,
  dispositivoId: string,
  jwt: string | null,
): Promise<void> {
  if (!jwt) throw new ErroDeIngestao(mensagemDeFalha(401), 401);

  let resposta: Response;
  try {
    resposta = await fetch(urlDaApi("/api/data"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${jwt}`,
      },
      body: JSON.stringify({ ...payload, device_id: dispositivoId }),
    });
  } catch {
    throw new ErroDeIngestao(mensagemDeFalha(0), 0);
  }

  if (resposta.status !== 201) {
    throw new ErroDeIngestao(mensagemDeFalha(resposta.status), resposta.status);
  }
}

// ── O lote da noite do app (APP-02, etapa 3) ─────────────────────────────

/** A resposta de `POST /api/data/lote` (contrato §5.2), pelo indice no array enviado. */
export type RespostaDoLote = {
  aceitas: number[];
  rejeitadas: { indice: number; erro: string }[];
  pendentes: number[];
};

/**
 * Envia até 60 épocas da noite numa requisição, autenticada pela sessão.
 *
 * Como o `enviarLeitura`, não passa pelo `requisitarJson`: um 401 aqui é a
 * sessão que venceu durante o envio, e a tela diz isso em vez de derrubar o
 * usuário para o login. 200 e 503 trazem as três listas; 503 é "nada
 * gravado, tudo pendente", e as listas dizem o mesmo.
 */
/**
 * Prazo de uma requisição de lote, da saída à leitura do corpo (APP-16).
 *
 * Os envios da noite são serializados por aparelho: um pedido que nunca
 * responde prenderia todas as tentativas seguintes, inclusive o "Enviar agora"
 * depois de sair da tela e voltar. Não há medição do tempo de um lote em
 * `gru1`; o servidor para de gravar aos 6 s (`ORCAMENTO_DE_TEMPO_S` em
 * `web-app/lote.py`), e o prazo dá dez vezes isso para partida a frio e rede
 * móvel lenta. Expirar é uma falha de envio comum: as épocas ficam no
 * aparelho, e o servidor deduplica um lote que tenha gravado (migração 011).
 */
export const PRAZO_DO_LOTE_MS = 60_000;

const MENSAGEM_DE_PRAZO = "O servidor nao respondeu a tempo. As epocas continuam no aparelho.";

export async function enviarLote(
  leituras: object[],
  dispositivoId: string,
  jwt: string | null,
): Promise<RespostaDoLote> {
  if (!jwt) throw new ErroDeIngestao(mensagemDeFalha(401), 401);

  // AbortController com setTimeout, e não AbortSignal.timeout: funciona em
  // WebView antiga e obedece ao relógio falso dos testes.
  const controle = new AbortController();
  const prazo = setTimeout(() => controle.abort(), PRAZO_DO_LOTE_MS);
  try {
    return await enviarLoteComSinal(leituras, dispositivoId, jwt, controle.signal);
  } catch (e) {
    if (controle.signal.aborted) throw new ErroDeIngestao(MENSAGEM_DE_PRAZO, 0);
    throw e;
  } finally {
    clearTimeout(prazo);
  }
}

async function enviarLoteComSinal(
  leituras: object[],
  dispositivoId: string,
  jwt: string,
  signal: AbortSignal,
): Promise<RespostaDoLote> {
  let resposta: Response;
  try {
    resposta = await fetch(urlDaApi("/api/data/lote"), {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${jwt}` },
      body: JSON.stringify({ device_id: dispositivoId, leituras }),
      signal,
    });
  } catch {
    throw new ErroDeIngestao(mensagemDeFalha(0), 0);
  }
  if (resposta.status !== 200 && resposta.status !== 503) {
    throw new ErroDeIngestao(mensagemDeFalha(resposta.status), resposta.status);
  }
  let corpo: unknown;
  try {
    corpo = await resposta.json();
  } catch {
    corpo = null;
  }
  const c = corpo as Partial<RespostaDoLote> | null;
  if (!c || !Array.isArray(c.aceitas) || !Array.isArray(c.rejeitadas) || !Array.isArray(c.pendentes)) {
    // Sem as listas não há como saber o que gravou: tudo pendente.
    if (resposta.status === 503) return { aceitas: [], rejeitadas: [], pendentes: leituras.map((_, i) => i) };
    throw new ErroDeIngestao("Resposta do servidor sem o resultado do lote.", resposta.status);
  }
  return { aceitas: c.aceitas, rejeitadas: c.rejeitadas, pendentes: c.pendentes };
}
