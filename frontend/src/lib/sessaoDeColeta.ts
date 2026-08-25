import type { Registro } from "../hooks/useColeta";

/**
 * Contas sobre uma sessao de coleta (APP-12).
 *
 * Funcoes puras para que o que a tela AFIRMA possa ser testado sem montar
 * tela — mesma escolha de `metricas.ts` e `consulta.py`.
 *
 * Existem porque a tela simplificada esconde a tabela de registros atras de
 * "detalhes tecnicos". Esconder detalhe e uma coisa; esconder PROBLEMA e
 * outra. Estas contas sao o que garante que uma falha continue aparecendo no
 * caminho principal.
 */

export type ResumoDaSessao = {
  /** Quantos registros a sessao produziu, em qualquer estado. */
  total: number;
  /** Ja confirmados no banco. */
  gravados: number;
  /** Ainda no ar. */
  enviando: number;
  /** Nao gravados. */
  falhas: number;
};

export function resumoDaSessao(registros: Registro[]): ResumoDaSessao {
  const resumo: ResumoDaSessao = { total: 0, gravados: 0, enviando: 0, falhas: 0 };
  for (const r of registros) {
    resumo.total += 1;
    if (r.envio === "gravada") resumo.gravados += 1;
    else if (r.envio === "enviando") resumo.enviando += 1;
    else resumo.falhas += 1;
  }
  return resumo;
}

/**
 * Quantos registros NAO foram gravados.
 *
 * Separado do resumo porque e a unica conta que a tela principal usa para
 * decidir se mostra alarme — e conta de alarme merece ser obvia no codigo.
 *
 * "Enviando" NAO conta como falha: a requisicao ainda esta no ar, e foi
 * exatamente essa confusao que produziu o defeito do APP-10.
 */
export function contarFalhas(registros: Registro[]): number {
  return registros.reduce((n, r) => n + (r.envio === "falhou" ? 1 : 0), 0);
}
