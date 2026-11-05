import { useEffect, useState } from "react";

import { estaEmModoDemo } from "../lib/demo";
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
    // DEMO-03 (04/11): no modo demonstração não há conta nem dispositivo, e o
    // `useHistorico` já gera os dados no cliente. Sem este retorno a lista era
    // pedida à API mesmo assim, e o servidor de desenvolvimento sem backend
    // respondia 500 no console. Lista vazia é o painel sem seletor — o mesmo
    // que a falha silenciosa abaixo já produzia, sem o pedido.
    if (estaEmModoDemo()) return;
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
