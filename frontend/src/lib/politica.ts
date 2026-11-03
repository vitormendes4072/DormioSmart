/**
 * A política de privacidade servida no app (LGPD-01 (b), 03/11).
 *
 * ── UMA FONTE SÓ ─────────────────────────────────────────────────────────
 *
 * O texto NÃO é copiado para o código: a página importa o próprio
 * `docs/POLITICA-DE-PRIVACIDADE.md` no build e mostra só o trecho entre as
 * linhas `── TEXTO` e `── FIM DO TEXTO`. Fora delas ficam as notas para o
 * autor ("Notas de levantamento", "Lacunas conhecidas"), que não são para o
 * titular. Uma cópia no código divergiria do documento em silêncio — o padrão
 * que este projeto já pagou várias vezes (§6 das lições).
 *
 * ── CONTROLADOR E CONTATO ────────────────────────────────────────────────
 *
 * O documento diz `[CONTROLADOR]` e `[CONTATO]`: o repositório é público e não
 * pode conter nome de pessoa (`CLAUDE.md`). Os valores vêm das variáveis de
 * build `VITE_POLITICA_CONTROLADOR` e `VITE_POLITICA_CONTATO`, definidas na
 * Vercel. Sem elas, a página diz que o dado ainda não foi informado — em vez
 * de mostrar o marcador cru ou um espaço vazio.
 */

const INICIO = "── TEXTO";
const FIM = "── FIM DO TEXTO";

export const NAO_INFORMADO = "(ainda não informado nesta versão preliminar)";

/** O trecho publicável: entre `── TEXTO` e `── FIM DO TEXTO`, sem as duas linhas. */
export function textoPublicavel(documento: string): string {
  const linhas = documento.replace(/\r\n/g, "\n").split("\n");
  const ini = linhas.findIndex((l) => l.startsWith(INICIO));
  const fim = linhas.findIndex((l) => l.startsWith(FIM));
  if (ini < 0 || fim < 0 || fim <= ini) {
    throw new Error("política sem os marcadores `── TEXTO` e `── FIM DO TEXTO`");
  }
  return linhas.slice(ini + 1, fim).join("\n").trim();
}

export type DadosDoControlador = { controlador?: string; contato?: string };

/** Troca `[CONTROLADOR]` e `[CONTATO]` pelos valores dados, ou pelo aviso. */
export function preencher(texto: string, dados: DadosDoControlador): string {
  const valor = (v?: string) => (v && v.trim() ? v.trim() : NAO_INFORMADO);
  return texto
    .split("[CONTROLADOR]").join(valor(dados.controlador))
    .split("[CONTATO]").join(valor(dados.contato));
}

/** Marcadores `[MAIUSCULAS]` que sobraram — o texto publicado não pode ter nenhum. */
export function marcadoresPendentes(texto: string): string[] {
  return [...new Set(texto.match(/\[[A-Z_]{3,}\]/g) ?? [])];
}
