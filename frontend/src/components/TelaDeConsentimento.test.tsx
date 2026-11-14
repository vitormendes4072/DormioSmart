// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CartaoDaNoite } from "./CartaoDaNoite";
import { TelaDeConsentimento } from "./TelaDeConsentimento";
import { TEXTO_DO_CONSENTIMENTO, consentimentoVigente, VERSAO_DO_CONSENTIMENTO } from "../lib/consentimento";
import type { EstadoDaNoite, PluginNoite } from "../lib/noiteNativa";

afterEach(cleanup);

/**
 * LGPD-12: a tela do consentimento específico e destacado, e o portão que a abre antes da primeira
 * noite. O que se trava: sem marcar a caixa não há "Concordo"; "Agora não" não mede nada; o
 * "Concordo" registra ANTES de iniciar; e quem já consentiu na versão vigente não vê a tela.
 */

describe("TelaDeConsentimento (LGPD-12)", () => {
  const abrir = (props: Partial<Parameters<typeof TelaDeConsentimento>[0]> = {}) =>
    render(
      <MemoryRouter>
        <TelaDeConsentimento aoConcordar={vi.fn(async () => {})} aoRecusar={vi.fn()} {...props} />
      </MemoryRouter>,
    );

  it("é um diálogo com o texto inteiro e o link da política", () => {
    abrir();
    expect(screen.getByRole("dialog")).toBeTruthy();
    for (const item of TEXTO_DO_CONSENTIMENTO) expect(screen.getByText(item)).toBeTruthy();
    expect(screen.getByRole("link", { name: /política de privacidade/i }).getAttribute("href")).toBe("/privacidade");
  });

  it("contém Tab e devolve o foco ao fechar com Escape", async () => {
    const usuario = userEvent.setup();
    const aoConcordar = vi.fn(async () => {});
    function Tela() {
      const [aberta, setAberta] = useState(false);
      return (
        <>
          <button onClick={() => setAberta(true)}>Abrir consentimento</button>
          {aberta && <TelaDeConsentimento aoConcordar={aoConcordar} aoRecusar={() => setAberta(false)} />}
          <button>Fora do diálogo</button>
        </>
      );
    }
    render(<MemoryRouter><Tela /></MemoryRouter>);
    const origem = screen.getByRole("button", { name: "Abrir consentimento" });
    await usuario.tab();
    expect(document.activeElement).toBe(origem);
    await usuario.keyboard("{Enter}");
    expect(document.activeElement).toBe(screen.getByRole("heading"));

    const politica = screen.getByRole("link", { name: /política de privacidade/i });
    const recusar = screen.getByRole("button", { name: "Agora não" });
    await usuario.tab();
    expect(document.activeElement).toBe(politica);
    await usuario.tab({ shift: true });
    expect(document.activeElement).toBe(recusar);
    await usuario.tab();
    expect(document.activeElement).toBe(politica);

    await usuario.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(document.activeElement).toBe(origem);
    expect(aoConcordar).not.toHaveBeenCalled();
  });

  it("o Concordo só liga depois de marcar a caixa", async () => {
    const aoConcordar = vi.fn(async () => {});
    abrir({ aoConcordar });
    const concordo = screen.getByRole("button", { name: /concordo/i }) as HTMLButtonElement;
    expect(concordo.disabled).toBe(true);
    fireEvent.click(concordo);
    expect(aoConcordar).not.toHaveBeenCalled();
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("checkbox", { name: /li e concordo/i }));
    expect(concordo.disabled).toBe(false);
    await act(async () => fireEvent.click(concordo));
    expect(aoConcordar).toHaveBeenCalledTimes(1);
  });

  it("Agora não fecha sem concordar", () => {
    const aoRecusar = vi.fn();
    const aoConcordar = vi.fn(async () => {});
    abrir({ aoRecusar, aoConcordar });
    fireEvent.click(screen.getByRole("button", { name: /agora não/i }));
    expect(aoRecusar).toHaveBeenCalledTimes(1);
    expect(aoConcordar).not.toHaveBeenCalled();
  });

  it("mostra o erro do registro", () => {
    abrir({ erro: "Não foi possível registrar o consentimento. Tente de novo." });
    expect(screen.getByRole("alert").textContent).toMatch(/não foi possível registrar/i);
  });
});

describe("a versão vigente (LGPD-12)", () => {
  it("só a versão desta tela conta", () => {
    expect(consentimentoVigente({ nome: null, idade: null, consentimento_saude_versao: VERSAO_DO_CONSENTIMENTO })).toBe(true);
    expect(consentimentoVigente({ nome: null, idade: null, consentimento_saude_versao: "2000-01-01" })).toBe(false);
    expect(consentimentoVigente({ nome: null, idade: null })).toBe(false);
    expect(consentimentoVigente(null)).toBe(false);
  });
});

// --- o portão na noite -------------------------------------------------------

const INICIO = 1_794_096_000_000;

function plugin(): PluginNoite & { atual: EstadoDaNoite } {
  const p = {
    atual: {
      ativa: false, rodando: false, inicioUtcMs: 0, epocasGravadas: 0, recusadas: 0,
      recusadasPorTaxa: 0, semFeatures: 0, amostras: 0, taxaHz: 0, retomadas: 0,
      ultimaEpocaUtcMs: 0, isentoDeBateria: true,
    } as EstadoDaNoite,
    noites: vi.fn(async () => ({ noites: [] })),
    lerEpocas: vi.fn(async () => ({ epocas: [] })),
    marcarEnviadas: vi.fn(async () => ({ enviadas: 0 })),
    iniciar: vi.fn(async () => {
      p.atual = { ...p.atual, ativa: true, rodando: true, inicioUtcMs: INICIO };
      return { notificacoes: true };
    }),
    apagarTeste: vi.fn(async () => {}),
    compartilharTeste: vi.fn(async () => {}),
    encerrar: vi.fn(async () => {}),
    estado: vi.fn(async () => p.atual),
    pedirIsencaoDeBateria: vi.fn(async () => ({ isentoDeBateria: true })),
    salvarNotas: vi.fn(async ({ notas }: { arquivo: string; notas: object }) => notas),
  };
  return p;
}

async function tocarIniciar(p: PluginNoite, consentimento: { vigente: boolean; registrar: () => Promise<void> }, teste = false) {
  render(
    <MemoryRouter>
      <CartaoDaNoite plugin={p} agora={() => INICIO} consentimento={consentimento} />
    </MemoryRouter>,
  );
  const iniciar = await screen.findByRole("button", { name: /iniciar a noite/i });
  fireEvent.click(screen.getByLabelText(/sobre o colchão/i));
  await waitFor(() => expect((iniciar as HTMLButtonElement).disabled).toBe(false));
  if (teste) fireEvent.click(screen.getByRole("checkbox", { name: /gravação de teste/i }));
  await act(async () => fireEvent.click(iniciar));
}

describe("o portão do consentimento na noite (LGPD-12)", () => {
  it("sem consentimento, Iniciar abre a tela e não inicia", async () => {
    const p = plugin();
    await tocarIniciar(p, { vigente: false, registrar: vi.fn(async () => {}) });
    expect(screen.getByRole("dialog")).toBeTruthy();
    expect(p.iniciar).not.toHaveBeenCalled();
  });

  it("marcar Gravação de teste não libera o início sem consentimento", async () => {
    const p = plugin();
    const registrar = vi.fn(async () => {});
    await tocarIniciar(p, { vigente: false, registrar }, true);
    const dialogo = within(screen.getByRole("dialog"));
    expect((screen.getByRole("checkbox", { name: /gravação de teste/i }) as HTMLInputElement).checked).toBe(true);
    expect((dialogo.getByRole("checkbox", { name: /li e concordo/i }) as HTMLInputElement).checked).toBe(false);
    const concordo = dialogo.getByRole("button", { name: /concordo/i }) as HTMLButtonElement;
    expect(concordo.disabled).toBe(true);
    await act(async () => fireEvent.click(concordo));
    expect(registrar).not.toHaveBeenCalled();
    expect(p.iniciar).not.toHaveBeenCalled();
  });

  it("Agora não fecha a tela e a noite não começa", async () => {
    const p = plugin();
    const registrar = vi.fn(async () => {});
    await tocarIniciar(p, { vigente: false, registrar });
    fireEvent.click(screen.getByRole("button", { name: /agora não/i }));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(registrar).not.toHaveBeenCalled();
    expect(p.iniciar).not.toHaveBeenCalled();
  });

  it("Concordo registra primeiro e só então inicia a noite", async () => {
    const p = plugin();
    const ordem: string[] = [];
    const registrar = vi.fn(async () => {
      ordem.push("registrar");
    });
    (p.iniciar as ReturnType<typeof vi.fn>).mockImplementation(async () => {
      ordem.push("iniciar");
      return { notificacoes: true };
    });
    await tocarIniciar(p, { vigente: false, registrar });
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("checkbox", { name: /li e concordo/i }));
    await act(async () => fireEvent.click(screen.getByRole("button", { name: /concordo/i })));
    expect(ordem).toEqual(["registrar", "iniciar"]);
    expect(p.iniciar).toHaveBeenCalledWith({ posicao: "colchao" });
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("se o registro falha, a noite não começa e a tela diz por quê", async () => {
    const p = plugin();
    await tocarIniciar(p, { vigente: false, registrar: vi.fn(async () => { throw new Error("rede"); }) });
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("checkbox", { name: /li e concordo/i }));
    await act(async () => fireEvent.click(screen.getByRole("button", { name: /concordo/i })));
    expect(p.iniciar).not.toHaveBeenCalled();
    expect(screen.getByRole("alert").textContent).toMatch(/não foi possível registrar/i);
  });

  it("com o consentimento vigente, inicia direto, sem tela", async () => {
    const p = plugin();
    await tocarIniciar(p, { vigente: true, registrar: vi.fn(async () => {}) });
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(p.iniciar).toHaveBeenCalledTimes(1);
  });
});
