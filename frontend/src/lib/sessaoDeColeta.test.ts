import { describe, expect, it } from "vitest";

import { contarFalhas, resumoDaSessao } from "./sessaoDeColeta";
import type { EstadoDoEnvio, Registro } from "../hooks/useColeta";

function reg(envio: EstadoDoEnvio, i = 0): Registro {
  return {
    agregado: { ax: 0, ay: 0, az: 9.81, total: 9.81, amostras: 600,
                epocaSegundos: 30, fimEmMs: 1000 + i },
    envio,
    falha: envio === "falhou" ? "Sem conexao." : null,
  };
}

describe("resumoDaSessao", () => {
  it("sessao vazia nao inventa numero", () => {
    expect(resumoDaSessao([])).toEqual({ total: 0, gravados: 0, enviando: 0, falhas: 0 });
  });

  it("separa os tres estados", () => {
    const r = resumoDaSessao([
      reg("gravada", 1), reg("gravada", 2), reg("enviando", 3), reg("falhou", 4),
    ]);
    expect(r).toEqual({ total: 4, gravados: 2, enviando: 1, falhas: 1 });
  });

  it("o total fecha com a soma das partes", () => {
    const lista = [reg("gravada", 1), reg("enviando", 2), reg("falhou", 3), reg("gravada", 4)];
    const r = resumoDaSessao(lista);
    expect(r.gravados + r.enviando + r.falhas).toBe(r.total);
  });
});

describe("contarFalhas", () => {
  it("conta so o que falhou de verdade", () => {
    expect(contarFalhas([reg("falhou", 1), reg("falhou", 2)])).toBe(2);
  });

  it("ENVIANDO NAO e falha", () => {
    // Foi exatamente essa confusao que produziu o defeito do APP-10: a tela
    // desenhava X vermelho para requisicao ainda no ar. Aqui isso nao pode
    // voltar disfarcado de contador de alarme.
    expect(contarFalhas([reg("enviando", 1), reg("enviando", 2)])).toBe(0);
  });

  it("gravada nao e falha", () => {
    expect(contarFalhas([reg("gravada", 1)])).toBe(0);
  });

  it("sessao vazia nao alarma", () => {
    expect(contarFalhas([])).toBe(0);
  });
});

/**
 * Le o codigo-fonte SEM comentarios.
 *
 * As guardas abaixo procuram jargao na interface. Sem tirar comentarios, elas
 * casam com a propria nota que EXPLICA por que o jargao saiu — foi o que
 * aconteceu na primeira versao deste teste.
 */
function fonteSemComentarios(caminho: string, base: string): string {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const { readFileSync } = require("node:fs") as typeof import("node:fs");
  return readFileSync(new URL(caminho, base), "utf-8")
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/^\s*\/\/.*$/gm, "");
}

describe("a tela principal nao fala a lingua do desenvolvedor", () => {
  it("'época' e 'amostras' só aparecem nos detalhes técnicos", () => {
    // A tela nasceu como instrumento de bancada e expunha as engrenagens.
    // Quem vai dormir não sabe o que é época de agregação.
    const fonte = fonteSemComentarios("../pages/Coletar.tsx", import.meta.url);

    const abre = fonte.indexOf("<details");
    expect(abre).toBeGreaterThan(0);

    const principal = fonte.slice(0, abre);
    for (const jargao of ["Época de agregação", "ÉPOCA DE AGREGAÇÃO", "Épocas registradas"]) {
      expect(principal).not.toContain(jargao);
    }
  });

  it("o caminho principal leva ao painel", () => {
    // Sem saída, a pessoa coleta e a tela não a leva a lugar nenhum — e o
    // gráfico é o ponto inteiro.
    const fonte = fonteSemComentarios("../pages/Coletar.tsx", import.meta.url);
    const principal = fonte.slice(0, fonte.indexOf("<details"));
    expect(principal).toContain('to="/dashboard"');
  });

  it("o aviso da noite e a contagem de falhas ficam FORA dos detalhes", () => {
    // Simplificar não pode virar esconder problema.
    const fonte = fonteSemComentarios("../pages/Coletar.tsx", import.meta.url);
    const principal = fonte.slice(0, fonte.indexOf("<details"));
    expect(principal).toContain("não cobre uma noite de sono");
    expect(principal).toContain("contarFalhas");
  });
});

describe("o contador não roda a 60 Hz", () => {
  it("o listener de devicemotion não chama setState", () => {
    // Atualizar estado a cada amostra custava ~60 renderizações por segundo
    // durante a coleta inteira — bateria queimada para animar um contador,
    // no aparelho onde a bateria é o recurso escasso.
    const fonte = fonteSemComentarios("../hooks/useColeta.ts", import.meta.url);

    const inicio = fonte.indexOf("const aoMover");
    const fim = fonte.indexOf("};", inicio);
    const listener = fonte.slice(inicio, fim);

    expect(listener).toContain("buffer.current.push");
    expect(listener).not.toContain("setAmostrasNaEpoca");
  });
});
