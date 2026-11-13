// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ListaDeNoites } from "./ListaDeNoites";
import type { NoiteGravada, NotasDaNoite, PluginNoite } from "../lib/noiteNativa";

afterEach(() => cleanup());

function plugin(noites: NoiteGravada[]) {
  const notas: Record<string, NotasDaNoite> = {};
  const p = {
    iniciar: vi.fn(),
    encerrar: vi.fn(),
    estado: vi.fn(),
    pedirIsencaoDeBateria: vi.fn(),
    lerEpocas: vi.fn(),
    marcarEnviadas: vi.fn(),
    noites: vi.fn(async () => ({ noites })),
    salvarNotas: vi.fn(async ({ arquivo, notas: n }: { arquivo: string; notas: NotasDaNoite }) => {
      notas[arquivo] = { ...(notas[arquivo] ?? {}), ...n };
      return notas[arquivo];
    }),
  } as unknown as PluginNoite & { salvarNotas: ReturnType<typeof vi.fn> };
  return p;
}

const NOITE_ANTIGA: NoiteGravada = {
  arquivo: "noite-1.jsonl",
  epocas: 960,
  enviadas: 960,
  primeiraTs: "2026-11-08T02:00:00.000Z",
  ultimaTs: "2026-11-08T09:59:30.000Z",
  notas: { posicao: "fronha" },
};
const NOITE_NOVA: NoiteGravada = {
  arquivo: "noite-2.jsonl",
  epocas: 100,
  enviadas: 40,
  primeiraTs: "2026-11-09T02:00:00.000Z",
  ultimaTs: "2026-11-09T02:59:30.000Z",
  notas: { posicao: "colchao", fim: "temperatura" },
};

function montar(p: PluginNoite) {
  return render(
    <MemoryRouter>
      <ListaDeNoites plugin={p} />
    </MemoryRouter>,
  );
}

describe("ListaDeNoites (APP-02, etapa 4)", () => {
  it("a mais recente primeiro, com posicao, envio e cobertura", async () => {
    montar(plugin([NOITE_ANTIGA, NOITE_NOVA]));
    const cartoes = await screen.findAllByTestId(/^noite-/);
    expect(cartoes.map((c) => c.getAttribute("data-testid"))).toEqual(["noite-noite-2.jsonl", "noite-noite-1.jsonl"]);
    expect(cartoes[0].textContent).toMatch(/Sobre o colchão/);
    expect(cartoes[0].textContent).toMatch(/40 de 100/);
    expect(cartoes[1].textContent).toMatch(/Dentro da fronha/);
    expect(cartoes[1].textContent).toMatch(/100 %/);
  });

  it("noite encerrada pelo calor diz isso", async () => {
    montar(plugin([NOITE_NOVA]));
    expect((await screen.findByRole("alert")).textContent).toMatch(/45 °C/);
  });

  it("as anotacoes do diario sao salvas na noite certa", async () => {
    const p = plugin([NOITE_ANTIGA, NOITE_NOVA]);
    montar(p);
    const botoes = await screen.findAllByRole("button", { name: /anotações da noite/i });
    // O segundo cartao e a noite antiga.
    fireEvent.click(botoes[1]);
    fireEvent.change(screen.getByLabelText(/deitei às/i), { target: { value: "23:10" } });
    fireEvent.change(screen.getByLabelText(/acordei às/i), { target: { value: "06:45" } });
    await act(async () => fireEvent.click(screen.getByRole("button", { name: /salvar anotações/i })));
    expect(p.salvarNotas).toHaveBeenCalledTimes(1);
    const arg = p.salvarNotas.mock.calls[0][0];
    expect(arg.arquivo).toBe("noite-1.jsonl");
    expect(arg.notas.deitou).toBe("23:10");
    expect(arg.notas.acordou).toBe("06:45");
    // A posicao e o fim nao saem do formulario: nao sao reescritos por engano.
    expect("posicao" in arg.notas).toBe(false);
    expect((await screen.findByRole("status")).textContent).toMatch(/salvas no aparelho/);
  });

  it("ver no painel so aparece com algo enviado", async () => {
    montar(plugin([{ ...NOITE_ANTIGA, enviadas: 0 }]));
    await screen.findByTestId("noite-noite-1.jsonl");
    expect(screen.queryByRole("link", { name: /ver no painel/i })).toBeNull();
  });

  it("mostra a falha do plugin e recupera a lista ao tentar novamente", async () => {
    const p = plugin([NOITE_ANTIGA]);
    vi.mocked(p.noites).mockRejectedValueOnce(new Error("falha de leitura"));
    montar(p);

    expect((await screen.findByRole("alert")).textContent).toMatch(/não foi possível carregar as noites gravadas/i);
    expect(screen.queryByText(/nenhuma noite gravada/i)).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(await screen.findByTestId("noite-noite-1.jsonl")).toBeTruthy();
    expect(screen.queryByRole("alert")).toBeNull();
    expect(p.noites).toHaveBeenCalledTimes(2);
  });

  it("sem noites, diz isso", async () => {
    montar(plugin([]));
    expect(await screen.findByText(/nenhuma noite gravada/i)).toBeTruthy();
  });

  it("a noite em andamento aparece marcada, sem envio nem anotacoes (achado no percurso)", async () => {
    montar(plugin([{ arquivo: "noite-3.jsonl", epocas: 3, enviadas: 0, ativa: true,
      primeiraTs: "2026-11-09T20:41:00.000Z", ultimaTs: "2026-11-09T20:42:00.000Z", notas: { posicao: "fronha" } }]));
    const cartao = await screen.findByTestId("noite-noite-3.jsonl");
    expect(cartao.textContent).toMatch(/Noite em andamento/);
    expect(cartao.textContent).not.toMatch(/Envio/);
    expect(screen.queryByRole("button", { name: /anotações da noite/i })).toBeNull();
  });

  it("noite sem epocas nao ganha o visto de enviada nem o nome do arquivo (achado no percurso)", async () => {
    montar(plugin([{ arquivo: "noite-4.jsonl", epocas: 0, enviadas: 0 }]));
    const cartao = await screen.findByTestId("noite-noite-4.jsonl");
    expect(cartao.textContent).toMatch(/Noite sem épocas gravadas/);
    expect(cartao.textContent).not.toMatch(/noite-4\.jsonl|0 de 0/);
  });
});
