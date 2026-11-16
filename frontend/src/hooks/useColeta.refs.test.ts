// @vitest-environment jsdom
import { act, renderHook } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { useColeta } from "./useColeta";

const { enviar, sessao } = vi.hoisted(() => ({
  enviar: vi.fn(),
  sessao: { atual: null as { access_token: string } | null },
}));
vi.mock("../contexts/AuthContext", () => ({ useAuth: () => ({ sessao: sessao.atual }) }));
vi.mock("../lib/coleta", () => ({
  enviarLeitura: enviar,
  ErroDeIngestao: class extends Error {},
}));

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  enviar.mockReset();
  sessao.atual = null;
});

function mover() {
  window.dispatchEvent(Object.assign(new Event("devicemotion"), {
    accelerationIncludingGravity: { x: 0, y: 0, z: 9.81 },
  }));
}

// UI-33: os refs passaram a ser atualizados depois da renderização aplicada.
// A época tem de usar o aparelho e o JWT da renderização mais recente, não os
// da primeira.
it("a época usa o aparelho e o JWT da renderização mais recente", async () => {
  vi.useFakeTimers();
  vi.stubGlobal("DeviceMotionEvent", class {});
  enviar.mockResolvedValue(undefined);
  sessao.atual = { access_token: "jwt-antigo" };
  const { result, rerender } = renderHook(
    ({ id }: { id: string }) => useColeta(30, id),
    { initialProps: { id: "aparelho-antigo" } },
  );

  await act(async () => result.current.comecar());
  sessao.atual = { access_token: "jwt-novo" };
  rerender({ id: "aparelho-novo" });

  act(() => mover());
  await act(async () => vi.advanceTimersByTime(30_000));

  expect(enviar).toHaveBeenCalledTimes(1);
  expect(enviar.mock.calls[0][1]).toBe("aparelho-novo");
  expect(enviar.mock.calls[0][2]).toBe("jwt-novo");
});
