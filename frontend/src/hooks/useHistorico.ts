import { useCallback, useEffect, useState } from "react";

import { ErroApi, buscarHistorico } from "../lib/api";
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
 */
export function useHistorico(): EstadoHistorico {
  const [leituras, setLeituras] = useState<LeituraSono[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      setLeituras(await buscarHistorico());
    } catch (e) {
      // 401 ja disparou o callback de sessao expirada dentro do cliente; aqui
      // so registramos a mensagem para a tela exibir.
      setErro(e instanceof ErroApi ? e.message : "Falha inesperada ao carregar.");
      setLeituras([]);
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  return { leituras, carregando, erro, recarregar: () => void carregar() };
}
