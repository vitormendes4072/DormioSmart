// @vitest-environment jsdom
/**
 * DEMO-03: em modo demonstração, a lista de dispositivos não vai à API.
 *
 * O `useHistorico` gera a noite no cliente quando `?demo=1`; o `useDispositivos`
 * pedia `/api/devices` mesmo assim, e o servidor de desenvolvimento sem backend
 * respondia 500 no console. O painel não quebrava (a lista falha em silêncio),
 * por isso nada acusava.
 */
import { cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const listarDispositivos = vi.fn();
vi.mock("../lib/dispositivos", () => ({
  listarDispositivos: () => listarDispositivos(),
}));

import { useDispositivos } from "./useDispositivos";

afterEach(() => {
  cleanup();
  listarDispositivos.mockReset();
  vi.unstubAllEnvs();
  window.history.replaceState(null, "", "/");
});

describe("useDispositivos e o modo demonstração (DEMO-03)", () => {
  it("em demonstração, não chama a API e devolve a lista vazia", async () => {
    vi.stubEnv("DEV", true);
    window.history.replaceState(null, "", "/dashboard?demo=1");
    const { result } = renderHook(() => useDispositivos());
    await new Promise((r) => setTimeout(r, 0));
    expect(listarDispositivos).not.toHaveBeenCalled();
    expect(result.current).toEqual([]);
  });

  it("fora da demonstração, busca a lista e a devolve", async () => {
    vi.stubEnv("DEV", true);
    listarDispositivos.mockResolvedValue([{ id: "d1", nome: "Travesseiro" }]);
    const { result } = renderHook(() => useDispositivos());
    await waitFor(() => expect(result.current).toHaveLength(1));
    expect(listarDispositivos).toHaveBeenCalledTimes(1);
  });

  it("no build de produção, ?demo=1 não desliga a busca", async () => {
    vi.stubEnv("DEV", false);
    window.history.replaceState(null, "", "/dashboard?demo=1");
    listarDispositivos.mockResolvedValue([]);
    renderHook(() => useDispositivos());
    await waitFor(() => expect(listarDispositivos).toHaveBeenCalledTimes(1));
  });
});
