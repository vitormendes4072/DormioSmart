// @vitest-environment jsdom
/**
 * UI-40: o resumo no topo do Início. O que se confere aqui é que cada frase diz
 * o que a conta diz, inclusive nas bordas (zero, um, todas as sessões).
 */
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { agruparEmSessoes } from "../lib/cobertura";
import { calcularMetricas } from "../lib/metricas";
import type { LeituraSono } from "../types/sleep";
import { ResumoDaSessao } from "./ResumoDaSessao";

afterEach(cleanup);

// Hora local, para o texto não depender do fuso de quem roda.
const BASE = new Date(2026, 10, 17, 2, 44).getTime();

/** Blocos de épocas de 30 s a partir de `inicio`, com silêncio antes de cada um. */
function serie(
  blocos: Array<[epocas: number, silencioMs?: number]>,
  { inicio = BASE, movimentoACada = 0 } = {},
): LeituraSono[] {
  const lista: LeituraSono[] = [];
  let t = inicio;
  for (const [n, silencio = 0] of blocos) {
    t += silencio;
    for (let i = 0; i < n; i++) {
      t += 30_000;
      lista.push({
        created_at: new Date(t).toISOString(),
        movimento_total: 9.81,
        temp: null,
        status: movimentoACada && i % movimentoACada === 0 ? "Movimento" : "Repouso",
        epoca_segundos: 30,
      });
    }
  }
  return lista;
}

function texto(leituras: LeituraSono[], verTudo = false): string {
  const sessoes = agruparEmSessoes(leituras);
  const exibidas = verTudo ? sessoes : sessoes.slice(-1);
  const { container } = render(
    <ResumoDaSessao
      sessoes={exibidas}
      verTudo={verTudo}
      metricas={calcularMetricas(verTudo ? leituras : exibidas[0].leituras)}
    />,
  );
  return container.textContent!.replace(/\s+/g, " ");
}

describe("ResumoDaSessao (UI-40)", () => {
  it("a noite com duas pausas: quando, quanto, quantas paradas", () => {
    const t = texto(serie([[11], [708, 129_000], [67, 91_000]]));
    expect(t).not.toContain("Última sessão ·");
    expect(t).toContain("17/11, das 02:44 às 09:");
    expect(t).toMatch(/6h 33m de 6h 36m/);
    expect(t).toContain("2 pausasMaior pausa: 2m 9s");
  });

  it("uma parada fica no singular", () => {
    expect(texto(serie([[20], [20, 150_000]]))).toContain("1 pausaDuração: 2m 30s");
  });

  it("sem interrupção, diz que não parou", () => {
    expect(texto(serie([[40]]))).toContain("Sem pausas");
  });

  it("movimento é fração do tempo, e pouco não vira nenhum", () => {
    expect(texto(serie([[100]], { movimentoACada: 10 }))).toContain("10%Com movimento no tempo registrado");
    cleanup();
    expect(texto(serie([[200]], { movimentoACada: 200 }))).toContain("<1%Com movimento no tempo registrado");
  });

  it("o maior período sem movimento registrado não atravessa a parada", () => {
    texto(serie([[20], [30, 150_000]]));
    const cartao = within(screen.getByRole("list", { name: "Métricas da sessão" })).getAllByRole("listitem")[1];
    expect(within(cartao).getByRole("strong").textContent).toBe("15m 0s");
    expect(cartao.textContent).toContain("Maior período sem movimento registrado");
  });

  it("a sessão que cruza a meia-noite diz os dois dias", () => {
    const t = texto(serie([[960]], { inicio: new Date(2026, 10, 16, 23, 0).getTime() }));
    expect(t).toContain("de 16/11, 23:00 a 17/11, 07:00");
  });

  it("em todas as sessões, o intervalo entre elas não é parada nem denominador", () => {
    const t = texto(serie([[20], [20, 150_000], [40, 8 * 3_600_000]]), true);
    expect(t).toContain("40m 0s em 2 sessões");
    expect(t).toContain("1 pausaDuração: 2m 30s");
  });

  it("registro sem duração não inventa porcentagem", () => {
    const solto = serie([[1]]).map((l) => ({ ...l, epoca_segundos: null }));
    const t = texto(solto);
    expect(t).toContain("Sem registro suficiente para calcular o movimento");
    expect(t).not.toContain("%");
  });

  it("não dá nota nem interpreta", () => {
    expect(texto(serie([[100]], { movimentoACada: 10 })))
      .not.toMatch(/dormi|sono|qualidade|eficiência|agitad|tranquil|você se mexeu|nota|\bbom\b|\bruim\b/i);
  });
});

it("destaca o tempo registrado e distribui as frases em três cartões (UI-43)", () => {
  texto(serie([[4], [4, 150_000]], { movimentoACada: 4 }));
  const registrado = screen.getByRole("group", { name: "Registrado" });
  expect(registrado.textContent).toContain("4m 0s de 6m 30s · 17/11,");

  const metricas = within(screen.getByRole("list", { name: "Métricas da sessão" }));
  const cartoes = metricas.getAllByRole("listitem");
  expect(cartoes.map((cartao) => within(cartao).getByRole("strong").textContent)).toEqual(["25%", "1m 30s", "1 pausa"]);
  expect(metricas.queryByRole("heading")).toBeNull();
  expect(cartoes[0].textContent).toBe("25%Com movimento no tempo registrado");
  // UI-43: o valor fica só no destaque, e a frase embaixo não o repete.
  expect(cartoes[1].textContent).toBe("1m 30sMaior período sem movimento registrado");
  expect(cartoes[2].textContent).toBe("1 pausaDuração: 2m 30s");
});
