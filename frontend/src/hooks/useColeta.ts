import { useCallback, useEffect, useRef, useState } from "react";

import {
  type Agregado,
  type Amostra,
  agregar,
  montarPayload,
} from "../lib/acelerometro";
import { useAuth } from "../contexts/AuthContext";
import { ErroDeIngestao, enviarLeitura } from "../lib/coleta";

/**
 * Plumbing do acelerometro do navegador (APP-01).
 *
 * Toda a matematica vive em `lib/acelerometro.ts`, testada como funcao pura.
 * Aqui fica so o que exige navegador: permissao, listener, temporizador,
 * wake lock.
 *
 * ── O QUE ESTE HOOK NAO CONSEGUE FAZER ──────────────────────────────────
 *
 * Monitorar a noite inteira. `devicemotion` para quando a tela bloqueia ou a
 * aba vai para o fundo. O Wake Lock segura a tela acesa, mas isso torra
 * bateria e esquenta o aparelho debaixo do edredom. Esta coleta serve para
 * sessoes de minutos — bancada, VIA-01, VIA-02. Noite inteira exige app
 * nativo com foreground service (APP-02), e no iOS provavelmente nem isso.
 *
 * A tela DIZ isso ao usuario. Um coletor que promete a noite e entrega 4
 * minutos e pior do que nenhum.
 *
 * ── POR QUE EXISTE UMA SONDA DE SINAL (APP-06) ──────────────────────────
 *
 * `"DeviceMotionEvent" in window` e TRUE em navegador de desktop, que nao tem
 * acelerometro nenhum. A API existe; os eventos e que nunca chegam. Sem a
 * sonda, comecar a coletar num computador iniciava, mostrava "0 amostras" e
 * nao produzia leitura nenhuma — para sempre, sem dizer por que.
 *
 * Falha silenciosa e o pior tipo. A sonda espera alguns segundos pela
 * primeira amostra e, se nada chegar, para e explica.
 *
 * O limiar e seguro porque `devicemotion` dispara por AMOSTRAGEM, e nao por
 * movimento: um celular parado na mesa continua emitindo dezenas de eventos
 * por segundo, todos perto de 9,81. Zero evento significa ausencia de sensor,
 * nao ausencia de movimento.
 */

/** Tempo de espera pela primeira amostra antes de declarar que nao ha sensor. */
export const ESPERA_DE_SINAL_MS = 2500;

export const MENSAGEM_SEM_SINAL =
  "Nenhuma amostra chegou do acelerometro. Computador nao tem esse sensor — " +
  "abra esta pagina no celular.";

export type EstadoDaColeta = "ocioso" | "coletando" | "erro";

/**
 * Estado do envio de uma epoca (APP-10).
 *
 * Tres estados EXPLICITOS, e nao um booleano `enviada` mais um `falha`
 * anulavel. A versao anterior codificava tres situacoes em dois campos, e a
 * tela leu como duas: `enviada ? check : X`. Resultado — a epoca aparecia com
 * X VERMELHO enquanto ainda estava sendo enviada, e virava check um segundo
 * depois. Alarme falso.
 *
 * Com um tipo de tres valores, esquecer um caso vira erro de compilacao em
 * vez de susto na tela.
 */
export type EstadoDoEnvio = "enviando" | "gravada" | "falhou";

export type Registro = {
  agregado: Agregado;
  envio: EstadoDoEnvio;
  falha: string | null;
};

/** `DeviceMotionEvent` com o `requestPermission` que so o iOS expoe. */
type ComPermissao = {
  requestPermission?: () => Promise<"granted" | "denied" | "default">;
};

export function suportaAcelerometro(): boolean {
  return typeof window !== "undefined" && "DeviceMotionEvent" in window;
}

/**
 * Pede permissao de sensor.
 *
 * No iOS 13+ `DeviceMotionEvent.requestPermission()` so funciona chamado a
 * partir de um gesto do usuario, e exige HTTPS. Nos demais navegadores a API
 * nao existe e nao ha o que pedir — daí o `true`.
 */
export async function pedirPermissao(): Promise<boolean> {
  const alvo = (window as unknown as { DeviceMotionEvent?: ComPermissao }).DeviceMotionEvent;
  if (typeof alvo?.requestPermission !== "function") return true;
  try {
    return (await alvo.requestPermission()) === "granted";
  } catch {
    return false;
  }
}

export function useColeta(epocaSegundos: number, dispositivoId: string | null) {
  const [estado, setEstado] = useState<EstadoDaColeta>("ocioso");
  const [erro, setErro] = useState<string | null>(null);
  const [registros, setRegistros] = useState<Registro[]>([]);
  const [amostrasNaEpoca, setAmostrasNaEpoca] = useState(0);

  // Refs, e nao estado: o listener dispara dezenas de vezes por segundo, e
  // re-renderizar a cada amostra derrubaria o quadro a quadro da propria
  // pagina que esta medindo.
  const buffer = useRef<Amostra[]>([]);
  const wakeLock = useRef<{ release: () => Promise<void> } | null>(null);
  // Refs para o que o listener e o temporizador consultam sem re-renderizar.
  const dispositivoRef = useRef(dispositivoId);
  dispositivoRef.current = dispositivoId;
  const jwtRef = useRef<string | null>(null);
  jwtRef.current = useAuth().sessao?.access_token ?? null;

  const fecharEpoca = useCallback(async () => {
    const amostras = buffer.current;
    buffer.current = [];
    setAmostrasNaEpoca(0);

    const agregado = agregar(amostras, epocaSegundos, Date.now());
    if (agregado === null) return; // época sem amostra não vira leitura

    const registro: Registro = { agregado, envio: "enviando", falha: null };
    setRegistros((atuais) => [registro, ...atuais]);

    const alvo = dispositivoRef.current;
    if (!alvo) {
      // Nao deveria acontecer — o botao so libera com o aparelho preparado.
      // Mas deixar a epoca presa em "enviando" para sempre seria pior que
      // dizer que nao deu.
      registro.envio = "falhou";
      registro.falha = "Aparelho ainda nao preparado.";
      setRegistros((atuais) => [...atuais]);
      return;
    }

    try {
      await enviarLeitura(montarPayload(agregado), alvo, jwtRef.current);
      registro.envio = "gravada";
    } catch (e) {
      registro.envio = "falhou";
      registro.falha =
        e instanceof ErroDeIngestao ? e.message : "Falha inesperada ao enviar.";
    }
    // Substitui pela mesma referencia mutada: a lista e curta e o objetivo e
    // so refletir o resultado do envio.
    setRegistros((atuais) => [...atuais]);
  }, [epocaSegundos]);

  const soltarTela = useCallback(() => {
    void wakeLock.current?.release().catch(() => {});
    wakeLock.current = null;
  }, []);

  const parar = useCallback(() => {
    setEstado("ocioso");
    soltarTela();
  }, [soltarTela]);

  const comecar = useCallback(async () => {
    setErro(null);

    if (!suportaAcelerometro()) {
      setErro("Este navegador nao expoe a API de acelerometro.");
      setEstado("erro");
      return;
    }
    if (!(await pedirPermissao())) {
      setErro("Permissao de sensor negada. No iOS, ela so pode ser concedida em HTTPS.");
      setEstado("erro");
      return;
    }

    buffer.current = [];
    setAmostrasNaEpoca(0);
    setEstado("coletando");

    // Sem isto a tela bloqueia e o `devicemotion` para. Falhar aqui nao
    // impede a coleta — so a encurta.
    try {
      const navegador = navigator as unknown as {
        wakeLock?: { request: (t: "screen") => Promise<{ release: () => Promise<void> }> };
      };
      wakeLock.current = (await navegador.wakeLock?.request("screen")) ?? null;
    } catch {
      wakeLock.current = null;
    }
  }, []);

  useEffect(() => {
    if (estado !== "coletando") return;

    const aoMover = (evento: DeviceMotionEvent) => {
      const a = evento.accelerationIncludingGravity;
      // `accelerationIncludingGravity` e o que casa com o contrato: magnitude
      // COM gravidade, ~9,81 em repouso. `acceleration` (sem gravidade) daria
      // ~0 em repouso e quebraria o limiar.
      if (!a || a.x == null || a.y == null || a.z == null) return;
      buffer.current.push({ ax: a.x, ay: a.y, az: a.z });
      setAmostrasNaEpoca(buffer.current.length);
    };

    window.addEventListener("devicemotion", aoMover);
    const relogio = setInterval(() => void fecharEpoca(), epocaSegundos * 1000);

    // Sonda de sinal. Ver a nota no topo do arquivo.
    const sonda = setTimeout(() => {
      if (buffer.current.length > 0) return;
      setErro(MENSAGEM_SEM_SINAL);
      setEstado("erro");
      soltarTela();
    }, ESPERA_DE_SINAL_MS);

    return () => {
      window.removeEventListener("devicemotion", aoMover);
      clearInterval(relogio);
      clearTimeout(sonda);
    };
  }, [estado, epocaSegundos, fecharEpoca, soltarTela]);

  // Solta o wake lock se o componente sair enquanto coletava.
  useEffect(() => () => void wakeLock.current?.release().catch(() => {}), []);

  return { estado, erro, registros, amostrasNaEpoca, comecar, parar };
}
