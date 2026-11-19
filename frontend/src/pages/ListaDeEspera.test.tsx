// @vitest-environment jsdom
/**
 * A página da lista de espera (UI-14).
 *
 * O que estes testes travam: o botão só habilita com o e-mail certo e as duas
 * confirmações, e diz o que falta; o resto do formulário só se abre com o
 * e-mail certo; o envio leva exatamente o que a pessoa marcou; o sucesso e as
 * falhas aparecem; o campo-isca existe e está fora da vista e do teclado; o
 * texto da confirmação é o da constante; e a página não promete diagnóstico.
 * A tela é a REAL; só a chamada ao servidor é falsa.
 */
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { inscrever } = vi.hoisted(() => ({
  inscrever: vi.fn(() => Promise.resolve({ tipo: "inscrito" } as { tipo: string })),
}));

vi.mock("../lib/listaDeEspera", async (original) => ({
  ...(await original<typeof import("../lib/listaDeEspera")>()),
  inscreverNaListaDeEspera: inscrever,
}));

import { TEXTO_DO_CONSENTIMENTO_DA_LISTA } from "../lib/listaDeEspera";
import { ListaDeEspera } from "./ListaDeEspera";

function abrir() {
  render(
    <MemoryRouter>
      <ListaDeEspera />
    </MemoryRouter>,
  );
}

const email = () => screen.getByLabelText("Seu e-mail") as HTMLInputElement;
const botao = () => screen.getByRole("button", { name: /Comece pelo e-mail|confirma|Entrar na lista|Guardando/ });
const consentimento = () => screen.getByRole("checkbox", { name: /Concordo que o Smart Dormio/ });
const maioridade = () => screen.getByRole("checkbox", { name: "Tenho 18 anos ou mais." });

function preencherTudo(comNome = "Maria Silva") {
  fireEvent.change(email(), { target: { value: "maria@exemplo.com" } });
  fireEvent.change(screen.getByLabelText(/Como prefere ser chamado/), { target: { value: comNome } });
  fireEvent.click(consentimento());
  fireEvent.click(maioridade());
}

beforeEach(() => {
  inscrever.mockClear();
  inscrever.mockImplementation(() => Promise.resolve({ tipo: "inscrito" }));
  // O jsdom não tem `matchMedia`. O tema o consulta; aqui a página responde como
  // para quem pede menos movimento, para os testes não dependerem de animação.
  window.matchMedia = vi.fn((consulta: string) => ({
    matches: consulta.includes("reduced-motion"),
    media: consulta,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })) as unknown as typeof window.matchMedia;
  window.scrollBy = vi.fn();
  Element.prototype.scrollIntoView = vi.fn();
});

afterEach(() => {
  cleanup();
});

describe("o botão diz o que falta", () => {
  it("começa desabilitado, pedindo o e-mail", () => {
    abrir();
    expect(botao()).toHaveProperty("disabled", true);
    expect(botao().textContent).toContain("Comece pelo e-mail");
  });

  it("com o e-mail certo, pede as confirmações, uma a uma, e só então habilita", () => {
    abrir();
    fireEvent.change(email(), { target: { value: "maria@exemplo.com" } });
    expect(botao().textContent).toContain("Marque as duas confirmações");
    fireEvent.click(consentimento());
    expect(botao().textContent).toContain("Falta uma confirmação");
    expect(botao()).toHaveProperty("disabled", true);
    fireEvent.click(maioridade());
    expect(botao().textContent).toContain("Entrar na lista de espera");
    expect(botao()).toHaveProperty("disabled", false);
  });

  it("e-mail inválido não habilita, mesmo com as duas confirmações", () => {
    abrir();
    fireEvent.change(email(), { target: { value: "maria@exemplo" } });
    fireEvent.click(consentimento());
    fireEvent.click(maioridade());
    expect(botao()).toHaveProperty("disabled", true);
  });
});

describe("o formulário se abre por partes", () => {
  it("o resto fica fechado até o e-mail estar certo", () => {
    abrir();
    const resto = consentimento().closest(".le-abre");
    expect(resto?.classList.contains("aberto")).toBe(false);
    fireEvent.change(email(), { target: { value: "maria@exemplo.com" } });
    expect(resto?.classList.contains("aberto")).toBe(true);
  });

  it("ao sair do campo com um e-mail incompleto, diz por quê", () => {
    abrir();
    fireEvent.change(email(), { target: { value: "maria@" } });
    fireEvent.blur(email());
    expect(screen.getByText("Confira o e-mail: ele parece incompleto.")).toBeTruthy();
    expect(email().getAttribute("aria-invalid")).toBe("true");
  });

  it("sugere o domínio provável e corrige só com o clique", () => {
    abrir();
    fireEvent.change(email(), { target: { value: "maria@gmial.com" } });
    fireEvent.blur(email());
    expect(email().value).toBe("maria@gmial.com");
    fireEvent.click(screen.getByRole("button", { name: "maria@gmail.com" }));
    expect(email().value).toBe("maria@gmail.com");
  });
});

describe("o envio", () => {
  it("leva o que a pessoa preencheu e mostra o sucesso com o nome dela", async () => {
    abrir();
    preencherTudo();
    fireEvent.click(botao());
    await waitFor(() => expect(inscrever).toHaveBeenCalledTimes(1));
    expect(inscrever).toHaveBeenCalledWith({
      email: "maria@exemplo.com", nome: "Maria Silva", consentimento: true, maioridade: true, site: "",
    });
    expect(await screen.findByRole("heading", { name: "Maria, você está na lista." })).toBeTruthy();
    expect(screen.getByText("maria@exemplo.com")).toBeTruthy();
    expect(screen.getByRole("button", { name: /Compartilhar o Smart Dormio/ })).toBeTruthy();
  });

  it("sem nome, o sucesso não inventa um", async () => {
    abrir();
    preencherTudo("");
    fireEvent.click(botao());
    expect(await screen.findByRole("heading", { name: "Você está na lista." })).toBeTruthy();
  });

  it("não envia sem as confirmações, nem com Enter", () => {
    abrir();
    fireEvent.change(email(), { target: { value: "maria@exemplo.com" } });
    fireEvent.submit(email().closest("form")!);
    expect(inscrever).not.toHaveBeenCalled();
  });

  it.each([
    ["lista_cheia", "Recebemos muitas inscrições agora"],
    ["indisponivel", "Seu e-mail não foi guardado"],
    ["texto_mudou", "Recarregue a página"],
  ])("a falha %s aparece e o formulário fica", async (tipo, trecho) => {
    inscrever.mockImplementation(() => Promise.resolve({ tipo }));
    abrir();
    preencherTudo();
    fireEvent.click(botao());
    expect((await screen.findByRole("alert")).textContent).toContain(trecho);
    expect(email().value).toBe("maria@exemplo.com");
  });
});

describe("o que a página não pode deixar de ter", () => {
  it("o texto da confirmação é o da constante", () => {
    abrir();
    const texto = consentimento().closest("label")?.textContent?.replace(/\s+/g, " ").trim();
    expect(texto).toBe(TEXTO_DO_CONSENTIMENTO_DA_LISTA);
  });

  it("o campo-isca existe, fora da vista e do teclado", () => {
    abrir();
    const isca = document.querySelector('input[name="site"]') as HTMLInputElement;
    expect(isca).not.toBeNull();
    expect(isca.tabIndex).toBe(-1);
    expect(isca.closest('[aria-hidden="true"]')).not.toBeNull();
  });

  it("o link para a política está no formulário", () => {
    abrir();
    expect(screen.getByRole("link", { name: "política de privacidade" }).getAttribute("href")).toBe("/privacidade");
  });

  it.each(["diagnóstico de", "detecta apneia", "estágios do sono", "melhora o sono", "trata"])(
    "não promete: %s",
    (termo) => {
      abrir();
      const texto = document.body.textContent?.toLowerCase() ?? "";
      expect(texto).not.toContain(termo);
    },
  );

  it("declara o escopo: não faz estadiamento nem diagnóstico", () => {
    abrir();
    expect(document.body.textContent).toContain("não faz estadiamento de sono nem diagnóstico clínico");
  });
});
