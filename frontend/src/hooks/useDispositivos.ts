import { useEffect, useState } from "react";

import { listarDispositivos, type Dispositivo } from "../lib/dispositivos";

/**
 * Lista de dispositivos do usuario, para o seletor do painel (DASH-05).
 *
 * Falha em silencio, de proposito: se a listagem cair, o painel continua
 * mostrando o grafico sem seletor — que e exatamente o comportamento de antes
 * do DASH-05. Derrubar a tela inteira porque a lista de dispositivos nao
 * carregou seria trocar um recurso acessorio pelo principal.
 */
export function useDispositivos(): Dispositivo[] {
  const [dispositivos, setDispositivos] = useState<Dispositivo[]>([]);

  useEffect(() => {
    let vivo = true;
    listarDispositivos()
      .then((lista) => {
        if (vivo) setDispositivos(lista);
      })
      .catch(() => {
        if (vivo) setDispositivos([]);
      });
    return () => {
      vivo = false;
    };
  }, []);

  return dispositivos;
}
