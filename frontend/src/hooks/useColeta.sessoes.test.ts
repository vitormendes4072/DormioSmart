// @vitest-environment jsdom
import { act, renderHook } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { useColeta } from "./useColeta";

const { enviar } = vi.hoisted(() => ({ enviar: vi.fn() }));
vi.mock("../contexts/AuthContext", () => ({ useAuth: () => ({ sessao: null }) }));
vi.mock("../lib/coleta", () => ({
  enviarLeitura: enviar,
  ErroDeIngestao: class extends Error {},
}));

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  enviar.mockReset();
});

it("zera os registros ao iniciar outra sessão, inclusive com um envio anterior pendente", async () => {
  vi.useFakeTimers();
  vi.stubGlobal("DeviceMotionEvent", class {});
  let concluir!: () => void;
  enviar.mockImplementationOnce(() => new Promise<void>((resolve) => { concluir = resolve; }));
  const { result } = renderHook(() => useColeta(30, "dispositivo-teste"));

  await act(async () => result.current.comecar());
  act(() => {
    window.dispatchEvent(Object.assign(new Event("devicemotion"), {
      accelerationIncludingGravity: { x: 0, y: 0, z: 9.81 },
    }));
    vi.advanceTimersByTime(30_000);
  });
  expect(result.current.registros).toHaveLength(1);
  expect(result.current.registros[0].envio).toBe("enviando");

  act(() => result.current.parar());
  expect(result.current.registros).toHaveLength(1);
  await act(async () => result.current.comecar());
  expect(result.current.registros).toHaveLength(0);
  expect(result.current.decorridoMs).toBe(0);

  await act(async () => concluir());
  expect(result.current.registros).toHaveLength(0);
  expect(enviar).toHaveBeenCalledTimes(1);
});

it("avisa sobre a primeira janela, o encerramento sem registros e o reinício", async () => {
  vi.useFakeTimers();
  vi.stubGlobal("DeviceMotionEvent", class {});
  enviar.mockResolvedValue(undefined);
  const { result } = renderHook(() => useColeta(30, "dispositivo-teste"));

  await act(async () => result.current.comecar());
  expect(result.current.segundosAtePrimeiroRegistro).toBe(30);
  act(() => result.current.parar());
  expect(result.current.encerradaSemRegistros).toBe(true);
  expect(result.current.segundosAtePrimeiroRegistro).toBeNull();
  expect(enviar).not.toHaveBeenCalled();

  await act(async () => result.current.comecar());
  expect(result.current.encerradaSemRegistros).toBe(false);
  expect(result.current.segundosAtePrimeiroRegistro).toBe(30);
  act(() => {
    window.dispatchEvent(Object.assign(new Event("devicemotion"), {
      accelerationIncludingGravity: { x: 0, y: 0, z: 9.81 },
    }));
    vi.advanceTimersByTime(29_000);
  });
  expect(result.current.segundosAtePrimeiroRegistro).toBe(1);
  await act(async () => vi.advanceTimersByTime(1000));
  expect(result.current.registros).toHaveLength(1);
  expect(result.current.segundosAtePrimeiroRegistro).toBeNull();

  act(() => result.current.parar());
  expect(result.current.encerradaSemRegistros).toBe(false);
});
