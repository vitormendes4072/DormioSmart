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

/** Para onde vai quem acabou de entrar, quando não há destino válido. */
export const DESTINO_PADRAO_APOS_LOGIN = "/dashboard";

/**
 * O destino pós-login, só se for um caminho INTERNO (SEC-16, 03/11).
 *
 * O `Login` navega para a página que a pessoa tentava abrir antes de ser
 * mandada ao login. Hoje esse valor só é escrito pelo guarda de rotas, a partir
 * das rotas protegidas (fixas) — então não é explorável. Mas ele não era
 * validado, e é o padrão exato que o aviso GHSA-wrjc-x8rr-h8h6 do
 * `react-router` explora: `navigate("/\\evil.com")` sai do site. A biblioteca
 * foi corrigida (7.18.4); esta função é a defesa do lado de cá, para não
 * depender só dela.
 *
 * Aceita: começa com uma barra, e o segundo caractere não é barra nem barra
 * invertida. Recusa `//host`, `/\\host`, `https://…`, `javascript:…`, vazio
 * e o que não for texto — e devolve o destino padrão.
 */
export function destinoSeguro(candidato: unknown): string {
  if (typeof candidato !== "string") return DESTINO_PADRAO_APOS_LOGIN;
  if (!candidato.startsWith("/")) return DESTINO_PADRAO_APOS_LOGIN;
  const segundo = candidato.charAt(1);
  if (segundo === "/" || segundo === "\\") return DESTINO_PADRAO_APOS_LOGIN;
  // Caractere de controle no meio (tab, quebra de linha) pode ser descartado
  // pelo navegador ao resolver a URL e transformar "/\t/host" em "//host".
  if (/[\u0000-\u001f\u007f]/.test(candidato)) return DESTINO_PADRAO_APOS_LOGIN;
  return candidato;
}
