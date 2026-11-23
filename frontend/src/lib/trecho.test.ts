import { describe, expect, it, vi } from "vitest";

import type { LeituraSono } from "../types/sleep";
import { ehBancada, impressaoDosIds, semBancada, sessoesDaMarca, trechoDaSessao } from "./trecho";

let proximoId = 0;
const leitura = (extra: Partial<LeituraSono> = {}): LeituraSono => ({
  id: `00000000-0000-0000-0000-${String(++proximoId).padStart(12, "0")}`,
  created_at: "2026-11-17T12:00:00.000Z",
  movimento_total: 9.8,
  temp: null,
  status: "Repouso",
  device_id: "d1",
  ...extra,
});

describe("trechoDaSessao (DATA-16)", () => {
  it("vai do primeiro ao último instante MEDIDO, em qualquer ordem de chegada", () => {
    const trecho = trechoDaSessao([
      leitura({ captured_at: "2026-11-17T05:00:30.000Z" }),
      leitura({ captured_at: "2026-11-17T05:35:00.000Z" }),
      leitura({ captured_at: "2026-11-17T05:00:00.000Z" }),
    ]);
    expect(trecho).toMatchObject({ device: "d1", desde: "2026-11-17T05:00:00.000Z", ate: "2026-11-17T05:35:00.000Z" });
  });

  it("usa a chegada quando a medição não foi declarada, como o banco (coalesce)", () => {
    const trecho = trechoDaSessao([
      leitura({ captured_at: null, created_at: "2026-11-17T06:00:00.000Z" }),
      leitura({ captured_at: "2026-11-17T05:00:00.000Z" }),
    ]);
    expect(trecho).toMatchObject({ device: "d1", desde: "2026-11-17T05:00:00.000Z", ate: "2026-11-17T06:00:00.000Z" });
  });

  it("não age sem leitura, sem aparelho ou com aparelhos misturados", () => {
    expect(trechoDaSessao([])).toBeNull();
    expect(trechoDaSessao([leitura({ device_id: null })])).toBeNull();
    expect(trechoDaSessao([leitura(), leitura({ device_id: "d2" })])).toBeNull();
  });
});

describe("a marca de bancada", () => {
  it("só conta o verdadeiro explícito", () => {
    expect(ehBancada(leitura({ bancada: true }))).toBe(true);
    expect(ehBancada(leitura({ bancada: false }))).toBe(false);
    expect(ehBancada(leitura({ bancada: null }))).toBe(false);
    expect(ehBancada(leitura())).toBe(false);
  });

  it("semBancada tira as marcadas e devolve a mesma lista quando não há nenhuma", () => {
    const normal = leitura();
    const marcada = leitura({ bancada: true });
    expect(semBancada([normal, marcada])).toEqual([normal]);
    const sem = [normal];
    expect(semBancada(sem)).toBe(sem);
  });
});

describe("o trecho leva só o que a tela mostrou (UI-38)", () => {
  it("manda o instante original, com os microssegundos e o fuso que vieram", () => {
    const desde = "2026-11-17T05:00:00.000456+00:00";
    const ate = "2026-11-17T05:01:30.12345+00:00";
    expect(trechoDaSessao([
      leitura({ captured_at: null, created_at: ate }),
      leitura({ captured_at: null, created_at: desde }),
    ])).toMatchObject({ device: "d1", desde, ate });
  });

  it("ordena dentro do mesmo milissegundo, e entre fusos", () => {
    const antes = "2026-11-17T05:00:00.1231+00:00";
    const depois = "2026-11-17T02:00:00.123999-03:00";
    expect(trechoDaSessao([leitura({ captured_at: depois }), leitura({ captured_at: antes })]))
      .toMatchObject({ device: "d1", desde: antes, ate: depois });
  });

  it("não age quando a janela pega época do mesmo aparelho fora da sessão", () => {
    const a = leitura({ captured_at: "2026-11-17T05:00:00Z" });
    const alheia = leitura({ captured_at: "2026-11-17T05:00:30Z", bancada: true });
    const b = leitura({ captured_at: "2026-11-17T05:01:00Z" });
    expect(trechoDaSessao([a, b], [a, alheia, b])).toBeNull();
  });

  it("o instante empatado com outra marca também trava a ação", () => {
    const a = leitura({ captured_at: "2026-11-17T05:00:00Z" });
    const mesma = leitura({ captured_at: "2026-11-17T05:00:00Z", bancada: true });
    expect(trechoDaSessao([a], [a, mesma])).toBeNull();
  });

  it("época de outro aparelho na janela não conta", () => {
    const a = leitura({ captured_at: "2026-11-17T05:00:00Z" });
    const outro = leitura({ captured_at: "2026-11-17T05:00:00Z", device_id: "d2" });
    expect(trechoDaSessao([a], [a, outro])).not.toBeNull();
  });
});

describe("sessoesDaMarca (UI-38)", () => {
  const serie = (de: number, n: number, extra: Partial<LeituraSono> = {}) =>
    Array.from({ length: n }, (_, i) => leitura({
      captured_at: new Date(Date.parse("2026-11-17T05:00:00Z") + (de + i) * 30_000).toISOString(),
      epoca_segundos: 30,
      ...extra,
    }));
  const tamanhos = (todas: LeituraSono[], bancada: boolean) =>
    sessoesDaMarca(todas, bancada).map((sessao) => sessao.leituras.length);

  it("corta onde a marca muda, dos dois lados", () => {
    const todas = [...serie(0, 20), ...serie(20, 10, { bancada: true }), ...serie(30, 20)];
    expect(tamanhos(todas, false)).toEqual([20, 20]);
    expect(tamanhos(todas, true)).toEqual([10]);
  });

  it("cada pedaço começa onde começa a sua primeira época", () => {
    const todas = [...serie(0, 20), ...serie(20, 1, { bancada: true }), ...serie(21, 20)];
    const [antes, depois] = sessoesDaMarca(todas, false);
    expect(antes.fim).toBe(Date.parse("2026-11-17T05:09:30Z"));
    expect(depois.inicio).toBe(Date.parse("2026-11-17T05:10:00Z"));
  });

  it("a ordem de chegada não muda o corte", () => {
    const todas = [...serie(0, 20), ...serie(20, 10, { bancada: true }), ...serie(30, 20)].reverse();
    expect(tamanhos(todas, false)).toEqual([20, 20]);
  });

  it("sem marca no meio, a pausa curta não corta", () => {
    expect(tamanhos([...serie(0, 20), ...serie(30, 20)], false)).toEqual([40]);
  });

  it("a bancada de um aparelho não parte a sessão contínua de outro", () => {
    const todas = [...serie(0, 50), ...serie(20, 10, { bancada: true, device_id: "d2" })];
    expect(tamanhos(todas, false)).toEqual([50]);
  });
});


describe("DATA-17: identidade da sessão", () => {
  it("não oferece ação para leitura sem id", () => {
    expect(trechoDaSessao([leitura({ id: undefined })])).toBeNull();
  });
});


it("DATA-17: hash canônico independe da ordem e da caixa", async () => {
  const ids = ["FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF", "00000000-0000-0000-0000-000000000001"];
  expect(await impressaoDosIds(ids)).toBe("20ee2864a148031ef14ad1732f7ecebf7e5d06b9d9e71336b0c24629afc119d5");
});


it("DATA-17: sem SHA-256 não oferece ação", () => {
  try {
    for (const crypto of [{}, { subtle: {} }]) {
      vi.stubGlobal("crypto", crypto);
      expect(trechoDaSessao([leitura()])).toBeNull();
    }
  } finally { vi.unstubAllGlobals(); }
});
