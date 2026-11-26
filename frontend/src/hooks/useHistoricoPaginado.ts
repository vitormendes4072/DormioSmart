import { useEffect, useState } from "react";

import { buscarJanelaDoHistorico, ErroApi } from "../lib/api";
import { gerarHistoricoDemo } from "../lib/demo";

type Janela = { desde: string; ate: string };
type Resultado = Awaited<ReturnType<typeof buscarJanelaDoHistorico>>;
type Resposta = { chave: string; dados: Resultado | null; erro: string | ErroApi | null };

export function useHistoricoPaginado(janela: Janela | null, dispositivo: string | null, demo: boolean) {
  const { desde, ate } = janela ?? {};
  const [tentativa, setTentativa] = useState(0);
  const [resposta, setResposta] = useState<Resposta>();
  const chave = JSON.stringify([dispositivo, desde, ate, demo, tentativa]);

  useEffect(() => {
    if (desde === undefined || ate === undefined) return;
    const controle = new AbortController();
    const pedido = import.meta.env.DEV && demo
      ? Promise.resolve({ leituras: gerarHistoricoDemo(dispositivo), truncada: false })
      : buscarJanelaDoHistorico({ dispositivo, desde, ate }, controle.signal, () => {});
    void pedido.then(
      (dados) => {
        if (!controle.signal.aborted) setResposta({ chave, dados, erro: null });
      },
      (falha: unknown) => {
        if (!controle.signal.aborted) {
          setResposta({ chave, dados: null, erro: falha instanceof ErroApi ? falha : "Falha ao carregar registros." });
        }
      },
    );
    return () => controle.abort();
  }, [ate, chave, demo, desde, dispositivo]);

  const atual = resposta?.chave === chave ? resposta : undefined;
  return {
    dados: atual?.dados,
    erro: atual?.erro ?? null,
    carregando: janela !== null && atual === undefined,
    recarregar: () => setTentativa((valor) => valor + 1),
  };
}
