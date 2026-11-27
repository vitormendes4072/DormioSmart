import { useEffect } from "react";
import { useNavigate } from "react-router";

import { useAuth } from "../contexts/AuthContext";
import { verificarRegistrosDaConta } from "../lib/api";
import { noiteNativaDisponivel } from "../lib/noiteNativa";
import { anotarAviso, estadoDoAviso, guardarJornada, lerJornada } from "../lib/primeirosPassos";
import { DESTINO_PADRAO_APOS_LOGIN } from "../lib/rotas";

export function EntradaDaConta() {
  const { sessao } = useAuth();
  const conta = sessao?.user.id;
  const navegar = useNavigate();

  useEffect(() => {
    if (!conta) return;
    const destino = noiteNativaDisponivel() ? "/noite" : DESTINO_PADRAO_APOS_LOGIN;
    if (lerJornada(conta)) {
      navegar(destino, { replace: true });
      return;
    }
    const controle = new AbortController();
    const prazo = window.setTimeout(() => {
      controle.abort();
      navegar(destino, { replace: true });
    }, 12_000);
    async function entrar(id: string) {
      const presenca = await verificarRegistrosDaConta(null, controle.signal).catch(() => "inconclusivo");
      window.clearTimeout(prazo);
      if (controle.signal.aborted) return;
      if (presenca === "sem-registro") {
        if (estadoDoAviso(id) === null) anotarAviso(id, "aguardando");
        if (!lerJornada(id) && guardarJornada(id, { passo: "inicio" })) {
          navegar("/primeiros-passos", { replace: true });
          return;
        }
      }
      navegar(destino, { replace: true });
    }
    void entrar(conta);
    return () => {
      window.clearTimeout(prazo);
      controle.abort();
    };
  }, [conta, navegar]);

  return <p role="status" className="p-6 text-sm text-muted-foreground">Verificando seus registros…</p>;
}
