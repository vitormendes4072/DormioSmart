import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

import { useAuth } from "./AuthContext";
import { buscarPerfil, type PerfilDoServidor } from "../lib/perfil";

/**
 * O leitor do perfil (PERFIL-01).
 *
 * ── POR QUE É CONTEXTO, E NÃO UM HOOK QUE CADA TELA CHAMA ────────────────
 *
 * A **Regra 1** da decisão é *leitor único*: o nome exibido vem de
 * `public.profiles`, e de mais nenhum lugar. Duas telas leem nome hoje — a
 * saudação da `Sidebar` e a seção *Conta* das Configurações — e antes do
 * `PERFIL-01` as duas liam `user_metadata.nome` cada uma por si.
 *
 * Com um hook por tela, "leitor único" valeria para a *fonte* e não para o
 * *valor*: duas buscas independentes, dois estados, e a saudação continuaria
 * mostrando o nome velho depois de uma correção até alguém recarregar a
 * página. O defeito seria pequeno e exatamente do tipo que ninguém nota — a
 * tela "quase certa".
 *
 * Então há um estado só, e `recarregar()` é o que a tela de edição chama
 * depois de salvar.
 *
 * ── O QUE ESTE CONTEXTO FAZ COM FALHA ────────────────────────────────────
 *
 * Distingue "ainda não sei" de "não há nome". `perfil` nulo com
 * `carregando: false` e `erro` preenchido é o terceiro estado, e existe porque
 * mostrar nome em branco quando a leitura falhou é degradação silenciosa (§7):
 * quem tem nome veria a tela de quem não tem. A `Sidebar` mostra o e-mail
 * nesse caso, que é informação verdadeira e sempre disponível.
 */

type ContextoDePerfil = {
  perfil: PerfilDoServidor | null;
  carregando: boolean;
  erro: string | null;
  recarregar: () => Promise<void>;
};

const Contexto = createContext<ContextoDePerfil | null>(null);

export function PerfilProvider({ children }: { children: ReactNode }) {
  const { sessao, carregando: carregandoSessao } = useAuth();
  const [perfil, setPerfil] = useState<PerfilDoServidor | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      setPerfil(await buscarPerfil());
    } catch (falha) {
      // Não cai para o metadado do Auth: seria o segundo leitor de volta, sob
      // condição — e invariante com cláusula de exceção é o que apodrece
      // primeiro. Ver `docs/DECISAO-FONTE-DO-PERFIL.md`, seção 3.
      setPerfil(null);
      setErro(falha instanceof Error ? falha.message : "Não foi possível carregar o perfil.");
    } finally {
      setCarregando(false);
    }
  }, []);

  // Dispara quando a sessão existe, e **de novo quando o usuário muda**: sem a
  // dependência no id, entrar com outra conta na mesma aba mostraria o nome da
  // anterior.
  const usuarioId = sessao?.user?.id ?? null;
  useEffect(() => {
    if (carregandoSessao) return;
    if (!usuarioId) {
      setPerfil(null);
      setErro(null);
      return;
    }
    void carregar();
  }, [usuarioId, carregandoSessao, carregar]);

  return (
    <Contexto.Provider value={{ perfil, carregando, erro, recarregar: carregar }}>
      {children}
    </Contexto.Provider>
  );
}

/**
 * ⚠️ **Levanta, e não devolve um valor neutro — e isso é a mitigação de um
 * ponto cego real.**
 *
 * ✏️ **19/10: a ausência de verificação descrita abaixo foi fechada** — o
 * `montagem.test.ts` tem a asserção `o <PerfilProvider> está montado na árvore
 * de produção`, por duas provas independentes (o pedido a `/api/me/perfil`
 * acontece, e o nome que ele carregou chega à tela). Medida por controle
 * positivo: removido o provedor do `main.tsx`, caem **8 de 8** testes de
 * montagem — e o `alcance.test.ts` continua passando, que era o ponto. O
 * `throw` abaixo **continua sendo a escolha certa**, por um motivo que não era
 * o original: ele é a defesa em tempo de execução, e o teste é a defesa em
 * tempo de commit; nenhum dos dois substitui o outro, e o `jsdom` não é
 * navegador.
 *
 * O que o parágrafo abaixo descrevia, mantido para o histórico ficar legível:
 *
 * Nada neste repositório verifica que `<PerfilProvider>` está **montado** em
 * `main.tsx`. O `alcance.test.ts` prova que este módulo está no grafo de
 * imports, e ele continua no grafo mesmo se o provider sair do JSX — medido
 * por controle positivo em 17/10: removido o `<PerfilProvider>` do `main.tsx`,
 * o `alcance.test.ts` **passa**. É exatamente a metade que falta do `UI-17`, e
 * a mesma classe de defeito que deixou o `UI-10` inalcançável por dezoito
 * dias.
 *
 * Com o `throw`, a ausência do provider quebra a primeira renderização de
 * forma ruidosa. Se este hook devolvesse `{ perfil: null }`, o aplicativo
 * subiria mostrando **nome em branco para quem tem nome** — dado
 * errado-com-cara-de-certo, que é o §7 das lições e o desfecho pior dos dois.
 */
export function usePerfil(): ContextoDePerfil {
  const contexto = useContext(Contexto);
  if (!contexto) {
    throw new Error("usePerfil precisa estar dentro de <PerfilProvider>.");
  }
  return contexto;
}
