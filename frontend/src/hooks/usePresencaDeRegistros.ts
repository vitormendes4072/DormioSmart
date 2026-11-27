import { useEffect, useState } from "react";

import { LIMITE_DO_PAINEL, verificarRegistrosDaConta } from "../lib/api";
import { ehBancada } from "../lib/trecho";
import type { LeituraSono } from "../types/sleep";

type Presenca = Awaited<ReturnType<typeof verificarRegistrosDaConta>>;

// undefined aguarda os dados do Início. null pede a primeira página no Histórico.
export function usePresencaDeRegistros(primeiraPagina: LeituraSono[] | null | undefined): Presenca {
  const [resposta, setResposta] = useState<{ primeiraPagina: LeituraSono[] | null; presenca: Presenca }>();
  const jaTemRegistro = primeiraPagina?.some((registro) => !ehBancada(registro)) ?? false;
  const terminou = primeiraPagina != null && primeiraPagina.length < LIMITE_DO_PAINEL;

  useEffect(() => {
    if (primeiraPagina === undefined || jaTemRegistro || terminou) return;
    const controle = new AbortController();
    const guardar = (presenca: Presenca) => {
      if (!controle.signal.aborted) setResposta({ primeiraPagina, presenca });
    };
    void verificarRegistrosDaConta(primeiraPagina, controle.signal).then(guardar, () => guardar("inconclusivo"));
    return () => controle.abort();
  }, [primeiraPagina, jaTemRegistro, terminou]);

  if (jaTemRegistro) return "com-registro";
  if (terminou) return "sem-registro";
  return resposta && resposta.primeiraPagina === primeiraPagina ? resposta.presenca : "inconclusivo";
}
