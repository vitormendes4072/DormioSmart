import { useCallback, useEffect, useState } from "react";

import { ErroApi, buscarHistorico, type FiltroDeHistorico } from "../lib/api";
import { estaEmModoDemo, gerarNoiteDemo } from "../lib/demo";
import type { LeituraSono } from "../types/sleep";

export type EstadoHistorico = {
  leituras: LeituraSono[];
  carregando: boolean;
  erro: string | null;
  recarregar: () => void;
};

/**
 * Carrega o historico de leituras.
 *
 * Expoe os tres estados que o mock do prototipo nao tinha — carregando, vazio
 * (leituras.length === 0) e erro — porque com dado real os tres acontecem: o
 * dispositivo pode nunca ter enviado nada, e a rede pode cair.
 *
 * `filtro` recorta por dispositivo e janela (DASH-05/DASH-06). As chaves sao
 * desmembradas na dependencia do `useCallback` de proposito: um objeto literal
 * vindo do componente muda de identidade a cada render e recarregaria em loop.
 */
export function useHistorico(filtro: FiltroDeHistorico = {}): EstadoHistorico {
  const { dispositivo = null, desde = null, ate = null, limite = null } = filtro;
  const [leituras, setLeituras] = useState<LeituraSono[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      // Modo demo (DEMO-01): dados gerados no cliente, sem tocar na API.
      // Guardado por build de desenvolvimento — ver lib/demo.ts.
      if (estaEmModoDemo()) {
        setLeituras(gerarNoiteDemo());
        return;
      }
      setLeituras(await buscarHistorico({ dispositivo, desde, ate, limite }));
    } catch (e) {
      // 401 ja disparou o callback de sessao expirada dentro do cliente; aqui
      // so registramos a mensagem para a tela exibir.
      setErro(e instanceof ErroApi ? e.message : "Falha inesperada ao carregar.");
      setLeituras([]);
    } finally {
      setCarregando(false);
    }
  }, [dispositivo, desde, ate, limite]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  return { leituras, carregando, erro, recarregar: () => void carregar() };
}
