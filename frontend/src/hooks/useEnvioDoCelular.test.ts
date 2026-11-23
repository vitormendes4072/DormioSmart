// @vitest-environment jsdom
// APP-19: a Noite do app informa a versão instalada ao preparar o dispositivo.
import { act, renderHook } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it, vi } from "vitest";

const preparar = vi.fn(() => Promise.resolve({ id: "dev-celular" }));
vi.mock("../lib/coleta", () => ({
  prepararDispositivoDoCelular: (...args: unknown[]) => preparar(...(args as [])),
  enviarLote: vi.fn(),
}));
vi.mock("../contexts/AuthContext", () => ({ useAuth: () => ({ sessao: { access_token: "jwt" } }) }));

import { VERSAO_DO_APP_ANDROID } from "../lib/appAndroid";
import { useEnvioDoCelular } from "./useEnvioDoCelular";

describe("o envio do app (APP-19)", () => {
  it("prepara o dispositivo informando a versão do app", async () => {
    renderHook(() => useEnvioDoCelular(true));
    await act(async () => {});
    expect(preparar).toHaveBeenCalledWith(VERSAO_DO_APP_ANDROID);
  });

  it("o aviso de versão nova está na casca das telas depois do login", () => {
    const layout = readFileSync(resolve("src/components/Layout.tsx"), "utf8");
    expect(layout).toMatch(/<AvisoDeAtualizacao \/>\s*<Outlet \/>/);
  });
});
