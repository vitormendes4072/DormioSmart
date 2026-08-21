/**
 * Decisao de acesso a uma rota (AUTH-04).
 *
 * Extraida como funcao pura porque o caso dificil nao e "tem sessao ou nao" —
 * e o instante em que AINDA NAO SE SABE. Ao recarregar a pagina, o Supabase
 * leva alguns milissegundos para restaurar a sessao do armazenamento local.
 * Um guarda ingenuo le "sem sessao" nesse intervalo e chuta o usuario logado
 * para o login: o sintoma classico de "recarreguei e fui deslogado".
 *
 * Por isso "aguardar" e um estado de primeira classe aqui, e nao um detalhe.
 */

export type Destino =
  | "aguardar"
  | "liberar"
  | "ir-para-login"
  | "ir-para-dashboard";

export type Situacao = {
  /** A sessao ainda esta sendo restaurada. */
  carregando: boolean;
  temSessao: boolean;
  /** Rota de visitante (login, cadastro): quem ja entrou nao deve ficar nela. */
  ehRotaDeVisitante: boolean;
};

export function decidirDestino({
  carregando,
  temSessao,
  ehRotaDeVisitante,
}: Situacao): Destino {
  // Enquanto nao se sabe, nao se decide.
  if (carregando) return "aguardar";

  if (ehRotaDeVisitante) {
    return temSessao ? "ir-para-dashboard" : "liberar";
  }
  return temSessao ? "liberar" : "ir-para-login";
}

/**
 * O link de recuperacao de senha traz os tokens na URL.
 *
 * O supabase-js consome esses parametros ao carregar (`detectSessionInUrl`) e
 * cria uma sessao temporaria. Precisamos reconhecer esse retorno para mostrar
 * o formulario de nova senha em vez de mandar direto ao dashboard.
 *
 * O formato mudou entre versoes do Supabase: antes vinha no fragmento
 * (`#type=recovery`), hoje pode vir na query (`?type=recovery`) ou como
 * `?code=` do fluxo PKCE. Aceitamos as tres formas.
 */
export function ehRetornoDeRecuperacao(url: {
  hash?: string;
  search?: string;
}): boolean {
  const fragmento = (url.hash ?? "").replace(/^#/, "");
  const consulta = (url.search ?? "").replace(/^\?/, "");

  const tipo =
    new URLSearchParams(fragmento).get("type") ??
    new URLSearchParams(consulta).get("type");

  if (tipo === "recovery") return true;

  // Fluxo PKCE: so vem `code`, sem `type`. Na rota de nova senha, a presenca
  // do code ja significa retorno de e-mail.
  return new URLSearchParams(consulta).has("code");
}
