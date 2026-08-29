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

// --- vazamentos de bastidores (nivel 3 da revisao de 25/08) --------------
//
// Regra: se o texto explica POR QUE construimos assim, nao e informacao para
// quem usa. Estas guardas travam a regressao.

describe("a interface nao explica a si mesma", () => {
  function telas(): string {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { readFileSync } = require("node:fs") as typeof import("node:fs");
    return ["../pages/Dashboard.tsx", "../pages/Settings.tsx", "../pages/Coletar.tsx"]
      .map((c) => readFileSync(new URL(c, import.meta.url), "utf-8"))
      .join("\n")
      .replace(/\/\*[\s\S]*?\*\//g, "")
      .replace(/^\s*\/\/.*$/gm, "");
  }

  it("nao mostra identificador de item de roadmap", () => {
    // "(DATA-02)" aparecia no rodape da tabela de leituras.
    expect(telas()).not.toMatch(/\(DATA-\d+\)/);
    expect(telas()).not.toMatch(/\(DASH-\d+\)/);
  });

  it("nao mostra justificativa de engenharia", () => {
    // "enviar tudo daria mais de 200 mil linhas por hora" e razao de projeto,
    // nao informacao de uso.
    expect(telas()).not.toContain("mil linhas por hora");
  });

  it("nao afirma que a autenticacao ainda nao existe", () => {
    // Texto que ficou obsoleto quando o AUTH-02/03 subiu, e passou a dizer
    // que uma coisa pronta nao existe.
    expect(telas()).not.toContain("autenticação de usuário entrar no ar");
  });

  it("nao promete politica de privacidade 'em elaboracao'", () => {
    // Item morto num app que coleta dado corporal chama atencao para a
    // lacuna sem resolve-la. Volta quando existir (LGPD-01).
    expect(telas()).not.toContain("em elaboração");
  });
});

describe("a barra de navegacao tem so destinos", () => {
  it("Sair nao ocupa slot de navegacao", () => {
    // Um quarto da barra para uma acao usada uma vez por sessao, ao lado de
    // tres lugares visitados o tempo todo.
    // Sem tirar comentarios, casa com a nota que EXPLICA por que o Sair
    // saiu daqui — terceira vez que uma guarda de fonte tropeça nisso.
    const nav = fonteSemComentarios("../components/MobileNav.tsx", import.meta.url);
    expect(nav).not.toContain("Sair");
    expect(nav).not.toContain("sair()");
  });

  it("mas Sair existe nas Configuracoes", () => {
    const cfg = fonteSemComentarios("../pages/Settings.tsx", import.meta.url);
    expect(cfg).toContain("Sair da conta");
  });
});
