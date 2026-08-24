import { GRAVIDADE, LIMIAR_DE_MOVIMENTO } from "../types/sleep";

/**
 * Agregacao das amostras do acelerometro por epoca (APP-01, contrato v2.0.0).
 *
 * ── POR QUE AGREGAR ─────────────────────────────────────────────────────
 *
 * O ESP32 manda uma linha por evento: acorda, mede, dorme. Um celular
 * amostrando a 50 Hz geraria ~180 mil linhas por hora. A coleta resume uma
 * janela e envia uma linha por epoca.
 *
 * ── POR QUE O PICO, E NAO A MEDIA ───────────────────────────────────────
 *
 * A media sobre 60 s dilui um giro de 2 s ate ele sumir — exatamente o evento
 * que se quer registrar. O pico preserva a detectabilidade E mantem unidade e
 * limiar: `total` continua sendo magnitude em m/s², e o criterio continua
 * sendo |total − 9,81| > 1,2, sem excecao para o celular.
 *
 * Consequencia que fez o metodo ser escolhido: enviamos os eixos DA AMOSTRA DE
 * PICO, entao a checagem de coerencia do backend (|total − √(ax²+ay²+az²)| ≤
 * 0,5) continua valendo sem caso especial.
 *
 * `pico-da-magnitude` e provisorio — o CALC-03 formaliza o indice de atividade.
 * O identificador viaja com cada leitura justamente para que trocar de metodo
 * depois nao torne o historico ambiguo.
 *
 * Tudo aqui e funcao pura: a plumbing do navegador vive no hook.
 */

export const METODO = "pico-da-magnitude";

/** Duracao da epoca, em segundos. 30 s e a convencao classica de actigrafia. */
export const EPOCA_PADRAO_S = 30;
export const EPOCAS_DISPONIVEIS_S = [10, 30, 60] as const;

export type Amostra = { ax: number; ay: number; az: number };

/** Uma epoca fechada, pronta para virar payload. */
export type Agregado = {
  ax: number;
  ay: number;
  az: number;
  total: number;
  amostras: number;
  epocaSegundos: number;
  /** Instante do fim da janela — quando a epoca fechou. */
  fimEmMs: number;
};

/** Magnitude do vetor de aceleracao, com a gravidade incluida. */
export function magnitude({ ax, ay, az }: Amostra): number {
  return Math.sqrt(ax * ax + ay * ay + az * az);
}

/** Desvio em relacao ao repouso. E sobre ele que o limiar age. */
export function desvio(amostra: Amostra): number {
  return Math.abs(magnitude(amostra) - GRAVIDADE);
}

/**
 * Classifica pela mesma regra do firmware (DATA-02).
 *
 * Quem classifica e o DISPOSITIVO — e aqui o dispositivo e o proprio celular.
 * Por isso a regra vive no coletor, e nao no painel: o painel nunca
 * reclassifica, so exibe o rotulo recebido.
 */
export function classificar(amostra: Amostra): "Movimento" | "Repouso" {
  return desvio(amostra) > LIMIAR_DE_MOVIMENTO ? "Movimento" : "Repouso";
}

/**
 * Reduz um lote de amostras a uma epoca.
 *
 * Devolve `null` para lote vazio: uma epoca sem amostra nao e "repouso", e
 * inventar uma linha de repouso ai seria fabricar medicao. Acontece de
 * verdade — o navegador suspende `devicemotion` quando a aba vai para o fundo.
 */
export function agregar(
  amostras: Amostra[],
  epocaSegundos: number,
  fimEmMs: number,
): Agregado | null {
  if (amostras.length === 0) return null;

  let pico = amostras[0];
  let maiorDesvio = desvio(pico);

  for (const amostra of amostras) {
    const d = desvio(amostra);
    if (d > maiorDesvio) {
      maiorDesvio = d;
      pico = amostra;
    }
  }

  return {
    // Duas casas, como o firmware transmite — mantem a tolerancia de
    // coerencia do backend na mesma ordem de grandeza para as duas fontes.
    ax: arredondar(pico.ax),
    ay: arredondar(pico.ay),
    az: arredondar(pico.az),
    total: arredondar(magnitude(pico)),
    amostras: amostras.length,
    epocaSegundos,
    fimEmMs,
  };
}

function arredondar(valor: number): number {
  return Number(valor.toFixed(2));
}

/** Payload de `POST /api/data`, contrato v2.0.0. */
export type PayloadDeLeitura = {
  ax: number;
  ay: number;
  az: number;
  total: number;
  status: string;
  ts: string;
  epoca_s: number;
  metodo: string;
  amostras: number;
};

/**
 * Monta o corpo da ingestao.
 *
 * Sem `t` e sem `gx/gy/gz`, de proposito: celular nao tem temperatura de chip
 * do MPU6050, e o giroscopio nao entra em nenhum criterio. Mandar numero
 * inventado seria mentir no dado — o contrato v2.0.0 tornou os dois opcionais
 * exatamente para isso.
 */
export function montarPayload(agregado: Agregado): PayloadDeLeitura {
  const { ax, ay, az, total, amostras, epocaSegundos, fimEmMs } = agregado;
  return {
    ax,
    ay,
    az,
    total,
    status: classificar({ ax, ay, az }),
    ts: new Date(fimEmMs).toISOString(),
    epoca_s: epocaSegundos,
    metodo: METODO,
    amostras,
  };
}
