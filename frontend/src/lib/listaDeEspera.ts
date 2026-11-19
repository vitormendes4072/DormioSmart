import { ErroApi, requisitarJson } from "./api";

/**
 * A lista de espera do lançamento (UI-14).
 *
 * Quem ainda não tem conta deixa o e-mail para ser avisado do lançamento e
 * convidado para os primeiros testes. A garantia é do banco (migração 022):
 * ninguém do cliente lê a lista, a escrita só passa pela função de inscrição,
 * e o teto de inscrições por hora vive lá. O backend valida de novo tudo o que
 * esta tela valida.
 *
 * `VERSAO_DA_LISTA` é a mesma de `public.versao_da_lista_de_espera()` e de
 * `web-app/lista_de_espera.py`; `web-app/tests/test_lista_de_espera.py` confere
 * as três. **Mudar o texto do consentimento é mudar a versão nos três lugares.**
 */
export const VERSAO_DA_LISTA = "2026-11-19";

/** O texto da confirmação, como a tela mostra e a pessoa aceita. */
export const TEXTO_DO_CONSENTIMENTO_DA_LISTA =
  "Concordo que o Smart Dormio guarde meu e-mail (e o nome, se eu informar) só para me avisar do " +
  "lançamento e me convidar para os primeiros testes. Posso sair da lista quando quiser.";

/** O mesmo formato que o backend e o banco aceitam. */
const FORMATO_DO_EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/;
const EMAIL_MAX = 254;
export const NOME_MAX = 80;

export function emailValido(email: string): boolean {
  const limpo = email.trim().toLowerCase();
  return limpo.length <= EMAIL_MAX && FORMATO_DO_EMAIL.test(limpo);
}

/**
 * Os domínios mais comuns no Brasil. Um erro de digitação num deles é o
 * contato perdido de vez: o aviso do lançamento nunca chega.
 */
const DOMINIOS_COMUNS = [
  "gmail.com", "hotmail.com", "outlook.com", "yahoo.com", "yahoo.com.br",
  "icloud.com", "live.com", "uol.com.br", "bol.com.br", "terra.com.br",
];

function distancia(a: string, b: string): number {
  const linhas = Array.from({ length: a.length + 1 }, (_, i) => [i]);
  for (let j = 1; j <= b.length; j++) linhas[0][j] = j;
  for (let i = 1; i <= a.length; i++) {
    for (let j = 1; j <= b.length; j++) {
      linhas[i][j] = Math.min(
        linhas[i - 1][j] + 1,
        linhas[i][j - 1] + 1,
        linhas[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1),
      );
    }
  }
  return linhas[a.length][b.length];
}

/**
 * O e-mail com o domínio corrigido quando ele está a uma ou duas letras de um
 * domínio comum (`gmial.com` → `gmail.com`); `null` quando não há sugestão.
 * É só sugestão: a tela pergunta, nunca corrige sozinha.
 */
export function sugerirEmail(email: string): string | null {
  const limpo = email.trim().toLowerCase();
  const arroba = limpo.lastIndexOf("@");
  if (arroba < 1) return null;
  const dominio = limpo.slice(arroba + 1);
  if (!dominio || DOMINIOS_COMUNS.includes(dominio)) return null;
  let melhor: { dominio: string; distancia: number } | null = null;
  for (const candidato of DOMINIOS_COMUNS) {
    const d = distancia(dominio, candidato);
    if (d > 0 && d <= 2 && (!melhor || d < melhor.distancia)) melhor = { dominio: candidato, distancia: d };
  }
  return melhor ? limpo.slice(0, arroba + 1) + melhor.dominio : null;
}

type Inscricao = {
  email: string;
  nome: string;
  consentimento: boolean;
  maioridade: boolean;
  /** O campo-isca. Uma pessoa não o vê; quem o preenche é descartado pelo servidor. */
  site: string;
};

export type ResultadoDaInscricao =
  | { tipo: "inscrito" }
  | { tipo: "lista_cheia" }
  | { tipo: "texto_mudou" }
  | { tipo: "invalido"; mensagem: string }
  | { tipo: "indisponivel" };

/** Envia a inscrição e traduz a resposta para o que a tela precisa mostrar. */
export async function inscreverNaListaDeEspera(inscricao: Inscricao): Promise<ResultadoDaInscricao> {
  try {
    await requisitarJson<{ status: string }>("/api/lista-de-espera", {
      method: "POST",
      body: JSON.stringify({
        email: inscricao.email.trim(),
        nome: inscricao.nome.trim() || null,
        consentimento: inscricao.consentimento,
        maioridade: inscricao.maioridade,
        versao: VERSAO_DA_LISTA,
        site: inscricao.site,
      }),
    });
    return { tipo: "inscrito" };
  } catch (erro) {
    if (!(erro instanceof ErroApi)) return { tipo: "indisponivel" };
    if (erro.status === 429) return { tipo: "lista_cheia" };
    if (erro.status === 409) return { tipo: "texto_mudou" };
    if (erro.status === 400) return { tipo: "invalido", mensagem: erro.message };
    return { tipo: "indisponivel" };
  }
}
