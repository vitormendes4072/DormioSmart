import { useCallback, useEffect, useState } from "react";

import {
  aplicarTema,
  lerPreferencia,
  resolverTema,
  salvarPreferencia,
  type PreferenciaDeTema,
  type TemaAplicado,
} from "../lib/tema";

const CONSULTA_ESCURO = "(prefers-color-scheme: dark)";

export function useTema() {
  const [preferencia, setPreferenciaEstado] = useState<PreferenciaDeTema>(() =>
    lerPreferencia(window.localStorage),
  );
  const [aplicado, setAplicado] = useState<TemaAplicado>(
    () => (document.documentElement.dataset.theme as TemaAplicado) ?? "light",
  );

  useEffect(() => {
    const consulta = window.matchMedia(CONSULTA_ESCURO);

    const sincronizar = () => {
      const tema = resolverTema(preferencia, consulta.matches);
      aplicarTema(tema, document.documentElement);
      setAplicado(tema);
    };

    sincronizar();

    // Com "sistema", o app precisa acompanhar a troca no SO em tempo real —
    // sem isso, mudar o tema do sistema so faria efeito no proximo reload.
    if (preferencia !== "sistema") return;
    consulta.addEventListener("change", sincronizar);
    return () => consulta.removeEventListener("change", sincronizar);
  }, [preferencia]);

  const definirPreferencia = useCallback((nova: PreferenciaDeTema) => {
    salvarPreferencia(window.localStorage, nova);
    setPreferenciaEstado(nova);
  }, []);

  return { preferencia, aplicado, definirPreferencia };
}
