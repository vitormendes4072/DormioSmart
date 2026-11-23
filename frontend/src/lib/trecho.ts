/**
 * O trecho de uma sessão — aparelho, início e fim — e a marca de bancada (DATA-16).
 *
 * O servidor guarda épocas, e não sessões: a sessão é desenhada aqui, pelas
 * pausas no envio (`agruparEmSessoes`). Para excluir ou marcar uma, o app manda
 * ao backend o aparelho e o primeiro e o último instante das épocas DELA, pelo
 * mesmo `instanteDaLeitura` que o banco usa (`coalesce(captured_at,
 * created_at)`, migração 023).
 *
 * Para que a janela represente a sessão carregada (UI-38):
 *  - a sessão é cortada onde a marca muda (`sessoesDaMarca`);
 *  - os instantes vão como vieram: o `Date` do JS corta os microssegundos do
 *    Postgres, e a última época ficava fora da janela;
 *  - se ainda assim a janela pegar outra época carregada, não há ação.
 * A 025 confere contagem, marca e SHA-256 dos IDs no banco e age somente
 * sobre IDs travados. Inserções posteriores à conferência ficam fora.
 */
import { instanteDaLeitura, type LeituraSono } from "../types/sleep";
import { agruparEmSessoes, calcularCobertura, type Sessao } from "./cobertura";

export type Trecho = { device: string; desde: string; ate: string; epocas_esperadas: number; bancada_atual: boolean; ids: string[] };

// UUID canônico minúsculo, ordenado por comparação simples; unir com vírgulas,
// sem espaços nem vírgula final, codificar em UTF-8 e SHA-256 em hex minúsculo.
// A ordem é a mesma de ORDER BY id (uuid), independente da collation.
export async function impressaoDosIds(ids: string[]): Promise<string> {
  if (typeof globalThis.crypto?.subtle?.digest !== "function") throw new Error("Não foi possível conferir esta sessão neste aparelho.");
  const dados = new TextEncoder().encode([...ids].map((id) => id.toLowerCase()).sort().join(","));
  const hash = await globalThis.crypto.subtle.digest("SHA-256", dados);
  return Array.from(new Uint8Array(hash), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

const calculados = new WeakMap<LeituraSono, number>();

/** O instante em microssegundos, a resolução do Postgres. Cabe num inteiro seguro. */
function micro(leitura: LeituraSono): number {
  let valor = calculados.get(leitura);
  if (valor === undefined) {
    const iso = instanteDaLeitura(leitura);
    const resto = /\.\d{3}(\d{1,3})/.exec(iso)?.[1] ?? "";
    valor = Date.parse(iso) * 1000 + Number(resto.padEnd(3, "0"));
    calculados.set(leitura, valor);
  }
  return valor;
}

/**
 * O trecho das leituras de UMA sessão, ou `null` quando não há como agir sobre
 * ela: sem leitura, sem aparelho (linhas anteriores ao multiusuário), com mais
 * de um aparelho misturado, ou com outra época de `carregadas` dentro da janela.
 */
export function trechoDaSessao(leituras: LeituraSono[], carregadas = leituras): Trecho | null {
  if (leituras.length === 0 || typeof globalThis.crypto?.subtle?.digest !== "function") return null;
  const ids = leituras.map((leitura) => leitura.id?.toLowerCase() ?? "");
  if (ids.some((id) => !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(id))
      || new Set(ids).size !== ids.length) return null;
  if (leituras.some((leitura) => ehBancada(leitura) !== ehBancada(leituras[0]))) return null;
  const device = leituras[0].device_id;
  if (!device || leituras.some((leitura) => leitura.device_id !== device)) return null;
  let primeira = leituras[0];
  let ultima = leituras[0];
  for (const leitura of leituras) {
    if (!Number.isFinite(micro(leitura))) return null;
    if (micro(leitura) < micro(primeira)) primeira = leitura;
    if (micro(leitura) > micro(ultima)) ultima = leitura;
  }
  const naJanela = carregadas.filter((leitura) => leitura.device_id === device
    && micro(leitura) >= micro(primeira) && micro(leitura) <= micro(ultima));
  if (naJanela.length !== leituras.length) return null;
  return { device, desde: instanteDaLeitura(primeira), ate: instanteDaLeitura(ultima), epocas_esperadas: leituras.length, bancada_atual: ehBancada(leituras[0]), ids };
}

/** A época que o titular marcou como bancada/teste. */
export function ehBancada(leitura: LeituraSono): boolean {
  return leitura.bancada === true;
}

/**
 * As sessões das leituras com uma das marcas, em ordem, cortadas onde houver
 * leitura com a outra marca entre duas seguidas do mesmo aparelho. A bancada
 * de um aparelho não parte a sessão de outro.
 */
export function sessoesDaMarca(leituras: LeituraSono[], bancada: boolean): Sessao[] {
  const minhas = leituras.filter((leitura) => ehBancada(leitura) === bancada);
  const sessoes = agruparEmSessoes(minhas);
  if (minhas.length === leituras.length) return sessoes;

  const outras = leituras
    .filter((leitura) => ehBancada(leitura) !== bancada && Number.isFinite(micro(leitura)))
    .sort((a, b) => micro(a) - micro(b));
  let j = 0;
  return sessoes.flatMap((sessao) => {
    const ordenadas = [...sessao.leituras].sort((a, b) => micro(a) - micro(b));
    const pedacos = [[ordenadas[0]]];
    for (let i = 1; i < ordenadas.length; i++) {
      const anterior = ordenadas[i - 1];
      const atual = ordenadas[i];
      let cortar = false;
      while (j < outras.length && micro(outras[j]) < micro(atual)) {
        const outra = outras[j++];
        cortar ||= micro(outra) > micro(anterior)
          && outra.device_id === anterior.device_id && outra.device_id === atual.device_id;
      }
      if (cortar) pedacos.push([atual]);
      else pedacos[pedacos.length - 1].push(atual);
    }
    if (pedacos.length === 1) return [sessao];
    return pedacos.map((pedaco) => {
      const { trechos } = calcularCobertura(pedaco);
      return { inicio: trechos[0].inicio, fim: trechos[trechos.length - 1].fim, leituras: pedaco };
    });
  });
}

/** O que o painel e as análises veem: tudo, menos o marcado como bancada. */
export function semBancada(leituras: LeituraSono[]): LeituraSono[] {
  return leituras.some(ehBancada) ? leituras.filter((leitura) => !ehBancada(leitura)) : leituras;
}
