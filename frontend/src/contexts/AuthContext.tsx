import type { Session, User } from "@supabase/supabase-js";
import { createContext, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { definirCallbackDeSessaoExpirada, definirProvedorDeToken } from "../lib/api";
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

  // Liga a sessao ao cliente de API DURANTE A RENDERIZACAO, e nao num efeito
  // (AUTH-07). No React os efeitos dos filhos rodam ANTES dos do pai: com o
  // provedor registrado num `useEffect` daqui, o `PerfilProvider` -- filho, que
  // busca o perfil no instante em que a sessao aparece -- mandava a primeira
  // chamada sem `Authorization`, recebia 401, e o callback abaixo derrubava a
  // sessao recem-criada. Era o login que voltava para /login (31/10).
  //
  // A ref e atualizada a cada renderizacao, antes de qualquer efeito de filho,
  // e o provedor e registrado uma vez e le dela: toda chamada leva o token
  // atual, inclusive depois da renovacao de uma hora.
  const sessaoAtual = useRef<Session | null>(sessao);
  sessaoAtual.current = sessao;
  useState(() => {
    definirProvedorDeToken(() => sessaoAtual.current?.access_token ?? null);
    // 401 vindo da API significa sessao morta no servidor -- mesmo que o
    // cliente ainda ache que tem uma. Limpar aqui evita o estado em que a
    // tela parece logada e nada carrega. O guarda de rota faz o resto
    // (AUTH-04). Registrado aqui pelo mesmo motivo do provedor.
    //
    // E limpa tambem a sessao GUARDADA pelo Supabase no navegador (AUTH-08):
    // sem isso, recarregar a pagina ressuscitava a sessao que o servidor ja
    // recusou, e o 401 se repetia. `scope: "local"` nao chama o servidor --
    // a sessao ja e invalida la. So o 401 chega aqui: 503 (servico fora do
    // ar) nao desloga ninguem.
    definirCallbackDeSessaoExpirada(() => {
      void obterSupabase()?.auth.signOut({ scope: "local" });
      setSessao(null);
    });
  });

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
