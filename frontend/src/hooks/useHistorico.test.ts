// @vitest-environment jsdom
/** UI-24: promessas controladas exercitam o hook real, sem temporizadores de rede. */
import { createElement, StrictMode, type ReactNode } from "react";
import { act, cleanup, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { buscarHistorico, ErroApi } from "../lib/api";
import { useHistorico } from "./useHistorico";
import type { LeituraSono } from "../types/sleep";

vi.mock("../lib/api", async (original) => ({
  ...await original<typeof import("../lib/api")>(),
  buscarHistorico: vi.fn(),
}));

const buscar = vi.mocked(buscarHistorico);
const dados = (id: string): LeituraSono[] => [{
  device_id: id, created_at: "2026-11-04T00:00:00Z",
  movimento_total: 9.81, temp: null, status: "Repouso",
}];

function pendente() {
  let resolver!: (valor: LeituraSono[]) => void;
  let rejeitar!: (erro: Error) => void;
  const promessa = new Promise<LeituraSono[]>((resolve, reject) => {
    resolver = resolve;
    rejeitar = reject;
  });
  buscar.mockReturnValueOnce(promessa);
  return {
    sucesso: async (id: string) => {
      await act(async () => { resolver(dados(id)); await promessa; });
    },
    falha: async () => {
      await act(async () => {
        rejeitar(new ErroApi(503, "fonte indisponivel"));
        await promessa.catch(() => {});
      });
    },
  };
}

beforeEach(() => {
  buscar.mockReset();
  vi.stubEnv("DEV", true);
  window.history.replaceState(null, "", "/dashboard");
});
afterEach(() => {
  cleanup();
  vi.unstubAllEnvs();
  window.history.replaceState(null, "", "/");
});

describe("useHistorico: somente o carregamento vigente pode publicar estado", () => {
  it("publica os dados e encaminha todos os filtros", async () => {
    const pedido = pendente();
    const filtro = { dispositivo: "A", desde: "inicio", ate: "fim", limite: 100 };
    const { result } = renderHook(() => useHistorico(filtro));
    expect(result.current.carregando).toBe(true);
    expect(buscar).toHaveBeenCalledWith(filtro);
    await pedido.sucesso("A");
    expect(result.current).toMatchObject({ leituras: dados("A"), erro: null, carregando: false });
  });

  it("preserva a resposta nova quando a antiga termina depois", async () => {
    const antigo = pendente(), novo = pendente();
    const { result, rerender } = renderHook(({ dispositivo }) => useHistorico({ dispositivo }),
      { initialProps: { dispositivo: "A" } });
    rerender({ dispositivo: "B" });
    await novo.sucesso("B");
    await antigo.sucesso("A");
    expect(result.current).toMatchObject({ leituras: dados("B"), erro: null, carregando: false });
  });

  it("um erro antigo nao apaga a resposta nova", async () => {
    const antigo = pendente(), novo = pendente();
    const { result, rerender } = renderHook(({ dispositivo }) => useHistorico({ dispositivo }),
      { initialProps: { dispositivo: "A" } });
    rerender({ dispositivo: "B" });
    await novo.sucesso("B");
    await antigo.falha();
    expect(result.current).toMatchObject({ leituras: dados("B"), erro: null, carregando: false });
  });

  it("um sucesso antigo nao esconde o erro atual", async () => {
    const antigo = pendente(), novo = pendente();
    const { result, rerender } = renderHook(({ dispositivo }) => useHistorico({ dispositivo }),
      { initialProps: { dispositivo: "A" } });
    rerender({ dispositivo: "B" });
    await novo.falha();
    await antigo.sucesso("A");
    expect(result.current).toMatchObject({
      leituras: [], erro: "fonte indisponivel", carregando: false,
    });
  });

  it.each(["sucesso", "falha"] as const)(
    "o termino antigo (%s) nao encerra o carregamento novo", async (fim) => {
      const antigo = pendente(), novo = pendente();
      const { result, rerender } = renderHook(({ dispositivo }) => useHistorico({ dispositivo }),
        { initialProps: { dispositivo: "A" } });
      rerender({ dispositivo: "B" });
      if (fim === "sucesso") await antigo.sucesso("A");
      else await antigo.falha();
      expect(result.current).toMatchObject({ leituras: [], erro: null, carregando: true });
      await novo.sucesso("B");
      expect(result.current.leituras).toEqual(dados("B"));
    });

  it("recargas manuais tambem invalidam o pedido anterior", async () => {
    const antigo = pendente(), novo = pendente();
    const { result } = renderHook(() => useHistorico());
    act(() => result.current.recarregar());
    await novo.sucesso("novo");
    await antigo.sucesso("antigo");
    expect(result.current.leituras).toEqual(dados("novo"));
  });

  it("mudanca de janela invalida o pedido mesmo no mesmo dispositivo", async () => {
    const antigo = pendente(), novo = pendente();
    const { result, rerender } = renderHook(({ desde }) => useHistorico({ dispositivo: "A", desde }),
      { initialProps: { desde: "ontem" } });
    rerender({ desde: "hoje" });
    await novo.sucesso("hoje");
    await antigo.sucesso("ontem");
    expect(result.current.leituras).toEqual(dados("hoje"));
  });

  it("callback retido depois da desmontagem nao inicia nova busca", async () => {
    const pedido = pendente();
    const { result, unmount } = renderHook(() => useHistorico());
    const recarregar = result.current.recarregar;
    unmount();
    await pedido.sucesso("A");
    act(() => recarregar());
    expect(buscar).toHaveBeenCalledTimes(1);
  });

  it("Strict Mode invalida o primeiro efeito sem desativar o segundo", async () => {
    const primeiro = pendente(), segundo = pendente();
    const wrapper = ({ children }: { children: ReactNode }) => createElement(StrictMode, null, children);
    const { result } = renderHook(() => useHistorico(), { wrapper });
    expect(buscar).toHaveBeenCalledTimes(2);
    await segundo.sucesso("vigente");
    await primeiro.sucesso("descartado");
    expect(result.current).toMatchObject({ leituras: dados("vigente"), carregando: false, erro: null });
  });

  it("demo continua local e termina o carregamento", () => {
    window.history.replaceState(null, "", "/dashboard?demo=1");
    const { result } = renderHook(() => useHistorico());
    expect(buscar).not.toHaveBeenCalled();
    expect(result.current.leituras.length).toBeGreaterThan(0);
    expect(result.current).toMatchObject({ carregando: false, erro: null });
  });
});
