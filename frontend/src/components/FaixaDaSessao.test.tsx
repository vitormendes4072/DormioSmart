// @vitest-environment jsdom
/**
 * UI-53: a faixa de cada sessão no Histórico, a régua de horário comum e o menu "…".
 */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { marcasDaRegua, posicaoNaRegua, reguaDoHorario } from "../lib/faixaDaSessao";
import { FaixaDaSessao } from "./FaixaDaSessao";
import { MenuDaSessao } from "./MenuDaSessao";

afterEach(cleanup);

const H = 3_600_000;
const em = (dia: number, hora: number, minuto = 0) => new Date(2026, 10, dia, hora, minuto).getTime();

describe("a régua de horário", () => {
  it("vai da hora cheia antes do início mais cedo à hora cheia depois do fim mais tarde, sem partir na meia-noite", () => {
    const regua = reguaDoHorario([
      { inicio: em(20, 23, 10), fim: em(21, 6, 40) },
      { inicio: em(21, 22, 30), fim: em(22, 5, 0) },
    ]);
    // Do meio-dia: 22h é 10 h depois, 7h do dia seguinte é 19 h depois.
    expect(regua).toEqual({ deMs: 10 * H, ateMs: 19 * H });
    expect(marcasDaRegua(regua).map((m) => m.rotulo)).toEqual(["22h", "0h", "2h", "4h", "6h"]);
  });

  it("a mesma hora em dias diferentes cai no mesmo ponto", () => {
    const regua = reguaDoHorario([{ inicio: em(20, 23), fim: em(21, 7) }, { inicio: em(25, 23), fim: em(26, 7) }]);
    expect(posicaoNaRegua(regua, em(20, 23), em(21, 3))).toBeCloseTo(posicaoNaRegua(regua, em(25, 23), em(26, 3)), 9);
    expect(posicaoNaRegua(regua, em(20, 23), em(21, 3))).toBeCloseTo(0.5, 9);
  });

  it("uma sessão de tarde usa a régua da tarde", () => {
    expect(reguaDoHorario([{ inicio: em(26, 13, 35), fim: em(26, 21, 15) }])).toEqual({ deMs: 1 * H, ateMs: 10 * H });
  });

  it("não passa de 24 horas, e o que sobra fica preso na borda", () => {
    const regua = reguaDoHorario([{ inicio: em(20, 14), fim: em(22, 14) }]);
    expect(regua.ateMs - regua.deMs).toBe(24 * H);
    expect(posicaoNaRegua(regua, em(20, 14), em(22, 0))).toBe(1);
  });
});

describe("FaixaDaSessao", () => {
  it("desenha o período, os trechos com registro e um traço por registro com movimento, e diz tudo por escrito", () => {
    const regua = { deMs: 10 * H, ateMs: 20 * H };
    const { container } = render(
      <FaixaDaSessao regua={regua} inicio={em(20, 22)} fim={em(21, 6)} tempo={7 * H}
        trechos={[{ inicio: em(20, 22), fim: em(21, 1) }, { inicio: em(21, 2), fim: em(21, 6) }]}
        movimentos={[em(20, 23), em(21, 4)]} />,
    );
    const periodo = container.querySelector("[data-periodo]")!;
    expect(Number(periodo.getAttribute("x"))).toBeCloseTo(0, 6);
    expect(Number(periodo.getAttribute("width"))).toBeCloseTo(80, 6);
    expect(container.querySelectorAll("[data-registro]")).toHaveLength(2);
    expect(Number(container.querySelectorAll("[data-registro]")[1].getAttribute("x"))).toBeCloseTo(40, 6);
    expect(container.querySelectorAll("[data-movimento]")).toHaveLength(2);
    expect(screen.getByRole("img").getAttribute("aria-label"))
      .toBe("Das 22:00 às 06:00: 7h 0m com registro, 2 registros com movimento.");
  });
});

describe("MenuDaSessao", () => {
  function montar(aoMarcar = vi.fn()) {
    render(
      <MenuDaSessao rotulo="Ações da sessão de 26 nov 2026">
        <button type="button" onClick={aoMarcar}>Marcar como bancada</button>
        <button type="button">Excluir…</button>
      </MenuDaSessao>,
    );
    return screen.getByRole("button", { name: "Ações da sessão de 26 nov 2026" });
  }

  it("as ações só aparecem depois do toque no …, e o foco vai para a primeira", () => {
    const gatilho = montar();
    expect(screen.queryByRole("button", { name: "Excluir…" })).toBeNull();
    expect(gatilho.getAttribute("aria-expanded")).toBe("false");
    fireEvent.click(gatilho);
    expect(gatilho.getAttribute("aria-expanded")).toBe("true");
    expect(document.activeElement).toBe(screen.getByRole("button", { name: "Marcar como bancada" }));
  });

  it("escolher uma ação a executa e fecha o painel", () => {
    const aoMarcar = vi.fn();
    fireEvent.click(montar(aoMarcar));
    fireEvent.click(screen.getByRole("button", { name: "Marcar como bancada" }));
    expect(aoMarcar).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("button", { name: "Excluir…" })).toBeNull();
  });

  it("Esc fecha e devolve o foco ao …; tocar fora também fecha", () => {
    const gatilho = montar();
    fireEvent.click(gatilho);
    fireEvent.keyDown(screen.getByRole("button", { name: "Excluir…" }), { key: "Escape" });
    expect(screen.queryByRole("button", { name: "Excluir…" })).toBeNull();
    expect(document.activeElement).toBe(gatilho);
    fireEvent.click(gatilho);
    fireEvent.pointerDown(document.body);
    expect(screen.queryByRole("button", { name: "Excluir…" })).toBeNull();
  });
});
