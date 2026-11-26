import { afterEach, describe, expect, it, vi } from "vitest";
import { prepararDispositivoDoCelular } from "./coleta";
import { Noite, noiteNativaDisponivel } from "./noiteNativa";

vi.mock("./noiteNativa", () => ({
  noiteNativaDisponivel: vi.fn(),
  Noite: { modeloDoAparelho: vi.fn() },
}));

afterEach(() => { vi.resetAllMocks(); vi.unstubAllGlobals(); });

describe("modelo do celular", () => {
  function capturar() {
    const visto: { body?: BodyInit | null } = {};
    vi.stubGlobal("fetch", (_url: string, init: RequestInit) => {
      visto.body = init.body;
      return Promise.resolve(new Response(JSON.stringify({ id: "d" }), { status: 200 }));
    });
    return visto;
  }
  it("manda modelo com versao", async () => {
    vi.mocked(noiteNativaDisponivel).mockReturnValue(true);
    vi.mocked(Noite.modeloDoAparelho).mockResolvedValue({ modelo: "Marca Modelo" });
    const visto = capturar();
    await prepararDispositivoDoCelular("1.1.4");
    expect(JSON.parse(String(visto.body))).toEqual({ versao_app: "1.1.4", modelo: "Marca Modelo" });
  });
  it("sem modelo preserva corpo", async () => {
    vi.mocked(noiteNativaDisponivel).mockReturnValue(true);
    vi.mocked(Noite.modeloDoAparelho).mockResolvedValue({});
    const visto = capturar();
    await prepararDispositivoDoCelular("1.1.4");
    expect(JSON.parse(String(visto.body))).toEqual({ versao_app: "1.1.4" });
  });
  it("ignora falha do plugin", async () => {
    vi.mocked(noiteNativaDisponivel).mockReturnValue(true);
    vi.mocked(Noite.modeloDoAparelho).mockRejectedValue(new Error("indisponivel"));
    const visto = capturar();
    await prepararDispositivoDoCelular("1.1.4");
    expect(JSON.parse(String(visto.body))).toEqual({ versao_app: "1.1.4" });
  });
});
