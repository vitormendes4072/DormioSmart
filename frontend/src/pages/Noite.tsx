import { lazy, Suspense, useState } from "react";
import { useLocation } from "react-router";

import { EtiquetaDeRegistro } from "../components/CartoesDeRegistro";
import { CartaoDaNoite } from "../components/CartaoDaNoite";
import { ListaDeNoites } from "../components/ListaDeNoites";
import { useEnvioDoCelular } from "../hooks/useEnvioDoCelular";
import { usePerfil } from "../contexts/PerfilContext";
import { consentimentoVigente, registrarConsentimento } from "../lib/consentimento";
import { estaEmModoDemo } from "../lib/demo";
import type { PluginNoite } from "../lib/noiteNativa";
import type { EnviarLote } from "../lib/envioDaNoite";
import { noiteNativaDisponivel } from "../lib/noiteNativa";

/**
 * A noite no app Android (APP-02, etapa 4).
 *
 * Antes: a posição do celular e o preparo. Durante: o registro, com os números
 * que dizem se ele está acontecendo de verdade. Depois: as noites gravadas,
 * o envio e o diário de sono do protocolo.
 *
 * Só existe no app — no site, o registro da noite não tem como acontecer
 * (o navegador para o sensor com a tela bloqueada), e a rota explica isso.
 */
const NoiteDemo = import.meta.env.DEV ? lazy(() => import("./NoiteDemo")) : null;

export function Noite() {
  const { search } = useLocation();
  if (NoiteDemo && estaEmModoDemo(search)) {
    return <Suspense fallback={null}><NoiteDemo /></Suspense>;
  }
  return <NoiteNativa />;
}

function NoiteNativa() {
  const nativo = noiteNativaDisponivel();
  const { perfil, recarregar } = usePerfil();
  // LGPD-12: sem o consentimento vigente, o servidor recusa o envio (403); o
  // envio só se prepara depois dele, e as épocas esperam no aparelho.
  const vigente = consentimentoVigente(perfil);
  const enviar = useEnvioDoCelular(nativo && vigente);
  const consentimento = {
    vigente,
    registrar: async () => {
      await registrarConsentimento();
      await recarregar();
    },
  };
  return <ConteudoDaNoite disponivel={nativo} enviar={enviar} consentimento={consentimento} />;
}

export function ConteudoDaNoite({ disponivel, plugin, enviar, consentimento }: {
  disponivel: boolean;
  plugin?: PluginNoite;
  enviar?: EnviarLote;
  consentimento?: { vigente: boolean; registrar: () => Promise<void> };
}) {
  const [versao, setVersao] = useState(0);

  return (
    <div className="space-y-6">
      <div>
        <EtiquetaDeRegistro>Registro da noite</EtiquetaDeRegistro>
        <h1 className="mt-1 text-2xl font-extrabold tracking-tight text-foreground sm:text-[27px]">A noite inteira</h1>
      </div>

      {disponivel ? (
        <>
          <CartaoDaNoite
            plugin={plugin}
            enviar={enviar}
            aoMudar={() => setVersao((v) => v + 1)}
            consentimento={consentimento}
          />
          <div className="space-y-3">
            <h2 className="text-base font-semibold text-foreground">Noites neste aparelho</h2>
            <ListaDeNoites plugin={plugin} recarregar={versao} />
          </div>
        </>
      ) : (
        <p className="text-sm text-muted-foreground">
          O registro da noite inteira só funciona no app Android do Smart Dormio: o navegador desliga o
          sensor quando a tela bloqueia.
        </p>
      )}
    </div>
  );
}
