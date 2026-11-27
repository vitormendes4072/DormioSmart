import { useEffect, useState } from "react";

import { estaAtivo, listarDispositivos } from "../lib/dispositivos";

const INTERVALO = 5_000;
const PRAZO_DA_CONSULTA = 10_000;
type Resultado = "aguardando" | "sinal" | "erro" | "ausente";

export function usePrimeiroSinal(aparelho: string) {
  const [consulta, setConsulta] = useState(0);
  const [resultado, setResultado] = useState<Resultado>("aguardando");

  useEffect(() => {
    let controle: AbortController | undefined;
    let timer: number | undefined;
    let prazo: number | undefined;

    function parar() {
      controle?.abort();
      window.clearTimeout(timer);
      window.clearTimeout(prazo);
    }

    async function consultar() {
      if (document.hidden) return;
      const pedido = new AbortController();
      controle = pedido;
      const prazoDoPedido = window.setTimeout(() => {
        pedido.abort();
        setResultado("erro");
        timer = window.setTimeout(() => void consultar(), INTERVALO);
      }, PRAZO_DA_CONSULTA);
      prazo = prazoDoPedido;
      try {
        const lista = await listarDispositivos(pedido.signal);
        if (pedido.signal.aborted) return;
        const dispositivo = lista.find((d) => d.id === aparelho && estaAtivo(d));
        if (!dispositivo) {
          setResultado("ausente");
          return;
        }
        if (dispositivo.last_seen_at && Number.isFinite(Date.parse(dispositivo.last_seen_at))) {
          setResultado("sinal");
          return;
        }
        setResultado("aguardando");
      } catch {
        if (pedido.signal.aborted) return;
        setResultado("erro");
      } finally {
        window.clearTimeout(prazoDoPedido);
      }
      timer = window.setTimeout(() => void consultar(), INTERVALO);
    }

    function aoMudarVisibilidade() {
      parar();
      if (!document.hidden) void consultar();
    }

    document.addEventListener("visibilitychange", aoMudarVisibilidade);
    void consultar();
    return () => {
      document.removeEventListener("visibilitychange", aoMudarVisibilidade);
      parar();
    };
  }, [aparelho, consulta]);

  return {
    resultado,
    tentarNovamente: () => {
      setResultado("aguardando");
      setConsulta((anterior) => anterior + 1);
    },
  };
}
