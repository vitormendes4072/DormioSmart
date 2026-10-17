/**
 * Correção dos dados de perfil (UI-11 / LGPD art. 18, III).
 *
 * A `docs/POLITICA-DE-PRIVACIDADE.md` §6.3 teve de declarar que **não há tela
 * para corrigir nome e e-mail** — o app os exibia e mais nada —, e o art. 18,
 * III assegura a correção de dado incompleto, inexato ou desatualizado. Este
 * módulo é o lado de lógica dessa tela.
 *
 * ── ONDE O NOME MORA, QUE NÃO É ONDE O BACKLOG DIZIA ────────────────────
 *
 * O `UI-11` estava especificado assim: *"Barato: a policy de `update` em
 * `profiles` já existe desde a migração `001`; falta a interface."* **A
 * premissa está errada, e foi conferida no artefato antes de escrever isto.**
 *
 * - Nenhum código de produção toca `public.profiles`. As únicas referências no
 *   repositório estão em `web-app/tests/rls/`.
 * - O nome que a tela de Configurações exibe vem de
 *   `usuario.user_metadata.nome`, isto é, de `auth.users.raw_user_meta_data`.
 * - `profiles.nome` é uma **cópia tirada uma vez** pelo trigger
 *   `handle_new_user` (migração `001`, linha 125) a partir daquele metadado no
 *   signup, e **nunca é lida por nada**.
 *
 * Portanto: escrever em `profiles` pela policy existente **não mudaria uma
 * letra em tela nenhuma**. A correção que o titular pede tem de acontecer no
 * Supabase Auth, que é onde o dado efetivamente consumido mora. É o que este
 * módulo faz.
 *
 * ⚠️ **Consequência declarada, e não resolvida aqui:** depois desta tela,
 * `profiles.nome` passa a ser uma cópia que pode divergir do nome real. Não
 * escrevo nela de passagem — decidir para que a tabela `profiles` existe é o
 * item `PERFIL-01`, com três saídas e custo medido. Sincronizar agora, sem
 * essa decisão, criaria um segundo caminho de escrita para um dado que ninguém
 * lê, e tornaria impossível dizer depois qual dos dois lados está certo.
 *
 * ── POR QUE O E-MAIL TEM UM DESFECHO PRÓPRIO ────────────────────────────
 *
 * Nome e e-mail parecem dois campos do mesmo formulário e **não são a mesma
 * operação**. O nome é metadado: muda na hora. O e-mail é credencial de
 * acesso: o Supabase não o troca na resposta — manda link de confirmação e
 * mantém o endereço antigo até alguém clicar (e, conforme a configuração do
 * projeto, pode exigir confirmação **também no endereço atual**).
 *
 * Mostrar "e-mail alterado" ao receber a resposta seria confirmação emitida
 * antes da verificação — o §6 de `docs/LICOES-APRENDIDAS.md`, que este projeto
 * já pagou três vezes. Por isso há um estado `email-pendente` com nome
 * próprio, e a interpretação é **pessimista por omissão**: só dizemos que o
 * e-mail trocou quando a resposta do servidor **prova** que trocou.
 *
 * ── E POR QUE SÃO DUAS CHAMADAS, E NÃO UMA ──────────────────────────────
 *
 * `updateUser` aceita `{ data, email }` de uma vez. Separado de propósito: com
 * uma chamada só, uma falha no e-mail devolveria erro para a operação inteira,
 * e o nome — que já teria sido gravado — apareceria como não gravado. O
 * resultado aqui carrega `nomeAlterado` em **todos** os desfechos, inclusive
 * no de erro, justamente para que nenhum deles minta sobre o que já aconteceu.
 */
import type { User } from "@supabase/supabase-js";

import { traduzirErroDeAuth } from "./autenticacao";
import { obterSupabase } from "./supabase";

/**
 * Teto de caracteres do nome.
 *
 * ⚙️ **Decisão de interface, não limite de banco.** `profiles.nome` é `text`
 * (migração `001`, linha 20) e `raw_user_meta_data` é JSON: nenhum dos dois
 * impõe teto. O número existe para o nome não arrebentar o cabeçalho e para a
 * mensagem de erro aparecer antes da ida à rede. Marcado como decisão para não
 * ganhar, com o tempo, uma procedência que não tem (§3 das lições).
 */
export const NOME_MAXIMO_DO_PERFIL = 120;

export type DadosDoPerfil = { nome: string; email: string };

/** O que de fato mudou em relação ao que está na sessão. */
export type AlteracaoDePerfil = { nome?: string; email?: string };

export type ResultadoDePerfil =
  /** O formulário não mudou nada. Não houve ida à rede. */
  | { tipo: "nada-a-fazer" }
  /** Tudo que foi pedido já vale agora. */
  | { tipo: "salvo"; nomeAlterado: boolean }
  /** O e-mail depende de confirmação; o endereço de acesso segue o antigo. */
  | { tipo: "email-pendente"; emailPendente: string; nomeAlterado: boolean }
  | { tipo: "invalido"; mensagem: string }
  | { tipo: "erro"; mensagem: string; nomeAlterado: boolean };

const SEM_CONFIGURACAO = "Autenticação não configurada. Confira o arquivo frontend/.env.";

/**
 * Nome exibível a partir da sessão.
 *
 * Mesma leitura que a seção "Conta" já fazia, extraída para cá para que a tela
 * de edição e a de exibição não possam discordar sobre de onde vem o nome.
 */
export function nomeDaSessao(usuario: User | null): string {
  const bruto = usuario?.user_metadata?.nome;
  return typeof bruto === "string" ? bruto.trim() : "";
}

/** E-mail de acesso a partir da sessão. */
export function emailDaSessao(usuario: User | null): string {
  return typeof usuario?.email === "string" ? usuario.email : "";
}

/**
 * Normaliza o nome: tira as pontas e colapsa espaço interno.
 *
 * Colapsar o meio importa porque "Ana  Maria" e "Ana Maria" são o mesmo nome
 * para quem digitou, e sem isso o formulário detectaria mudança onde não houve
 * e mandaria uma escrita à toa.
 */
export function normalizarNome(texto: string): string {
  return texto.trim().replace(/\s+/g, " ");
}

/**
 * Normaliza o e-mail: tira as pontas e baixa a caixa.
 *
 * O Supabase guarda e compara e-mail em minúsculas. Sem baixar a caixa aqui,
 * digitar "Ana@x.com" sobre "ana@x.com" pareceria uma alteração e dispararia
 * um fluxo de confirmação que não troca nada.
 */
export function normalizarEmail(texto: string): string {
  return texto.trim().toLowerCase();
}

export function validarNome(texto: string): { ok: true } | { ok: false; motivo: string } {
  const nome = normalizarNome(texto);
  if (nome === "") return { ok: false, motivo: "O nome não pode ficar vazio." };
  if (nome.length > NOME_MAXIMO_DO_PERFIL) {
    return {
      ok: false,
      motivo: `O nome precisa ter no máximo ${NOME_MAXIMO_DO_PERFIL} caracteres.`,
    };
  }
  return { ok: true };
}

/**
 * Confere o e-mail ANTES de ir à rede.
 *
 * Deliberadamente frouxo. Não é tentativa de validar e-mail de verdade — isso
 * não se faz com regex, e quem manda é o servidor, que continua conferindo.
 * O objetivo é só que um erro de digitação óbvio ("ana@", "ana.com") apareça
 * como erro de digitação, e não como um fluxo de confirmação disparado para um
 * endereço que não existe. Mesma divisão de responsabilidade do
 * `confirmacaoValida` do `UI-10`.
 */
export function validarEmail(texto: string): { ok: true } | { ok: false; motivo: string } {
  const email = normalizarEmail(texto);
  if (email === "") return { ok: false, motivo: "O e-mail não pode ficar vazio." };
  if (/\s/.test(email)) return { ok: false, motivo: "O e-mail não pode conter espaços." };
  const partes = email.split("@");
  if (partes.length !== 2 || partes[0] === "" || !partes[1].includes(".")) {
    return { ok: false, motivo: "E-mail inválido." };
  }
  if (partes[1].startsWith(".") || partes[1].endsWith(".")) {
    return { ok: false, motivo: "E-mail inválido." };
  }
  return { ok: true };
}

/**
 * O que mudou entre a sessão e o formulário.
 *
 * Existe para que "salvar" sem ter mexido em nada **não** escreva nada. Num
 * formulário de perfil isso não é otimização: mandar o e-mail atual como se
 * fosse novo dispararia um pedido de confirmação para trocar um endereço pelo
 * mesmo endereço, e a pessoa receberia um e-mail dizendo que sua credencial
 * está mudando.
 */
export function calcularAlteracao(
  atual: DadosDoPerfil,
  formulario: DadosDoPerfil,
): AlteracaoDePerfil {
  const alteracao: AlteracaoDePerfil = {};
  const nome = normalizarNome(formulario.nome);
  const email = normalizarEmail(formulario.email);
  if (nome !== normalizarNome(atual.nome)) alteracao.nome = nome;
  if (email !== normalizarEmail(atual.email)) alteracao.email = email;
  return alteracao;
}

export function nadaAFazer(alteracao: AlteracaoDePerfil): boolean {
  return alteracao.nome === undefined && alteracao.email === undefined;
}

/**
 * O e-mail já vale, pela resposta do servidor?
 *
 * **Pessimista por omissão, de propósito.** Só devolve `true` quando o usuário
 * devolvido pela chamada traz, ele mesmo, o endereço novo em `email`. Resposta
 * sem usuário, usuário sem `email`, ou `email` ainda no antigo — todos contam
 * como pendente. É a mesma regra do `interpretarRecibo` do `UI-10`, e pelo
 * mesmo motivo: na dúvida, o desfecho pior é o verdadeiro.
 *
 * O caso em que isto devolve `true` é o projeto Supabase com confirmação de
 * troca de e-mail desligada. Não assumimos qual é a configuração — lemos o que
 * voltou.
 */
export function emailJaVale(usuario: User | null | undefined, emailNovo: string): boolean {
  const atual = typeof usuario?.email === "string" ? normalizarEmail(usuario.email) : "";
  return atual !== "" && atual === normalizarEmail(emailNovo);
}

/**
 * Aplica a correção.
 *
 * Ordem: nome primeiro, e-mail depois. O nome é a operação que não tem
 * desfecho parcial — fazê-la antes garante que, se o e-mail falhar, o que já
 * valeu é o que o resultado informa, e não o contrário.
 */
export async function atualizarPerfil(
  atual: DadosDoPerfil,
  formulario: DadosDoPerfil,
): Promise<ResultadoDePerfil> {
  const alteracao = calcularAlteracao(atual, formulario);
  if (nadaAFazer(alteracao)) return { tipo: "nada-a-fazer" };

  if (alteracao.nome !== undefined) {
    const valido = validarNome(alteracao.nome);
    if (!valido.ok) return { tipo: "invalido", mensagem: valido.motivo };
  }
  if (alteracao.email !== undefined) {
    const valido = validarEmail(alteracao.email);
    if (!valido.ok) return { tipo: "invalido", mensagem: valido.motivo };
  }

  const supabase = obterSupabase();
  if (!supabase) return { tipo: "invalido", mensagem: SEM_CONFIGURACAO };

  let nomeAlterado = false;

  if (alteracao.nome !== undefined) {
    const { error } = await supabase.auth.updateUser({ data: { nome: alteracao.nome } });
    if (error) {
      return { tipo: "erro", mensagem: traduzirErroDeAuth(error), nomeAlterado: false };
    }
    nomeAlterado = true;
  }

  if (alteracao.email === undefined) return { tipo: "salvo", nomeAlterado };

  const { data, error } = await supabase.auth.updateUser({ email: alteracao.email });
  if (error) {
    // O nome pode já ter sido gravado. O resultado diz isso em vez de deixar a
    // tela anunciar que nada foi salvo.
    return { tipo: "erro", mensagem: traduzirErroDeAuth(error), nomeAlterado };
  }

  if (emailJaVale(data?.user, alteracao.email)) {
    return { tipo: "salvo", nomeAlterado };
  }
  return { tipo: "email-pendente", emailPendente: alteracao.email, nomeAlterado };
}

/**
 * A frase que a tela mostra para cada desfecho.
 *
 * Separada do componente para poder ser testada: a diferença entre "salvo" e
 * "e-mail pendente" é exatamente o que não pode ser dito errado, e um texto
 * dentro de JSX não tem teste neste projeto (ver `UI-17`).
 */
export function descreverResultado(resultado: ResultadoDePerfil, emailAtual: string): string {
  switch (resultado.tipo) {
    case "nada-a-fazer":
      return "Nada a salvar — os dados já estão assim.";
    case "salvo":
      return "Dados atualizados.";
    case "email-pendente": {
      const inicio = resultado.nomeAlterado ? "Nome atualizado. " : "";
      return (
        `${inicio}Enviamos um link de confirmação para ${resultado.emailPendente}. ` +
        `Seu e-mail de acesso continua sendo ${emailAtual} até a confirmação — e pode ` +
        `ser pedida confirmação também no endereço atual.`
      );
    }
    case "invalido":
      return resultado.mensagem;
    case "erro":
      return resultado.nomeAlterado
        ? `O nome foi atualizado, mas o e-mail não: ${resultado.mensagem}`
        : resultado.mensagem;
  }
}
