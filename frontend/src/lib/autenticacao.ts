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
  // SEC-08 — a frase NAO nomeia o fato, e isso e decisao de seguranca.
  //
  // Ela dizia "Ja existe uma conta com este e-mail.", o que entrega ao
  // visitante, na propria tela e sem ferramenta nenhuma, quem tem cadastro:
  // e enumeracao de e-mails com um formulario. **Confirmado empiricamente em
  // 20/10** — cadastrando um e-mail existente, a tela mostrava a frase. Nao
  // foi inferido do codigo. A redacao de agora e condicional (mesmo modelo do
  // `recuperarSenha`, que responde identico com ou sem conta) e serve igual a
  // quem errou outra coisa no formulario.
  //
  // ⚠️ Isto fecha o canal OBVIO e nao fecha o ESTRUTURAL. Com confirmacao de
  // e-mail desligada os dois caminhos divergem por construcao: e-mail novo
  // recebe 200 + sessao e a tela vai para /dashboard; e-mail existente recebe
  // 422 `user_already_exists` e a tela fica onde esta. Quem olha o DESFECHO,
  // e nao a frase, continua distinguindo os dois — e nenhuma mudanca de
  // frontend fecha isso, porque o oraculo esta na resposta da API. Ver
  // `SEC-08` no backlog: a saida que torna os caminhos identicos e ligar a
  // confirmacao de e-mail, e essa decisao e do Vitor.
  if (eh("user_already_exists", "already registered")) {
    return (
      "Não foi possível criar a conta com estes dados. " +
      'Se você já tem cadastro, entre pelo login ou use "Esqueci minha senha".'
    );
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
  // O navegador nao distingue "sua rede caiu" de "o servico esta fora": as duas
  // coisas chegam aqui como `Failed to fetch` com status 0. Mandar o usuario
  // "verificar a internet" acusa o lado errado sempre que a causa e a segunda —
  // foi o que aconteceu quando o projeto Supabase ficou pausado e o DNS do host
  // deixou de resolver. A frase agora cobre os dois casos sem culpar nenhum.
  if (erro.status === 0 || texto.includes("fetch") || texto.includes("network")) {
    return "Não foi possível falar com o servidor. Se persistir, o serviço pode estar temporariamente fora.";
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
 *
 * ── E e aqui que mora o canal estrutural do `SEC-08` ──────────────────────
 *
 * O comportamento do Supabase diante de um e-mail JA cadastrado depende da
 * mesma chave, e os dois regimes sao opostos. Isto estava registrado no
 * cabecalho de `pareceContaExistente`, que era o unico lugar do repositorio a
 * guardar a informacao; a funcao foi apagada em 20/10 (era export morto, com
 * 3 testes afirmando uma decisao que nenhum caminho de producao exercitava —
 * `UI-19`), e a informacao fica aqui porque e insumo da decisao do `SEC-08`:
 *
 * - **Confirmacao LIGADA** (chamada de protecao contra enumeracao, e padrao
 *   do Supabase): cadastrar e-mail existente responde **SUCESSO**, com `user`
 *   preenchido mas `identities` **vazio**, e **sem sessao**. A tela e a mesma
 *   ("confira seu e-mail") e nao ha sessao em nenhum dos dois casos.
 *
 *   ⚠️ **E este paragrafo afirmava que os dois caminhos ficam
 *   "indistinguiveis pelo cliente". ERA FALSO, e o erro importa porque esta
 *   frase era o insumo da decisao do `SEC-08`.** `identities` **vazio**
 *   contra `identities` **populado** e justamente a diferenca, dentro de um
 *   200, em JSON, sem timing e sem ferramenta — e esta publicado como
 *   *metodo de deteccao* (`data.user.identities?.length === 0`). A propria
 *   documentacao oficial do `signUp` e hedged e deveria ter sido lida com
 *   atencao a qualificacao: *"you may get back an error message that
 *   **attempts to** hide this information from the user"*.
 *
 *   Consequencia pratica: ligar a confirmacao **nao fecha** a enumeracao no
 *   cadastro — troca o canal de status HTTP (422 vs 200) por um canal em
 *   campo do corpo. Muda o **custo de exploracao**, nao o fato.
 *
 *   ⚠️ **E abre dois canais que nao existem hoje:** (i) `email_not_confirmed`
 *   passa a existir no login, e a frase "Confirme seu e-mail antes de entrar"
 *   (tratada acima, em `traduzirErroDeAuth`) so aparece para **quem tem
 *   conta**; (ii) re-cadastro em endereco **nao confirmado** **nao
 *   sobrescreve a senha original**, o que e pre-sequestro de conta e nao
 *   enumeracao — e o `SEC-10` do backlog.
 *
 *   ⚠️ **Nada deste bloco foi medido contra o Supabase.** E fonte: doc
 *   oficial do `signUp` e relatos de comunidade. O que fecharia: projeto
 *   Supabase de teste com a confirmacao ligada, dois `signUp` por `curl`,
 *   comparar `identities`. E o mesmo instrumento que o `UI-11` ja deve.
 * - **Confirmacao DESLIGADA** (configuracao atual, e a decidida em 20/10 —
 *   saida (B′) do `SEC-08`): cadastrar e-mail existente responde **erro 422
 *   `user_already_exists`**, e e-mail novo responde 200 **com sessao**. A
 *   divergencia e por construcao, nao por redacao — ver o comentario do
 *   `user_already_exists` em `traduzirErroDeAuth`. **Confirmado
 *   empiricamente em 20/10**, e e o unico dos dois regimes que este projeto
 *   mediu.
 */
function temSessaoImediata(data: { session: unknown | null }): boolean {
  return data.session !== null && data.session !== undefined;
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
