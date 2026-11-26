import { describe, expect, it } from "vitest";

import type { LeituraSono } from "../types/sleep";
import {
  janelaDoCalendario,
  limitesDaConsulta,
  registrosDoCalendario,
  sequenciasDoCalendario,
  sessoesDoDia,
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

describe("sessoesDoDia (UI-46)", () => {
  const sessao = (hora: number, minuto: number, bancada = false): LeituraSono[] =>
    Array.from({ length: 3 }, (_, i) => ({
      created_at: new Date(2026, 10, 24, hora, minuto, (i + 1) * 30).toISOString(),
      epoca_segundos: 30,
      movimento_total: 9.81,
      temp: null,
      status: "Repouso",
      bancada,
    }));

  it("atribui ao dia de início uma sessão que termina depois da meia-noite", () => {
    const dados = sessao(23, 59);
    const sessoes = sessoesDoDia(dados, dia(11, 24));
    expect(sessoes).toHaveLength(1);
    expect(sessoes[0].leituras).toHaveLength(3);
    expect(new Date(sessoes[0].fim).getDate()).toBe(25);
    expect(sessoesDoDia(dados, dia(11, 25))).toEqual([]);
  });

  it("devolve vazio quando o dia não tem sessão", () => {
    expect(sessoesDoDia(sessao(5, 0), dia(11, 23))).toEqual([]);
  });

  it("devolve as duas sessões do dia em ordem de início", () => {
    expect(sessoesDoDia([...sessao(9, 0), ...sessao(1, 0)], dia(11, 24))
      .map(({ inicio }) => new Date(inicio).getHours())).toEqual([1, 9]);
  });

  it("exclui a sessão marcada como bancada", () => {
    const sessoes = sessoesDoDia([...sessao(1, 0), ...sessao(9, 0, true)], dia(11, 24));
    expect(sessoes).toHaveLength(1);
    expect(new Date(sessoes[0].inicio).getHours()).toBe(1);
  });
});
