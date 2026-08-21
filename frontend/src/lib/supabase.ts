/**
 * Cliente Supabase do navegador (AUTH-01).
 *
 * Usa a chave `anon` — publica por design. O isolamento entre usuarios vem do
 * RLS aplicado no banco (SEC-04), nunca de esconder a chave.
 *
 * O cliente e criado sob demanda: sem as variaveis de ambiente o app ainda
 * carrega e mostra um erro explicavel na tela de login, em vez de quebrar em
 * branco no import.
 */
import { createClient, type SupabaseClient } from "@supabase/supabase-js";

import { verificarChaveAnon } from "./chaveSupabase";

const URL_SUPABASE = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const CHAVE_ANON = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

let cliente: SupabaseClient | null = null;
let motivoDaFalha: string | null = null;

/** Descreve por que o cliente nao pode ser criado, ou null se estiver tudo certo. */
export function problemaDeConfiguracao(): string | null {
  if (!URL_SUPABASE || !URL_SUPABASE.trim()) {
    return "VITE_SUPABASE_URL nao definida. Copie frontend/.env.example para .env e preencha.";
  }
  const chave = verificarChaveAnon(CHAVE_ANON);
  if (!chave.valida) return chave.motivo;
  return null;
}

export function obterSupabase(): SupabaseClient | null {
  if (cliente) return cliente;
  if (motivoDaFalha) return null;

  const problema = problemaDeConfiguracao();
  if (problema) {
    motivoDaFalha = problema;
    // Erro, nao warning: configuracao ausente impede login por completo.
    console.error(`[Smart Dormio] ${problema}`);
    return null;
  }

  cliente = createClient(URL_SUPABASE!, CHAVE_ANON!, {
    auth: {
      // Mantem a sessao entre recarregamentos e renova o token sozinho.
      persistSession: true,
      autoRefreshToken: true,
      // O link de confirmacao de e-mail volta com os tokens na URL; o cliente
      // precisa consumi-los ao carregar a pagina (AUTH-04 trata a rota).
      detectSessionInUrl: true,
    },
  });
  return cliente;
}
