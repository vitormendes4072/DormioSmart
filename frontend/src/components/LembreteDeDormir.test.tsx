// @vitest-environment jsdom
// APP-20: o lembrete de dormir em Configurações.
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { EstadoDoLembrete } from "../lib/noiteNativa";
import { LembreteDeDormir, horarioComoTexto, lerHorario } from "./LembreteDeDormir";

afterEach(cleanup);

function plugin(inicial: EstadoDoLembrete, notificar = inicial.notificacoes) {
  let atual = inicial;
  return {
    lembrete: vi.fn(() => Promise.resolve(atual)),
    definirLembrete: vi.fn((o: { ativo: boolean; hora: number; minuto: number }) => {
      atual = { ...o, notificacoes: notificar };
      return Promise.resolve(atual);
    }),
  };
}

async function montar(p: ReturnType<typeof plugin>) {
  render(<LembreteDeDormir plugin={p} />);
  await act(async () => {});
}

const DESLIGADO: EstadoDoLembrete = { ativo: false, hora: 22, minuto: 30, notificacoes: true };

describe("o horário", () => {
  it("vai e volta entre texto e números", () => {
    expect(horarioComoTexto(7, 5)).toBe("07:05");
    expect(lerHorario("22:30")).toEqual({ hora: 22, minuto: 30 });
    expect(lerHorario("00:00")).toEqual({ hora: 0, minuto: 0 });
  });

  it("recusa o que não é horário", () => {
    for (const t of ["24:00", "22:60", "7:05", "", "22h30"]) expect(lerHorario(t)).toBeNull();
  });
});

describe("a seção do lembrete (APP-20)", () => {
  it("começa como está guardado no celular: desligado, 22:30", async () => {
    await montar(plugin(DESLIGADO));
    expect((screen.getByRole("checkbox", { name: "Lembrar todo dia" }) as HTMLInputElement).checked).toBe(false);
    expect((screen.getByLabelText("Horário") as HTMLInputElement).value).toBe("22:30");
  });

  it("ligar grava no celular e confirma o horário", async () => {
    const p = plugin(DESLIGADO);
    await montar(p);
    await act(async () => {
      fireEvent.click(screen.getByRole("checkbox", { name: "Lembrar todo dia" }));
    });
    expect(p.definirLembrete).toHaveBeenCalledWith({ ativo: true, hora: 22, minuto: 30 });
    expect(screen.getByText("Você vai receber o lembrete todo dia às 22:30.")).toBeTruthy();
  });

  it("mudar o horário grava o novo, mantendo ligado", async () => {
    const p = plugin({ ...DESLIGADO, ativo: true });
    await montar(p);
    await act(async () => {
      fireEvent.change(screen.getByLabelText("Horário"), { target: { value: "23:15" } });
    });
    expect(p.definirLembrete).toHaveBeenCalledWith({ ativo: true, hora: 23, minuto: 15 });
  });

  it("ligado sem permissão de notificar, diz como ativar", async () => {
    const p = plugin(DESLIGADO, false);
    await montar(p);
    await act(async () => {
      fireEvent.click(screen.getByRole("checkbox", { name: "Lembrar todo dia" }));
    });
    expect(screen.getByRole("alert").textContent).toContain("ative-as nas configurações do Android");
    expect(screen.queryByText(/Você vai receber/)).toBeNull();
  });

  it("falha ao gravar avisa e não finge que ligou", async () => {
    const p = plugin(DESLIGADO);
    p.definirLembrete.mockImplementationOnce(() => Promise.reject(new Error("x")));
    await montar(p);
    await act(async () => {
      fireEvent.click(screen.getByRole("checkbox", { name: "Lembrar todo dia" }));
    });
    expect(screen.getByText(/Não foi possível salvar o lembrete/)).toBeTruthy();
    expect((screen.getByRole("checkbox", { name: "Lembrar todo dia" }) as HTMLInputElement).checked).toBe(false);
  });

  it("só aparece em Configurações no app", () => {
    const tela = readFileSync(resolve("src/pages/Settings.tsx"), "utf8");
    expect(tela).toContain("{noiteNativaDisponivel() ? <SecaoLembrete /> : null}");
  });
});
