// @vitest-environment jsdom
// APP-19: a faixa da versão nova aparece só no app, só com versão mais nova, e some ao dispensar.
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { URL_DO_APK } from "../lib/appAndroid";
import { AvisoDeAtualizacao } from "./AvisoDeAtualizacao";

afterEach(cleanup);

async function montar(props: Parameters<typeof AvisoDeAtualizacao>[0]) {
  const r = render(<AvisoDeAtualizacao {...props} />);
  await act(async () => {});
  return r;
}

describe("o aviso de versão nova (APP-19)", () => {
  it("no app, com versão mais nova publicada, mostra a versão e o download", async () => {
    await montar({ noApp: true, instalada: "1.1.3", buscar: () => Promise.resolve("1.1.4") });
    expect(screen.getByRole("status").textContent).toContain("1.1.4");
    expect(screen.getByRole("status").textContent).toContain("1.1.3");
    const link = screen.getByRole("link", { name: "Baixar a versão nova" });
    expect(link.getAttribute("href")).toBe(URL_DO_APK);
    expect(link.getAttribute("target")).toBe("_blank");
  });

  it("com a versão instalada já em dia, não mostra nada", async () => {
    const { container } = await montar({ noApp: true, instalada: "1.1.4", buscar: () => Promise.resolve("1.1.4") });
    expect(container.textContent).toBe("");
  });

  it("sem resposta (sem internet), não mostra nada", async () => {
    const { container } = await montar({ noApp: true, instalada: "1.1.3", buscar: () => Promise.resolve(null) });
    expect(container.textContent).toBe("");
  });

  it("no site, nem pergunta", async () => {
    const buscar = vi.fn(() => Promise.resolve("9.9.9"));
    const { container } = await montar({ noApp: false, instalada: "1.1.3", buscar });
    expect(buscar).not.toHaveBeenCalled();
    expect(container.textContent).toBe("");
  });

  it("'Agora não' esconde a faixa", async () => {
    await montar({ noApp: true, instalada: "1.1.3", buscar: () => Promise.resolve("1.1.4") });
    fireEvent.click(screen.getByRole("button", { name: "Agora não" }));
    expect(screen.queryByRole("status")).toBeNull();
  });
});
