// @vitest-environment jsdom
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const html = readFileSync(resolve("public/landing-prototipo.html"), "utf8");
const pagina = new DOMParser().parseFromString(html, "text/html");

function textoDaPagina(): string {
  return pagina.querySelector("#screen-landing")?.textContent ?? "";
}

it("mantém as seções interativas do protótipo na landing", () => {
  for (const id of ["sdp-app", "lp-simulador", "lp-telemetria", "sdx-explorer"]) {
    expect(pagina.querySelector(`#screen-landing #${id}`)).not.toBeNull();
  }
  for (const caminho of ["/login", "/cadastro", "/privacidade"]) {
    expect(pagina.querySelector(`a[href="${caminho}"][target="_top"]`)).not.toBeNull();
  }
});

describe("página inicial x arquitetura de captação (UI-23)", () => {
  it.each(["Deep Sleep", "Wake-on-Motion", "a cada evento", "acorda ao detectar movimento"])(
    "não descreve a arquitetura abandonada: %s",
    (termo) => {
      expect(textoDaPagina().toLowerCase()).not.toContain(termo.toLowerCase());
    },
  );

  it("descreve a arquitetura C2: sono leve, FIFO a 50 Hz, envio em lote", () => {
    const texto = textoDaPagina();
    expect(texto).toContain("sono leve");
    expect(texto).toContain("50 Hz");
    expect(texto).toContain("A cada 10 minutos");
  });
});
