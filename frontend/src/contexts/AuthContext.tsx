import type { Session, User } from "@supabase/supabase-js";
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { definirProvedorDeToken } from "../lib/api";
import { obterSupabase, problemaDeConfiguracao } from "../lib/supabase";

/**
 * Sessao do usuario (AUTH-01).
 *
 * Este item entrega apenas o ENCANAMENTO: sessao, carregamento e sair. As
 * telas de login e cadastro passam a consumir isto no AUTH-02, e a protecao
 * de rotas no AUTH-04.
 *
 * O ponto que mais importa aqui e a ligacao com `lib/api.ts`: o provedor de
 * token e registrado assim que a sessao muda, entao toda chamada a `/api/*`
 * passa a levar o JWT sem que nenhuma tela precise saber disso.
 */

type ContextoDeAutenticacao = {
  sessao: Session | null;
  usuario: User | null;
  carregando: boolean;
  /** Configuracao ausente ou invalida (ex.: .env nao preenchido). */
  erroDeConfiguracao: string | null;
  sair: () => Promise<void>;
};

const Contexto = createContext<ContextoDeAutenticacao | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [sessao, setSessao] = useState<Session | null>(null);
  const [carregando, setCarregando] = useState(true);
  const erroDeConfiguracao = problemaDeConfiguracao();

  useEffect(() => {
    const supabase = obterSupabase();
    if (!supabase) {
      // Sem configuracao nao ha sessao a carregar — nao deixar `carregando`
      // preso, senao a UI fica num spinner eterno sem explicar o motivo.
      setCarregando(false);
      return;
    }

    let ativo = true;

    // Sessao ja persistida (recarregou a pagina com login ativo).
    void supabase.auth.getSession().then(({ data }) => {
      if (!ativo) return;
      setSessao(data.session);
      setCarregando(false);
    });

    // Login, logout, renovacao de token e retorno do link de e-mail passam
    // todos por aqui.
    const { data: assinatura } = supabase.auth.onAuthStateChange((_evento, novaSessao) => {
      setSessao(novaSessao);
      setCarregando(false);
    });

    return () => {
      ativo = false;
      assinatura.subscription.unsubscribe();
    };
  }, []);

  // Liga a sessao ao cliente de API. Fica dentro de efeito para rodar tambem
  // quando o token e renovado — um provedor que capturasse o JWT uma unica vez
  // passaria a mandar token expirado depois de uma hora.
  useEffect(() => {
    definirProvedorDeToken(() => sessao?.access_token ?? null);
  }, [sessao]);

  const valor = useMemo<ContextoDeAutenticacao>(
    () => ({
      sessao,
      usuario: sessao?.user ?? null,
      carregando,
      erroDeConfiguracao,
      sair: async () => {
        await obterSupabase()?.auth.signOut();
        setSessao(null);
      },
    }),
    [sessao, carregando, erroDeConfiguracao],
  );

  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function useAuth(): ContextoDeAutenticacao {
  const contexto = useContext(Contexto);
  if (!contexto) {
    throw new Error("useAuth precisa estar dentro de <AuthProvider>.");
  }
  return contexto;
}
