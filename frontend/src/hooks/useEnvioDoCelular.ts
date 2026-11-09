import { useEffect, useState } from "react";

import { useAuth } from "../contexts/AuthContext";
import { enviarLote, prepararDispositivoDoCelular } from "../lib/coleta";
import type { EnviarLote } from "../lib/envioDaNoite";

/**
 * O envio das noites do app para a conta (APP-02, etapas 3 e 4).
 *
 * Prepara o dispositivo `celular` deste usuário (create-or-get no servidor,
 * como a coleta pelo navegador) e monta o `enviar` com a sessão atual.
 * Devolve `undefined` enquanto falta um dos dois: sem eles, as épocas
 * esperam no aparelho, que é o lugar seguro delas.
 */
export function useEnvioDoCelular(ativo: boolean): EnviarLote | undefined {
  const jwt = useAuth().sessao?.access_token ?? null;
  const [dispositivo, setDispositivo] = useState<string | null>(null);

  useEffect(() => {
    if (!ativo || !jwt || dispositivo) return;
    let vivo = true;
    prepararDispositivoDoCelular()
      .then((d) => vivo && setDispositivo(d.id))
      .catch(() => {
        // Sem dispositivo, sem envio: a tela continua, e as épocas esperam.
      });
    return () => {
      vivo = false;
    };
  }, [ativo, jwt, dispositivo]);

  if (!ativo || !jwt || !dispositivo) return undefined;
  return (leituras) => enviarLote(leituras, dispositivo, jwt);
}
