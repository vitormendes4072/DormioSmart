/**
 * O trecho de uma sessão — aparelho, início e fim — e a marca de bancada (DATA-16).
 *
 * O servidor guarda épocas, e não sessões: a sessão é desenhada aqui, pelas
 * pausas no envio (`agruparEmSessoes`). Para excluir ou marcar uma, o app manda
 * ao backend o aparelho e o primeiro e o último instante das épocas DELA, pelo
 * mesmo `instanteDaLeitura` que o banco usa (`coalesce(captured_at,
 * created_at)`, migração 023). Assim o que sai do banco é exatamente o que a
 * tela mostrou como uma sessão.
 */
import { instanteDaLeitura, type LeituraSono } from "../types/sleep";

export type Trecho = { device: string; desde: string; ate: string };

/**
 * O trecho das leituras de UMA sessão, ou `null` quando não há como agir sobre
 * ela: sem leitura, sem aparelho (linhas anteriores ao multiusuário) ou com
 * mais de um aparelho misturado.
 */
export function trechoDaSessao(leituras: LeituraSono[]): Trecho | null {
  if (leituras.length === 0) return null;
  const device = leituras[0].device_id;
  if (!device || leituras.some((leitura) => leitura.device_id !== device)) return null;
  let primeiro = Infinity;
  let ultimo = -Infinity;
  for (const leitura of leituras) {
    const instante = Date.parse(instanteDaLeitura(leitura));
    if (!Number.isFinite(instante)) return null;
    primeiro = Math.min(primeiro, instante);
    ultimo = Math.max(ultimo, instante);
  }
  return { device, desde: new Date(primeiro).toISOString(), ate: new Date(ultimo).toISOString() };
}

/** A época que o titular marcou como bancada/teste. */
export function ehBancada(leitura: LeituraSono): boolean {
  return leitura.bancada === true;
}

/** O que o painel e as análises veem: tudo, menos o marcado como bancada. */
export function semBancada(leituras: LeituraSono[]): LeituraSono[] {
  return leituras.some(ehBancada) ? leituras.filter((leitura) => !ehBancada(leitura)) : leituras;
}
