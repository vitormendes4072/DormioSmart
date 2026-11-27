import { useEffect, useState } from "react";

import { buscarJanelaDoHistorico, LIMITE_DO_PAINEL } from "../lib/api";
import { calcularCobertura } from "../lib/cobertura";
import { anotarAviso, estadoDoAviso } from "../lib/primeirosPassos";
import { sessoesDaMarca } from "../lib/trecho";
import type { LeituraSono } from "../types/sleep";

export function useAvisoDaPrimeiraSessao(
  conta: string | undefined,
  presenca: "com-registro" | "sem-registro" | "inconclusivo",
  recentes: LeituraSono[],
) {
  const [aviso, setAviso] = useState<{ conta: string; tempo: string }>();

  useEffect(() => {
    if (!conta) return;
    const estado = estadoDoAviso(conta);
    if (presenca === "sem-registro" && estado === null) anotarAviso(conta, "aguardando");
    if (presenca !== "com-registro" || estado !== "aguardando") return;
    const controle = new AbortController();

    async function anunciar(id: string) {
      const historico = recentes.length < LIMITE_DO_PAINEL
        ? { leituras: recentes, truncada: false }
        : await buscarJanelaDoHistorico({}, controle.signal, () => {});
      if (controle.signal.aborted || historico.truncada || estadoDoAviso(id) !== "aguardando") return;
      const primeira = sessoesDaMarca(historico.leituras, false)[0];
      if (!primeira) return;
      const ms = calcularCobertura(primeira.leituras).tempoCobertoMs;
      if (ms <= 0) return;
      const segundos = Math.floor(ms / 1000);
      const horas = Math.floor(segundos / 3600);
      const minutos = Math.floor((segundos % 3600) / 60);
      const tempo = horas > 0 ? `${horas} h ${String(minutos).padStart(2, "0")} ${horas === 1 ? "registrada" : "registradas"}`
        : minutos > 0 ? `${minutos} min ${minutos === 1 ? "registrado" : "registrados"}`
        : `${segundos} s ${segundos === 1 ? "registrado" : "registrados"}`;
      if (anotarAviso(id, "mostrado")) setAviso({ conta: id, tempo });
    }
    void Promise.resolve().then(() => anunciar(conta)).catch(() => {});
    return () => controle.abort();
  }, [conta, presenca, recentes]);

  return aviso?.conta === conta ? aviso?.tempo : undefined;
}
