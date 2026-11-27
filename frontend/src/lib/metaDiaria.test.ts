import { expect, it } from "vitest";

import { serieDaSemana } from "./calendarioDoSono";
import { lerMetaDiaria, projetarMeta } from "./metaDiaria";

const dia = (numero: number) => new Date(2026, 10, numero, 12);
const hoje = dia(26);
const registros = (pares: Array<[number, number]>) =>
  new Map(pares.map(([numero, horas]) => [dia(numero).getTime(), horas * 3_600_000]));

it("UI-61: valida o campo opcional em horas e passos de 15 minutos", () => {
  expect(lerMetaDiaria("")).toEqual({ ok: true, valor: null });
  expect(lerMetaDiaria("6:45")).toEqual({ ok: true, valor: 405 });
  for (const texto of ["0:45", "16:15", "6:11", "6.75", "1:60"]) expect(lerMetaDiaria(texto).ok).toBe(false);
});

it("UI-61: usa a média dos dias com registro e conta hoje vazio e os dias futuros", () => {
  const serie = serieDaSemana(registros([[23, 6], [24, 6]]), hoje, hoje, false);
  expect(projetarMeta(serie, 480, hoje, false)).toEqual({ tipo: "possivel", restantes: 4, porDia: 540 });
});

it("UI-61: distingue meta alcançada e meta fora do alcance com dias restantes", () => {
  const boa = serieDaSemana(registros([[23, 8]]), hoje, hoje, false);
  const baixa = serieDaSemana(registros([[23, 1]]), hoje, hoje, false);
  expect(projetarMeta(boa, 480, hoje, false)).toEqual({ tipo: "atingida" });
  expect(projetarMeta(baixa, 960, hoje, false)).toEqual({ tipo: "fora-do-alcance" });
});

it("UI-61: encerra a projeção em uma semana passada e omite projeção sem média ou com dados parciais", () => {
  const passada = serieDaSemana(registros([[17, 2]]), dia(17), hoje, false);
  expect(projetarMeta(passada, 480, hoje, false)).toEqual({ tipo: "fora-do-alcance" });
  expect(projetarMeta(passada, 480, hoje, true)).toBeNull();
  expect(projetarMeta(serieDaSemana(new Map(), hoje, hoje, false), 480, hoje, false)).toBeNull();
});
