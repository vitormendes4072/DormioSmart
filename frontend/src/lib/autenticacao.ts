/**
 * Operacoes de autenticacao e traducao de erros (AUTH-02).
 *
 * O supabase-js devolve mensagens em ingles e voltadas ao desenvolvedor
 * ("Invalid login credentials"). Este modulo converte para portugues e para a
 * linguagem do usuario, dizendo o que fazer a seguir — e nao apenas o que
 * deu errado.
 */
import type { AuthError } from "@supabase/supabase-js";

import { obterSupabase } from "./supabase";

/** Minimo do app. O Supabase aceita 6 por padrao; aqui e mais rigido, e a
 *  tela de cadastro promete isso ao usuario. */
export const MINIMO_DA_SENHA = 8;

export type ResultadoDeAuth =
  | { ok: true; precisaConfirmarEmail?: boolean }
  | { ok: false; mensagem: string; naoConfirmado?: boolean };

/**
 * Traduz o erro do Supabase.
 *
 * Prefere `code`, que e estavel, e so cai para o texto da mensagem quando o
 * codigo nao vem — mensagens mudam entre versoes e nao deveriam ser contrato.
 */
export function traduzirErroDeAuth(erro: AuthError | null | undefined): string {
  if (!erro) return "Não foi possível concluir. Tente novamente.";

  const codigo = (erro as { code?: string }).code ?? "";
  const texto = (erro.message ?? "").toLowerCase();

  const eh = (c: string, t: string) => codigo === c || texto.includes(t);

  if (eh("invalid_credentials", "invalid login credentials")) {
    return "E-mail ou senha incorretos.";
  }
  if (eh("email_not_confirmed", "email not confirmed")) {
    return "Confirme seu e-mail antes de entrar. Verifique a caixa de entrada e o spam.";
  }
  if (eh("user_already_exists", "already registered")) {
    return "Já existe uma conta com este e-mail.";
  }
  if (eh("weak_password", "password should be at least")) {
    return `A senha precisa ter pelo menos ${MINIMO_DA_SENHA} caracteres.`;
  }
  if (eh("validation_failed", "unable to validate email")) {
    return "E-mail inválido.";
  }
  if (eh("over_email_send_rate_limit", "you can only request this after")) {
    return "Muitas tentativas em pouco tempo. Aguarde alguns instantes.";
  }
  if (eh("over_request_rate_limit", "rate limit")) {
    return "Muitas tentativas em pouco tempo. Aguarde alguns instantes.";
  }
  if (erro.status === 0 || texto.includes("fetch") || texto.includes("network")) {
    return "Sem conexão com o servidor. Verifique sua internet.";
  }

  // Sem correspondencia: nao repassar o texto cru em ingles, que nao ajuda
  // quem esta na tela e ainda expoe detalhe interno.
  return "Não foi possível concluir. Tente novamente em instantes.";
}

const SEM_CONFIGURACAO =
  "Autenticação não configurada. Confira o arquivo frontend/.env.";

export async function entrar(email: string, senha: string): Promise<ResultadoDeAuth> {
  const supabase = obterSupabase();
  if (!supabase) return { ok: false, mensagem: SEM_CONFIGURACAO };

  const { error } = await supabase.auth.signInWithPassword({
    email: email.trim(),
    password: senha,
  });

  if (error) {
    const codigo = (error as { code?: string }).code ?? "";
    const naoConfirmado =
      codigo === "email_not_confirmed" ||
      (error.message ?? "").toLowerCase().includes("email not confirmed");
    return { ok: false, mensagem: traduzirErroDeAuth(error), naoConfirmado };
  }

  return { ok: true };
}

export async function cadastrar(
  nome: string,
  email: string,
  senha: string,
): Promise<ResultadoDeAuth> {
  const supabase = obterSupabase();
  if (!supabase) return { ok: false, mensagem: SEM_CONFIGURACAO };

  if (senha.length < MINIMO_DA_SENHA) {
    return {
      ok: false,
      mensagem: `A senha precisa ter pelo menos ${MINIMO_DA_SENHA} caracteres.`,
    };
  }

  const { data, error } = await supabase.auth.signUp({
    email: email.trim(),
    password: senha,
    // `nome` vai para raw_user_meta_data; o trigger do SEC-04 o copia para
    // a tabela profiles na criacao do usuario.
    options: { data: { nome: nome.trim() } },
  });

  if (error) return { ok: false, mensagem: traduzirErroDeAuth(error) };

  return { ok: true, precisaConfirmarEmail: !temSessaoImediata(data) };
}

/**
 * Houve login imediato?
 *
 * Com confirmacao de e-mail ligada, `signUp` nao devolve sessao — o usuario
 * precisa clicar no link primeiro. Sem confirmacao, a sessao vem junto.
 */
function temSessaoImediata(data: { session: unknown | null }): boolean {
  return data.session !== null && data.session !== undefined;
}

/**
 * O e-mail informado ja pertence a uma conta?
 *
 * Com protecao contra enumeracao ligada (padrao do Supabase quando ha
 * confirmacao de e-mail), o cadastro de um e-mail existente responde SUCESSO,
 * mas com `identities` vazio. Nao dizemos ao usuario que a conta existe —
 * isso permitiria descobrir quem tem cadastro. A tela mostra a mesma mensagem
 * de "confira seu e-mail" nos dois casos, e quem ja tem conta recebe um
 * e-mail avisando disso.
 */
export function pareceContaExistente(data: {
  user: { identities?: unknown[] | null } | null;
}): boolean {
  const identidades = data.user?.identities;
  return Array.isArray(identidades) && identidades.length === 0;
}

export async function reenviarConfirmacao(email: string): Promise<ResultadoDeAuth> {
  const supabase = obterSupabase();
  if (!supabase) return { ok: false, mensagem: SEM_CONFIGURACAO };

  const { error } = await supabase.auth.resend({ type: "signup", email: email.trim() });
  if (error) return { ok: false, mensagem: traduzirErroDeAuth(error) };
  return { ok: true };
}

export async function recuperarSenha(email: string): Promise<ResultadoDeAuth> {
  const supabase = obterSupabase();
  if (!supabase) return { ok: false, mensagem: SEM_CONFIGURACAO };

  const { error } = await supabase.auth.resetPasswordForEmail(email.trim(), {
    redirectTo: `${window.location.origin}/nova-senha`,
  });
  if (error) return { ok: false, mensagem: traduzirErroDeAuth(error) };
  return { ok: true };
}
