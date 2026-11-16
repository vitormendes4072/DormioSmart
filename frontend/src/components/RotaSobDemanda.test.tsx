// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { carregarModulo } from "./RotaSobDemanda";

const chave = "teste:recarga";
const falhar = async () => { throw new Error("chunk ausente"); };

afterEach(() => {
  cleanup();
  sessionStorage.clear();
});

it("marca a primeira falha e recarrega a página uma vez", async () => {
  const recarregar = vi.fn();
  await carregarModulo(falhar, chave, sessionStorage, recarregar);
  expect(sessionStorage.getItem(chave)).toBe("1");
  expect(recarregar).toHaveBeenCalledOnce();
});

it("oferece Recarregar na segunda falha sem recarregar sozinha", async () => {
  const recarregar = vi.fn();
  sessionStorage.setItem(chave, "1");
  const { default: Falha } = await carregarModulo(falhar, chave, sessionStorage, recarregar);
  render(<Falha />);
  expect(recarregar).not.toHaveBeenCalled();
  expect(screen.getByRole("alert")).toBeTruthy();
  expect(screen.getByRole("button", { name: "Recarregar" })).toBeTruthy();
});

it("entrega o módulo sem recarregar e libera uma tentativa futura", async () => {
  const recarregar = vi.fn();
  const modulo = { default: () => null };
  sessionStorage.setItem(chave, "1");
  expect(await carregarModulo(async () => modulo, chave, sessionStorage, recarregar)).toBe(modulo);
  expect(recarregar).not.toHaveBeenCalled();
  expect(sessionStorage.getItem(chave)).toBeNull();
});
