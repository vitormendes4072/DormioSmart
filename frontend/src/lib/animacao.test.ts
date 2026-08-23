import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

import {
  CONSULTA_MENOS_MOVIMENTO,
  jaUltrapassado,
  podeAnimarRevelacao,
  prefereMenosMovimento,
} from "./animacao";

/** Janela falsa: `matchMedia` responde o que o teste mandar. */
function janela(reduz: boolean, comObservador = true) {
  return {
    matchMedia: (consulta: string) => ({ matches: consulta === CONSULTA_MENOS_MOVIMENTO && reduz }),
    ...(comObservador ? { IntersectionObserver: function () {} } : {}),
  };
}

describe("prefereMenosMovimento", () => {
  it("respeita o pedido de reducao do sistema", () => {
    expect(prefereMenosMovimento(janela(true))).toBe(true);
  });

  it("devolve false quando o sistema nao pede reducao", () => {
    expect(prefereMenosMovimento(janela(false))).toBe(false);
  });

  it("sem matchMedia, entende que nao houve pedido de reducao", () => {
    // Ausencia da API nao e um pedido. Se respondesse true, nenhum ambiente
    // sem matchMedia — incluindo o Node destes testes — teria animacao.
    expect(prefereMenosMovimento({})).toBe(false);
  });
});

describe("podeAnimarRevelacao", () => {
  it("libera quando ha observador e ninguem pediu reducao", () => {
    expect(podeAnimarRevelacao(janela(false))).toBe(true);
  });

  it("bloqueia sob pedido de reducao, mesmo com observador disponivel", () => {
    expect(podeAnimarRevelacao(janela(true))).toBe(false);
  });

  it("bloqueia sem IntersectionObserver", () => {
    // Sem observador nao ha quem revele. Armar o elemento nesse caso o
    // esconderia para sempre — o oposto de falhar aberto.
    expect(podeAnimarRevelacao(janela(false, false))).toBe(false);
  });
});

describe("jaUltrapassado", () => {
  it("nao considera ultrapassado o bloco na janela ou abaixo dela", () => {
    expect(jaUltrapassado({ bottom: 0 })).toBe(false);
    expect(jaUltrapassado({ bottom: 640 })).toBe(false);
    expect(jaUltrapassado({ bottom: 12000 })).toBe(false);
  });

  it("considera ultrapassado o bloco inteiro acima da janela", () => {
    // Defeito observado em producao: o navegador restaura a rolagem ao
    // recarregar, e o IntersectionObserver nunca reporta o que esta acima da
    // janela. Esses blocos ficavam escondidos ate o usuario voltar ao topo, e
    // entao animavam de novo — releitura virava desfile.
    expect(jaUltrapassado({ bottom: -1 })).toBe(true);
    expect(jaUltrapassado({ bottom: -1488 })).toBe(true);
  });
});

describe("animacoes.css desliga tudo sob prefers-reduced-motion", () => {
  const bruto = readFileSync(new URL("../styles/animacoes.css", import.meta.url), "utf-8");
  // Comentario nao e regra: `lib/animacao.ts` dentro de uma nota seria lido
  // como o seletor `.ts` pela varredura abaixo.
  const css = bruto.replace(/\/\*[\s\S]*?\*\//g, "");
  const marcador = "@media (prefers-reduced-motion: reduce)";
  const corte = css.indexOf(marcador);
  const acima = css.slice(0, corte);
  const bloco = css.slice(corte);

  it("o bloco de reducao existe e vem por ultimo", () => {
    // A especificidade e a mesma das regras acima; quem decide e a posicao.
    expect(corte).toBeGreaterThan(0);
    expect(bloco).toContain("animation: none");
    expect(bloco).toContain("transition: none");
  });

  it("toda classe que anima aparece no bloco de reducao", () => {
    // Esta e a razao de o teste existir: adicionar uma animacao nova e
    // esquecer de anula-la falha aqui, nao no navegador de alguem.
    const animadas = new Set(
      [...acima.matchAll(/\.([a-z-]+)[^{}]*\{[^}]*?(?:animation|transition):/g)].map((m) => m[1]),
    );

    expect(animadas.size).toBeGreaterThan(0);

    const esquecidas = [...animadas].filter((classe) => !bloco.includes(`.${classe}`));
    expect(esquecidas, `sem anulacao no bloco de reducao: ${esquecidas.join(", ")}`).toEqual([]);
  });

  it("a rolagem suave e declarada so na ausencia de pedido de reducao", () => {
    const semPreferencia = css.indexOf("@media (prefers-reduced-motion: no-preference)");
    expect(semPreferencia).toBeGreaterThan(0);
    expect(css.slice(semPreferencia, corte)).toContain("scroll-behavior: smooth");
    // Fora desse bloco nao pode haver outra declaracao de rolagem suave.
    expect(css.slice(0, semPreferencia)).not.toContain("scroll-behavior");
  });

  it("o texto da linha de fluxo volta a ter cor sob reducao", () => {
    // A varredura pinta o texto de transparente e desenha por
    // `background-clip`. Sem anular isso, o texto sumiria.
    const regra = bloco.slice(bloco.indexOf(".fluxo-animado"));
    expect(regra).toContain("background-image: none");
    expect(regra).toContain("color: var(--muted-foreground)");
  });
});
