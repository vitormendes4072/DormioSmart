/**
 * Verificacao da chave do Supabase exposta ao navegador (AUTH-01).
 *
 * ── O RISCO ─────────────────────────────────────────────────────────────
 *
 * No Vite, TODA variavel com prefixo `VITE_` e embutida no bundle e vai para
 * o navegador de qualquer visitante. A chave `anon` pode: ela existe para
 * isso, e o RLS e quem protege as linhas.
 *
 * A `service_role`, NAO. Ela ignora RLS por definicao — e o backend usa
 * exatamente essa propriedade para o caminho de ingestao. Se ela receber um
 * prefixo `VITE_` por engano, o banco inteiro fica legivel e gravavel por
 * qualquer pessoa que abrir o DevTools. Nao ha alerta do Vite, nem erro de
 * build: funciona, e vaza.
 *
 * O erro e plausivel: os dois valores ficam lado a lado no painel do Supabase,
 * tem aparencia parecida e um `.env` e copiado as pressas. Por isso a checagem
 * e de codigo, com teste — nao uma linha em checklist de revisao.
 *
 * ── COMO DISTINGUIR ─────────────────────────────────────────────────────
 *
 * Formato legado (JWT): tres partes separadas por ponto; o payload traz
 * `role: "anon"` ou `role: "service_role"`.
 *
 * Formato novo: prefixo `sb_publishable_` (publica) ou `sb_secret_` (secreta).
 */

export type ResultadoDaChave =
  | { valida: true }
  | { valida: false; motivo: string; perigosa: boolean };

function decodificarBase64Url(trecho: string): string | null {
  try {
    const base64 = trecho.replace(/-/g, "+").replace(/_/g, "/");
    const preenchido = base64.padEnd(Math.ceil(base64.length / 4) * 4, "=");
    return atob(preenchido);
  } catch {
    return null;
  }
}

export function verificarChaveAnon(chave: string | undefined): ResultadoDaChave {
  if (!chave || !chave.trim()) {
    return {
      valida: false,
      perigosa: false,
      motivo:
        "VITE_SUPABASE_ANON_KEY nao definida. Copie frontend/.env.example para .env e preencha.",
    };
  }

  const valor = chave.trim();

  // Formato novo
  if (valor.startsWith("sb_secret_")) {
    return {
      valida: false,
      perigosa: true,
      motivo:
        "A chave em VITE_SUPABASE_ANON_KEY e uma chave SECRETA (sb_secret_). " +
        "Ela nao pode ir para o navegador. Use a publicavel (sb_publishable_).",
    };
  }
  if (valor.startsWith("sb_publishable_")) {
    return { valida: true };
  }

  // Formato legado (JWT)
  const partes = valor.split(".");
  if (partes.length !== 3) {
    return {
      valida: false,
      perigosa: false,
      motivo: "VITE_SUPABASE_ANON_KEY nao parece uma chave do Supabase.",
    };
  }

  const payload = decodificarBase64Url(partes[1]);
  if (payload === null) {
    return {
      valida: false,
      perigosa: false,
      motivo: "Nao foi possivel ler a chave em VITE_SUPABASE_ANON_KEY.",
    };
  }

  let papel: unknown;
  try {
    papel = (JSON.parse(payload) as { role?: unknown }).role;
  } catch {
    return {
      valida: false,
      perigosa: false,
      motivo: "Nao foi possivel ler a chave em VITE_SUPABASE_ANON_KEY.",
    };
  }

  if (papel === "service_role") {
    return {
      valida: false,
      perigosa: true,
      motivo:
        "A chave em VITE_SUPABASE_ANON_KEY e a service_role. Ela ignora o RLS e " +
        "expor o banco inteiro no navegador. Troque pela chave anon e ROTACIONE a " +
        "service_role no Supabase — se ela chegou a ser publicada, esta comprometida.",
    };
  }

  if (papel !== "anon") {
    return {
      valida: false,
      perigosa: true,
      motivo: `Chave com papel inesperado (${String(papel)}). Esperado: anon.`,
    };
  }

  return { valida: true };
}
