/**
 * Eliminação da conta do titular (UI-10 / SEC-07 / LGPD art. 18, V).
 *
 * A rota `DELETE /api/me` existe desde o SEC-07. Este módulo é o lado do
 * cliente dela, e existe separado de `api.ts` por uma razão que não é
 * organização: **a resposta 200 desta rota pode significar sucesso parcial**, e
 * interpretar isso é regra de negócio, não transporte.
 *
 * ── O CASO QUE NÃO PODE SER TRATADO COMO SUCESSO ────────────────────────
 *
 * O recibo traz `conta_de_acesso_removida`. Quando ele é `false`, os dados de
 * sono, os dispositivos e o perfil saíram, mas a linha de `auth.users` — que
 * guarda o **e-mail** — permaneceu, porque o privilégio de `DELETE` nela
 * pertence ao Supabase e não existe em todo projeto (ver o cabeçalho de
 * `web-app/migrations/006_direito_de_eliminacao.sql`).
 *
 * Isso é HTTP 200. Um cliente ingênuo mostraria "conta excluída" e estaria
 * mentindo para alguém que acabou de exercer um direito — sobre dado pessoal
 * que ainda existe. Por isso o resultado aqui tem **três** estados, não dois,
 * e o estado do meio tem nome próprio.
 */
import { ErroApi, requisitarJson } from "./api";

/**
 * A frase exata exigida pelo backend (`CONFIRMACAO_EXCLUSAO` em `routes.py`).
 *
 * Em português e em maiúsculas de propósito: tem de ser DIGITADA. É a única
 * barreira entre um `DELETE` disparado por engano — retry automático de cliente
 * HTTP, clique duplo, fetch repetido por hot reload — e a perda definitiva do
 * histórico. Nenhum desses digita a frase.
 */
export const FRASE_DE_CONFIRMACAO = "APAGAR MINHA CONTA";

/** Recibo devolvido pelo backend no 200 (contrato, seção 6.2). */
export type ReciboDeExclusao = {
  leituras_apagadas: number;
  dispositivos_apagados: number;
  perfil_apagado: boolean;
  conta_de_acesso_removida: boolean;
  /** Presente só quando a eliminação foi parcial. */
  aviso?: string;
};

export type ResultadoDeExclusao =
  | { tipo: "completa"; recibo: ReciboDeExclusao }
  /** O dado de `public` saiu; o cadastro de acesso (e-mail) permaneceu. */
  | { tipo: "parcial"; recibo: ReciboDeExclusao; aviso: string };

/**
 * Confere a frase ANTES de chamar a rede.
 *
 * Não é validação duplicada por desconfiança do backend: é para que o erro de
 * digitação apareça como erro de digitação, e não como um 400 vindo do
 * servidor depois de uma ida à rede. O backend continua conferindo, e ele é
 * quem manda — esta função não dispensa aquela.
 *
 * Comparação EXATA, sem `trim` e sem ignorar caixa. Aceitar "apagar minha
 * conta " enfraqueceria justamente a barreira que a frase é: quanto mais
 * tolerante a conferência, mais perto ela fica de um clique.
 */
export function confirmacaoValida(texto: string): boolean {
  return texto === FRASE_DE_CONFIRMACAO;
}

/**
 * Executa a eliminação.
 *
 * Lança `ErroApi` nos casos de falha (400, 401, 503, rede). Devolve
 * `ResultadoDeExclusao` nos casos em que o backend executou — inclusive quando
 * executou pela metade.
 */
export async function excluirMinhaConta(confirmacao: string): Promise<ResultadoDeExclusao> {
  if (!confirmacaoValida(confirmacao)) {
    // 400 é o mesmo status que o backend usaria. Mantemos o código para que a
    // UI trate os dois caminhos do mesmo jeito.
    throw new ErroApi(400, `Digite exatamente: ${FRASE_DE_CONFIRMACAO}`);
  }

  const recibo = await requisitarJson<ReciboDeExclusao>("/api/me", {
    method: "DELETE",
    body: JSON.stringify({ confirmacao }),
  });

  return interpretarRecibo(recibo);
}

/**
 * Traduz o recibo em um dos três desfechos.
 *
 * Exportada para ser testável sem rede, e porque é aqui que mora a decisão que
 * o item existe para acertar: **não inventar sucesso onde a rota reportou
 * remoção parcial**.
 */
export function interpretarRecibo(recibo: ReciboDeExclusao): ResultadoDeExclusao {
  if (recibo?.conta_de_acesso_removida === true) {
    return { tipo: "completa", recibo };
  }

  // Qualquer coisa que não seja `true` é tratada como parcial — inclusive
  // `undefined`, que é o que viria de um backend antigo ou de um corpo
  // truncado. O padrão seguro aqui é o pessimista: afirmar remoção completa
  // sem o campo confirmando seria exatamente o erro que este módulo evita.
  const aviso =
    recibo?.aviso ??
    "Seus dados de sono, dispositivos e perfil foram apagados. O cadastro de " +
      "acesso (e-mail) ainda existe e precisa ser removido pelo administrador.";

  return { tipo: "parcial", recibo, aviso };
}

/**
 * Resumo em linguagem natural do que saiu, para o recibo na tela.
 *
 * Números concretos em vez de "seus dados foram apagados": quem acabou de
 * apagar uma noite de captação tem o direito de ver quantas linhas eram.
 */
export function descreverRecibo(recibo: ReciboDeExclusao): string {
  const partes: string[] = [];

  const n = recibo?.leituras_apagadas ?? 0;
  partes.push(n === 1 ? "1 leitura" : `${n.toLocaleString("pt-BR")} leituras`);

  const d = recibo?.dispositivos_apagados ?? 0;
  partes.push(d === 1 ? "1 dispositivo" : `${d} dispositivos`);

  if (recibo?.perfil_apagado) partes.push("o perfil");

  return partes.join(", ").replace(/, ([^,]*)$/, " e $1");
}
