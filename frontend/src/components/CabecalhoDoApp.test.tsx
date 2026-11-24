// @vitest-environment jsdom
// UI-43 (etapa 1): o cabeçalho do app no celular e a barra de abas com a pílula.
import { cleanup, render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it } from "vitest";

import { CabecalhoDoApp, secaoDaRota } from "./CabecalhoDoApp";
import { MobileNav } from "./MobileNav";

afterEach(cleanup);

describe("o nome da tela pela rota", () => {
  it("no app, as cinco telas", () => {
    expect(secaoDaRota("/noite", true)).toBe("Noite");
    expect(secaoDaRota("/dashboard", true)).toBe("Início");
    expect(secaoDaRota("/historico", true)).toBe("Histórico");
    expect(secaoDaRota("/dispositivos", true)).toBe("Dispositivos");
    expect(secaoDaRota("/configuracoes", true)).toBe("Configurações");
  });

  it("no site, Coletar no lugar de Noite", () => {
    expect(secaoDaRota("/coletar", false)).toBe("Coletar");
    expect(secaoDaRota("/noite", false)).toBeNull();
  });

  it("fora dos destinos, sem nome, e sem confundir prefixo", () => {
    expect(secaoDaRota("/privacidade", true)).toBeNull();
    expect(secaoDaRota("/historicox", true)).toBeNull();
  });
});

describe("o cabeçalho", () => {
  it("mostra a marca e a tela, só no celular", () => {
    render(<MemoryRouter initialEntries={["/historico"]}><CabecalhoDoApp nativo /></MemoryRouter>);
    const cab = screen.getByRole("banner");
    expect(cab.textContent).toBe("Smart DormioHistórico");
    expect(cab.className).toContain("md:hidden");
  });

  it("está na casca, antes do conteúdo da tela", () => {
    const layout = readFileSync(resolve("src/components/Layout.tsx"), "utf8");
    expect(layout).toMatch(/<CabecalhoDoApp \/>[\s\S]*<Outlet \/>/);
  });

  it("no celular, o caminho da BarraDoWorkspace se esconde para não repetir", () => {
    const barra = readFileSync(resolve("src/components/BarraDoWorkspace.tsx"), "utf8");
    expect(barra).toMatch(/className="hidden text-\[10px\] text-muted-foreground md:block"/);
    // Sem o caminho, o selo e o tema ficam à direita, e não encostados à esquerda.
    expect(barra).toContain('className="mb-6 flex items-center justify-end gap-3 md:justify-between"');
  });
});

describe("a barra de abas", () => {
  it("a aba ativa tem a pílula atrás do ícone, e só ela", () => {
    render(<MemoryRouter initialEntries={["/historico"]}><MobileNav /></MemoryRouter>);
    const ativa = screen.getByRole("link", { current: "page" });
    expect(ativa.textContent).toBe("Histórico");
    expect(ativa.className).toContain("group");
    const pilula = ativa.querySelector("[data-pilula]");
    expect(pilula?.className).toContain("group-aria-[current=page]:bg-secondary");
    expect(screen.getAllByRole("link").filter((l) => l.getAttribute("aria-current") === "page")).toHaveLength(1);
  });
});
