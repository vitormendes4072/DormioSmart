import { describe, expect, it } from "vitest";

import {
  EVENTOS_PADRAO,
  GEOMETRIA_PADRAO,
  PONTOS_PADRAO,
  caminhoEmLoop,
  gerarSinal,
  yDoValor,
} from "./sinal";
import { GRAVIDADE, LIMIAR_DE_MOVIMENTO } from "../types/sleep";

const G = GEOMETRIA_PADRAO;

/** Extrai os pares (x, y) de um caminho "Mx,y Lx,y ...". */
function pontosDo(caminho: string): [number, number][] {
  return caminho
    .split(" ")
    .map((parte) => parte.slice(1).split(",").map(Number) as [number, number]);
}

describe("gerarSinal", () => {
  it("e deterministico: a mesma semente devolve o mesmo desenho", () => {
    // A captura de tela do devlog e do texto do TCC precisa ser refazivel.
    expect(gerarSinal({ semente: 7 })).toEqual(gerarSinal({ semente: 7 }));
  });

  it("sementes diferentes desenham tracados diferentes", () => {
    expect(gerarSinal({ semente: 7 })).not.toEqual(gerarSinal({ semente: 8 }));
  });

  it("gera a quantidade pedida de pontos", () => {
    expect(gerarSinal()).toHaveLength(PONTOS_PADRAO);
    expect(gerarSinal({ pontos: 42 })).toHaveLength(42);
  });

  it("mantem o repouso abaixo do limiar desenhado", () => {
    // Se o ruido de repouso rompesse a faixa de 1,2 m/s2, o grafico
    // contradiria o proprio criterio que ele ilustra.
    const valores = gerarSinal();
    valores.forEach((valor, i) => {
      const fracao = i / valores.length;
      const emEvento = EVENTOS_PADRAO.some(([a, b]) => fracao >= a && fracao <= b);
      if (emEvento) return;
      expect(Math.abs(valor - GRAVIDADE)).toBeLessThan(LIMIAR_DE_MOVIMENTO);
    });
  });

  it("rompe o limiar dentro de cada evento", () => {
    const valores = gerarSinal();
    for (const [a, b] of EVENTOS_PADRAO) {
      const naFaixa = valores.filter((_, i) => {
        const fracao = i / valores.length;
        return fracao >= a && fracao <= b;
      });
      const maior = Math.max(...naFaixa.map((v) => Math.abs(v - GRAVIDADE)));
      expect(maior).toBeGreaterThan(LIMIAR_DE_MOVIMENTO);
    }
  });

  it("deixa as bordas em repouso, para a emenda do loop nao aparecer", () => {
    const valores = gerarSinal();
    for (const indice of [0, valores.length - 1]) {
      expect(Math.abs(valores[indice] - GRAVIDADE)).toBeLessThan(LIMIAR_DE_MOVIMENTO);
    }
  });
});

describe("yDoValor", () => {
  it("poe o repouso no meio da altura", () => {
    expect(yDoValor(GRAVIDADE)).toBe(G.altura / 2);
  });

  it("sobe na tela quando a aceleracao cresce", () => {
    // y cresce para baixo em SVG: valor maior tem y menor.
    expect(yDoValor(GRAVIDADE + 1)).toBeLessThan(yDoValor(GRAVIDADE));
    expect(yDoValor(GRAVIDADE - 1)).toBeGreaterThan(yDoValor(GRAVIDADE));
  });

  it("grampeia valor extremo na borda em vez de desenhar fora dela", () => {
    expect(yDoValor(GRAVIDADE + 1000)).toBe(0);
    expect(yDoValor(GRAVIDADE - 1000)).toBe(G.altura);
  });
});

describe("caminhoEmLoop", () => {
  const valores = gerarSinal({ pontos: 24, semente: 3 });
  const pontos = pontosDo(caminhoEmLoop(valores));

  it("desenha dois periodos mais o ponto de fechamento", () => {
    expect(pontos).toHaveLength(2 * valores.length + 1);
  });

  it("cobre exatamente o dobro da largura do recorte", () => {
    expect(pontos[0][0]).toBe(0);
    expect(pontos[pontos.length - 1][0]).toBeCloseTo(2 * G.largura, 1);
  });

  it("repete o desenho a cada periodo — e o que faz o loop nao ter emenda", () => {
    // A animacao desloca a camada em exatamente um periodo. Se o ponto i+n
    // nao fosse identico ao ponto i, o reinicio daria um salto visivel.
    const n = valores.length;
    for (let i = 0; i <= n; i++) {
      expect(pontos[i + n][1]).toBe(pontos[i][1]);
      expect(pontos[i + n][0] - pontos[i][0]).toBeCloseTo(G.largura, 1);
    }
  });

  it("comeca com M e segue so com L", () => {
    const caminho = caminhoEmLoop(valores);
    expect(caminho.startsWith("M")).toBe(true);
    expect(caminho.slice(1)).not.toContain("M");
  });

  it("devolve vazio sem pontos, em vez de um caminho invalido", () => {
    expect(caminhoEmLoop([])).toBe("");
  });
});
