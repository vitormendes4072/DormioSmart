import { describe, expect, it } from "vitest";

import type { LeituraSono } from "../types/sleep";
import { ehBancada, semBancada, trechoDaSessao } from "./trecho";

const leitura = (extra: Partial<LeituraSono> = {}): LeituraSono => ({
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
    expect(trecho).toEqual({ device: "d1", desde: "2026-11-17T05:00:00.000Z", ate: "2026-11-17T05:35:00.000Z" });
  });

  it("usa a chegada quando a medição não foi declarada, como o banco (coalesce)", () => {
    const trecho = trechoDaSessao([
      leitura({ captured_at: null, created_at: "2026-11-17T06:00:00.000Z" }),
      leitura({ captured_at: "2026-11-17T05:00:00.000Z" }),
    ]);
    expect(trecho).toEqual({ device: "d1", desde: "2026-11-17T05:00:00.000Z", ate: "2026-11-17T06:00:00.000Z" });
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
