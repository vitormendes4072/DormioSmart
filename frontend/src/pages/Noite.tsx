import { useState } from "react";

import { CartaoDaNoite } from "../components/CartaoDaNoite";
import { ListaDeNoites } from "../components/ListaDeNoites";
import { useEnvioDoCelular } from "../hooks/useEnvioDoCelular";
import { usePerfil } from "../contexts/PerfilContext";
import { consentimentoVigente, registrarConsentimento } from "../lib/consentimento";
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
export function Noite() {
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
  const [versao, setVersao] = useState(0);

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs text-muted-foreground uppercase tracking-wider">Registro da noite</p>
        <h1 className="text-xl sm:text-2xl font-semibold text-foreground mt-1">A noite inteira</h1>
      </div>

      {nativo ? (
        <>
          <CartaoDaNoite
            enviar={enviar}
            aoMudar={() => setVersao((v) => v + 1)}
            consentimento={consentimento}
          />
          <div className="space-y-3">
            <h2 className="text-base font-semibold text-foreground">Noites neste aparelho</h2>
            <ListaDeNoites recarregar={versao} />
          </div>
        </>
      ) : (
        <p className="text-sm text-muted-foreground">
          O registro da noite inteira só funciona no app Android do Dormio: o navegador desliga o
          sensor quando a tela bloqueia.
        </p>
      )}
    </div>
  );
}
