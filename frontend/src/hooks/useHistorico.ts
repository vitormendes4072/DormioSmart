import { useCallback, useEffect, useRef, useState } from "react";

import { ErroApi, buscarHistorico, type FiltroDeHistorico } from "../lib/api";
import { estaEmModoDemo, gerarHistoricoDemo } from "../lib/demo";
import type { LeituraSono } from "../types/sleep";

type EstadoHistorico = {
  leituras: LeituraSono[];
  carregando: boolean;
  erro: string | ErroApi | null;
  recarregar: () => void;
};

/**
 * Carrega o historico de leituras.
 *
 * Expoe carregamento, vazio e erro. As chaves do filtro sao desmembradas nas
 * dependencias para que um objeto literal novo nao recarregue em loop.
 *
 * UI-24: so o pedido mais recente pode publicar estado. A identificacao
 * tambem cobre recargas manuais; apenas uma flag por efeito nao distinguiria
 * duas recargas do mesmo filtro. O cleanup invalida os pedidos pendentes.
 * Isto descarta resultados no hook; nao cancela a chamada nem altera os
 * efeitos de autenticacao do cliente de API.
 */
export function useHistorico(filtro: FiltroDeHistorico = {}): EstadoHistorico {
  const { dispositivo = null, desde = null, ate = null, limite = null } = filtro;
  const [leituras, setLeituras] = useState<LeituraSono[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | ErroApi | null>(null);
  const ativo = useRef(false);
  const geracao = useRef(0);

  const carregar = useCallback(async () => {
    if (!ativo.current) return;
    const pedido = ++geracao.current;
    const vigente = () => ativo.current && pedido === geracao.current;

    setCarregando(true);
    setErro(null);
    try {
      // A demonstracao continua local e guardada por build de desenvolvimento.
      const dados = import.meta.env.DEV && estaEmModoDemo()
        ? gerarHistoricoDemo(dispositivo)
        : await buscarHistorico({ dispositivo, desde, ate, limite });
      if (vigente()) setLeituras(dados);
    } catch (e) {
      if (vigente()) {
        // 401 ja disparou o callback do cliente; aqui so exibimos a falha.
        setErro(e instanceof ErroApi ? e : "Falha inesperada ao carregar.");
        setLeituras([]);
      }
    } finally {
      if (vigente()) setCarregando(false);
    }
  }, [dispositivo, desde, ate, limite]);

  useEffect(() => {
    // Reativar no setup e necessario no ciclo setup/cleanup/setup do Strict Mode.
    ativo.current = true;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- UI-33: Busca na API a cada troca de filtro; sem o carregamento síncrono, o filtro novo mostraria os dados antigos sem aviso.
    void carregar();
    return () => {
      ativo.current = false;
      // eslint-disable-next-line react-hooks/exhaustive-deps -- Invalida a geração do pedido mais recente, inclusive recargas manuais.
      geracao.current++;
    };
  }, [carregar]);

  return { leituras, carregando, erro, recarregar: () => void carregar() };
}
