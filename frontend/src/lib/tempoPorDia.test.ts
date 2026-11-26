import { expect, it } from "vitest";

import { registrosDoCalendario, serieDaSemana } from "./calendarioDoSono";
import type { LeituraSono } from "../types/sleep";

const dia = (data: number) => new Date(2026, 10, data, 12);
const hora = 3_600_000;
const mapa = (tempos: Array<[number, number]>) =>
  new Map(tempos.map(([data, horas]) => [dia(data).getTime(), horas * hora]));

it("UI-47: ordena de segunda a domingo, separa ausência de zero e exclui o futuro", () => {
  const { dias, comRegistro } = serieDaSemana(mapa([[24, 0], [23, 2], [27, 9]]), dia(26), dia(26), false);
  expect(dias.map(({ rotulo }) => rotulo)).toEqual(["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]);
  expect(dias.map(({ estado }) => estado)).toEqual([
    "registrado", "registrado", "sem-registro", "sem-registro", "futuro", "futuro", "futuro",
  ]);
  expect(dias.map(({ tempoMs }) => tempoMs)).toEqual([2 * hora, 0, null, null, null, null, null]);
  expect(comRegistro.map(({ rotulo }) => rotulo)).toEqual(["Seg", "Ter"]);
});

it("UI-47: calcula a média apenas dos dias com registro", () => {
  const { media } = serieDaSemana(mapa([[23, 4], [25, 7]]), dia(25), dia(29), false);
  expect(media).toBe(5.5 * hora);
});

it("UI-47: inclui todos os dias empatados nos extremos", () => {
  const { maiores, menores } = serieDaSemana(mapa([[23, 8], [24, 4], [25, 8], [28, 4]]), dia(23), dia(29), false);
  expect(maiores.map(({ rotulo }) => rotulo)).toEqual(["Seg", "Qua"]);
  expect(menores.map(({ rotulo }) => rotulo)).toEqual(["Ter", "Sáb"]);
});

it("UI-47: exclui dias indeterminados da média e dos extremos", () => {
  const { dias, media, maiores, menores } = serieDaSemana(mapa([[23, 4], [25, 6]]), dia(25), dia(26), true);
  expect(dias[1]).toMatchObject({ estado: "incompleto", tempoMs: null });
  expect(dias[4]).toMatchObject({ estado: "futuro", tempoMs: null });
  expect(media).toBe(5 * hora);
  expect(maiores.map(({ rotulo }) => rotulo)).toEqual(["Qua"]);
  expect(menores.map(({ rotulo }) => rotulo)).toEqual(["Seg"]);
});

const fonte = (device_id: string, inicio: number, pontos: number, bancada = false): LeituraSono[] =>
  Array.from({ length: pontos }, (_, i) => ({
    device_id,
    created_at: new Date(inicio + (i + 1) * 30_000).toISOString(),
    epoca_segundos: 30,
    movimento_total: 9.81,
    temp: null,
    status: "Repouso",
    bancada,
  }));

it("UI-47: mantém o valor do calendário no dia de início e exclui bancada", () => {
  const registros = registrosDoCalendario([
    ...fonte("p", new Date(2026, 10, 24, 23, 59).getTime(), 4),
    ...fonte("c", new Date(2026, 10, 27, 6).getTime(), 4),
    ...fonte("p", new Date(2026, 10, 26, 6).getTime(), 4, true),
  ], dia(23), dia(29));
  const { dias } = serieDaSemana(registros, dia(24), dia(29), false);
  for (const valor of dias) expect(valor.tempoMs).toBe(registros.get(valor.data.getTime()) ?? null);
  expect(dias.map(({ tempoMs }) => tempoMs)).toEqual([null, 120_000, null, null, 120_000, null, null]);
});

it.each([[0, 7], [2, 9]])("UI-47: duas fontes de 7h com deslocamento de %ih resultam em %ih", (atraso, total) => {
  const inicio = new Date(2026, 10, 24, 1).getTime();
  const registros = registrosDoCalendario([
    ...fonte("p", inicio, 840),
    ...fonte("c", inicio + atraso * hora, 840),
  ], dia(23), dia(29));
  expect(registros.get(dia(24).getTime())).toBe(total * hora);
  expect(serieDaSemana(registros, dia(24), dia(29), false).dias[1].tempoMs).toBe(total * hora);
});
