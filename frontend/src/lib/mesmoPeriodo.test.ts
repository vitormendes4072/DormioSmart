/**
 * UI-56: o mesmo período gravado por aparelhos diferentes vira um grupo; nada é somado.
 */
import { describe, expect, it } from "vitest";

import { agruparMesmoPeriodo, duracaoDaUniao } from "./mesmoPeriodo";

const H = 3_600_000;
const s = (chave: string, aparelho: string, de: number, ate: number) => ({ chave, aparelho, inicio: de * H, fim: ate * H });
const chaves = (grupos: Array<Array<{ chave: string }>>) => grupos.map((g) => g.map((x) => x.chave));

describe("agruparMesmoPeriodo", () => {
  it("o celular e o travesseiro na mesma noite ficam juntos", () => {
    expect(chaves(agruparMesmoPeriodo([s("t", "trav", 23, 31), s("c", "cel", 22.8, 31.2)]))).toEqual([["c", "t"]]);
  });

  it("junta com 30% da sessão mais curta, e não com menos", () => {
    // A mais curta tem 2 h: 36 min de sobreposição é 30%; 30 min, 25%.
    expect(chaves(agruparMesmoPeriodo([s("t", "trav", 0, 8), s("c", "cel", 7.4, 9.4)]))).toEqual([["t", "c"]]);
    expect(chaves(agruparMesmoPeriodo([s("t", "trav", 0, 8), s("c", "cel", 7.5, 9.5)]))).toEqual([["c"], ["t"]]);
  });

  it("um teste de bancada à tarde não entra na noite", () => {
    const grupos = agruparMesmoPeriodo([s("noite", "trav", 23, 31), s("tarde", "cel", 14, 16)]);
    expect(chaves(grupos)).toEqual([["noite"], ["tarde"]]);
  });

  it("duas sessões do mesmo aparelho nunca se juntam por aqui", () => {
    expect(chaves(agruparMesmoPeriodo([s("a", "trav", 0, 4), s("b", "trav", 2, 6)]))).toEqual([["b"], ["a"]]);
  });

  it("a ligação é transitiva: o travesseiro reiniciado fica no grupo do celular", () => {
    const grupos = agruparMesmoPeriodo([s("t1", "trav", 23, 26), s("t2", "trav", 26.5, 31), s("c", "cel", 23, 31)]);
    expect(chaves(grupos)).toEqual([["t1", "c", "t2"]]);
  });
});

describe("duracaoDaUniao", () => {
  it("conta o tempo em que pelo menos um registrou, sem somar a sobreposição", () => {
    expect(duracaoDaUniao([{ inicio: 0, fim: 6 * H }, { inicio: 2 * H, fim: 7 * H }, { inicio: 9 * H, fim: 10 * H }])).toBe(8 * H);
    expect(duracaoDaUniao([])).toBe(0);
  });
});
