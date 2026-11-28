// @vitest-environment jsdom
import { act, cleanup, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { listarDispositivos, type Dispositivo } from "../lib/dispositivos";
import { usePrimeiroSinal } from "./usePrimeiroSinal";

vi.mock("../lib/dispositivos", async (original) => ({
  ...await original<typeof import("../lib/dispositivos")>(),
  listarDispositivos: vi.fn(),
}));

const travesseiro: Dispositivo = { id: "p", nome: "Travesseiro", tipo: "travesseiro", revoked_at: null, last_seen_at: null, created_at: "" };
const listar = vi.mocked(listarDispositivos);

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.restoreAllMocks();
  listar.mockReset();
});

describe("espera do primeiro sinal (UI-62)", () => {
  it("cancela a consulta em andamento e não continua consultando ao sair da rota", async () => {
    vi.useFakeTimers();
    listar.mockResolvedValueOnce([travesseiro]).mockImplementation(() => new Promise(() => {}));
    const { unmount } = renderHook(() => usePrimeiroSinal(travesseiro.id));
    await act(() => vi.advanceTimersByTimeAsync(5_000));
    expect(listar).toHaveBeenCalledTimes(2);
    const pendente = listar.mock.calls[1][0];
    expect(pendente?.aborted).toBe(false);
    unmount();
    expect(pendente?.aborted).toBe(true);
    await act(() => vi.advanceTimersByTimeAsync(20_000));
    expect(listar).toHaveBeenCalledTimes(2);
  });

  it("pausa em tela oculta e consulta imediatamente ao voltar", async () => {
    vi.useFakeTimers();
    const oculto = vi.spyOn(document, "hidden", "get").mockReturnValue(false);
    listar.mockResolvedValue([travesseiro]);
    const { result } = renderHook(() => usePrimeiroSinal(travesseiro.id));
    await act(() => vi.advanceTimersByTimeAsync(0));
    expect(listar).toHaveBeenCalledTimes(1);
    expect(result.current.pausado).toBe(false);
    oculto.mockReturnValue(true);
    act(() => { document.dispatchEvent(new Event("visibilitychange")); });
    await act(() => vi.advanceTimersByTimeAsync(20_000));
    expect(listar).toHaveBeenCalledTimes(1);
    expect(result.current.pausado).toBe(true);
    oculto.mockReturnValue(false);
    act(() => { document.dispatchEvent(new Event("visibilitychange")); });
    expect(listar).toHaveBeenCalledTimes(2);
    await act(() => vi.advanceTimersByTimeAsync(0));
    expect(result.current.pausado).toBe(false);
  });

  it("trata um pedido que fica sem resposta e volta a consultar", async () => {
    vi.useFakeTimers();
    listar.mockImplementationOnce(() => new Promise(() => {})).mockResolvedValue([travesseiro]);
    const { result } = renderHook(() => usePrimeiroSinal(travesseiro.id));
    await act(() => vi.advanceTimersByTimeAsync(10_000));
    expect(listar.mock.calls[0][0]?.aborted).toBe(true);
    expect(result.current.resultado).toBe("erro");
    await act(() => vi.advanceTimersByTimeAsync(5_000));
    expect(listar).toHaveBeenCalledTimes(2);
    expect(result.current.resultado).toBe("aguardando");
  });
});
