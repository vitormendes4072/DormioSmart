import { useEffect, useState } from "react";

import { estaEmModoDemo, listarAparelhosDemo } from "../lib/demo";
import { listarDispositivos, type Dispositivo } from "../lib/dispositivos";

/**
 * Lista de dispositivos do usuario, para o seletor do painel (DASH-05).
 *
 * Se a listagem cair, o painel continua mostrando o gráfico sem seletor.
 * O guia usa o estado da consulta para não tomar a falha por lista vazia.
 */
export function useDispositivos() {
  const demo = import.meta.env.DEV && estaEmModoDemo();
  const [resultado, setResultado] = useState<{ dispositivos: Dispositivo[]; estado: "carregando" | "erro" | "pronto" }>(() =>
    demo ? { dispositivos: listarAparelhosDemo(), estado: "pronto" } : { dispositivos: [], estado: "carregando" });

  useEffect(() => {
    // A demonstração tem sua própria lista local, sem consulta à API.
    if (demo) return;
    let vivo = true;
    listarDispositivos()
      .then((lista) => {
        if (vivo) setResultado({ dispositivos: lista, estado: "pronto" });
      })
      .catch(() => {
        if (vivo) setResultado({ dispositivos: [], estado: "erro" });
      });
    return () => {
      vivo = false;
    };
  }, [demo]);

  return resultado;
}
