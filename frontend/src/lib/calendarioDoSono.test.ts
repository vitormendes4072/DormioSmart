import { describe, expect, it } from "vitest";

import type { LeituraSono } from "../types/sleep";
import {
  janelaDoCalendario,
  limitesDaConsulta,
  registrosDoCalendario,
  sequenciasDoCalendario,
} from "./calendarioDoSono";

const dia = (mes: number, data: number) => new Date(2026, mes - 1, data, 12);

describe("calendarioDoSono", () => {
  it("soma o tempo registrado de duas sessões no mesmo dia", () => {
    const leituras: LeituraSono[] = [[2, 0], [2, 30], [22, 0], [22, 30], [22, 60]].map(([hora, segundos]) => ({
      created_at: new Date(2026, 10, 24, hora, 1, segundos).toISOString(),
      epoca_segundos: 30,
      movimento_total: 9.81,
      temp: null,
      status: "Repouso",
    }));

    expect(registrosDoCalendario(leituras, dia(11, 24), dia(11, 24))).toEqual(
      new Map([[dia(11, 24).getTime(), 150_000]]),
    );
  });

  it("agrupa dias consecutivos mesmo com a entrada fora de ordem", () => {
    const registros = new Map([dia(11, 25), dia(11, 23), dia(11, 24)].map((data) => [data.getTime(), 0]));
    expect(sequenciasDoCalendario(registros)).toEqual([[dia(11, 23), dia(11, 24), dia(11, 25)]]);
  });

  it("abre outra sequência quando falta um dia de registro", () => {
    const registros = new Map([dia(11, 22), dia(11, 23), dia(11, 25)].map((data) => [data.getTime(), 0]));
    expect(sequenciasDoCalendario(registros)).toEqual([[dia(11, 25)], [dia(11, 22), dia(11, 23)]]);
  });

  it("mantém a sequência na virada do mês", () => {
    const registros = new Map([dia(10, 31), dia(11, 1)].map((data) => [data.getTime(), 0]));
    expect(sequenciasDoCalendario(registros)).toEqual([[dia(10, 31), dia(11, 1)]]);
  });

  it("consulta a véspera e o dia seguinte completos", () => {
    expect(limitesDaConsulta(dia(10, 31), dia(11, 1))).toEqual({
      desde: new Date(2026, 9, 30).toISOString(),
      ate: new Date(2026, 10, 2, 23, 59, 59, 999).toISOString(),
    });
  });

  it("inclui a semana anterior quando o mês começa no domingo", () => {
    expect(janelaDoCalendario(dia(11, 15))).toEqual({
      inicio: dia(10, 26),
      fim: dia(12, 6),
      diasNoMes: 30,
      deslocamento: 6,
    });
  });
});
