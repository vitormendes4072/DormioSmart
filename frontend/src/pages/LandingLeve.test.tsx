// @vitest-environment jsdom
// APP-17: a apresentação leve também oferece o APK, pelo mesmo endereço da completa.
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { URL_DO_APK, VERSAO_DO_APP_ANDROID } from "../lib/appAndroid";
import { Landing } from "./Landing";

vi.mock("../contexts/AuthContext", () => ({ useAuth: () => ({ sessao: null }) }));

beforeAll(() => {
  window.matchMedia ??= ((consulta: string) => ({
    matches: false, media: consulta, onchange: null,
    addEventListener: () => {}, removeEventListener: () => {},
    addListener: () => {}, removeListener: () => {}, dispatchEvent: () => false,
  })) as typeof window.matchMedia;
  globalThis.IntersectionObserver ??= class {
    observe() {} unobserve() {} disconnect() {} takeRecords() { return []; }
    root = null; rootMargin = ""; thresholds = [];
  } as unknown as typeof IntersectionObserver;
});
afterEach(cleanup);

describe("landing leve, app Android", () => {
  it("leva ao APK publicado e mostra a versão", () => {
    render(<MemoryRouter initialEntries={["/?apresentacao=leve"]}><Landing /></MemoryRouter>);
    const link = screen.getByRole("link", { name: "Baixar para Android" });
    expect(link.getAttribute("href")).toBe(URL_DO_APK);
    expect(document.querySelector("#app-android")?.textContent).toContain(`Versão ${VERSAO_DO_APP_ANDROID}`);
  });
});
