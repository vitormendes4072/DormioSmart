import { describe, expect, it, vi } from "vitest";

import {
  CHAVE_ARMAZENAMENTO,
  aplicarTema,
  ehPreferenciaValida,
  lerPreferencia,
  resolverTema,
  salvarPreferencia,
} from "./tema";

function armazenamentoFalso(inicial: Record<string, string> = {}) {
  const dados = { ...inicial };
  return {
    getItem: (chave: string) => dados[chave] ?? null,
    setItem: (chave: string, valor: string) => {
      dados[chave] = valor;
    },
    dados,
  };
}

describe("resolverTema", () => {
  it("respeita a escolha explicita, ignorando o sistema", () => {
    expect(resolverTema("claro", true)).toBe("light");
    expect(resolverTema("escuro", false)).toBe("dark");
  });

  it("com 'sistema', segue a preferencia do sistema operacional", () => {
    expect(resolverTema("sistema", true)).toBe("dark");
    expect(resolverTema("sistema", false)).toBe("light");
  });

  it("nunca devolve 'sistema' — o CSS so conhece light e dark", () => {
    for (const p of ["claro", "escuro", "sistema"] as const) {
      expect(["light", "dark"]).toContain(resolverTema(p, true));
      expect(["light", "dark"]).toContain(resolverTema(p, false));
    }
  });
});

describe("lerPreferencia", () => {
  it("devolve o valor salvo quando e valido", () => {
    expect(lerPreferencia(armazenamentoFalso({ [CHAVE_ARMAZENAMENTO]: "escuro" }))).toBe("escuro");
  });

  it("cai em 'sistema' quando nao ha nada salvo", () => {
    expect(lerPreferencia(armazenamentoFalso())).toBe("sistema");
  });

  it("cai em 'sistema' diante de valor corrompido", () => {
    expect(lerPreferencia(armazenamentoFalso({ [CHAVE_ARMAZENAMENTO]: "arco-iris" }))).toBe(
      "sistema",
    );
  });

  it("nao quebra se o localStorage lancar (navegacao privada)", () => {
    const bloqueado = {
      getItem: () => {
        throw new DOMException("acesso negado");
      },
    };
    expect(lerPreferencia(bloqueado)).toBe("sistema");
  });
});

describe("salvarPreferencia", () => {
  it("grava sob a chave esperada", () => {
    const armazenamento = armazenamentoFalso();
    salvarPreferencia(armazenamento, "claro");
    expect(armazenamento.dados[CHAVE_ARMAZENAMENTO]).toBe("claro");
  });

  it("engole falha de escrita — tema e conforto, nao funcionalidade", () => {
    const cheio = {
      setItem: () => {
        throw new DOMException("cota excedida");
      },
    };
    expect(() => salvarPreferencia(cheio, "escuro")).not.toThrow();
  });
});

describe("ehPreferenciaValida", () => {
  it.each(["claro", "escuro", "sistema"])("aceita %s", (v) => {
    expect(ehPreferenciaValida(v)).toBe(true);
  });

  it.each([null, undefined, 42, "dark", "light", ""])("rejeita %s", (v) => {
    expect(ehPreferenciaValida(v)).toBe(false);
  });
});

describe("aplicarTema", () => {
  it("escreve em data-theme, que e o seletor usado pelo CSS", () => {
    const raiz = { dataset: {} } as unknown as HTMLElement;
    aplicarTema("dark", raiz);
    expect(raiz.dataset.theme).toBe("dark");
  });
});

describe("integracao preferencia -> tema aplicado", () => {
  it("valor invalido no armazenamento nao impede resolver um tema", () => {
    const preferencia = lerPreferencia(armazenamentoFalso({ [CHAVE_ARMAZENAMENTO]: "lixo" }));
    const raiz = { dataset: {} } as unknown as HTMLElement;
    aplicarTema(resolverTema(preferencia, false), raiz);
    expect(raiz.dataset.theme).toBe("light");
  });

  it("o ciclo salvar -> ler preserva a escolha", () => {
    const armazenamento = armazenamentoFalso();
    salvarPreferencia(armazenamento, "escuro");
    expect(lerPreferencia(armazenamento)).toBe("escuro");
  });
});

describe("script anti-flash do index.html", () => {
  it("usa a mesma chave de armazenamento que o app", async () => {
    // O script inline duplica a logica em JS puro por necessidade (roda antes
    // do bundle). Se as chaves divergirem, o tema salvo seria ignorado no
    // carregamento e voltaria o flash — este teste trava isso.
    const { readFileSync } = await import("node:fs");
    const html = readFileSync(new URL("../../index.html", import.meta.url), "utf-8");
    expect(html).toContain(CHAVE_ARMAZENAMENTO);
  });

  it("roda antes do bundle, senao nao evita o flash", async () => {
    const { readFileSync } = await import("node:fs");
    const html = readFileSync(new URL("../../index.html", import.meta.url), "utf-8");
    expect(html.indexOf(CHAVE_ARMAZENAMENTO)).toBeLessThan(html.indexOf("/src/main.tsx"));
  });
});

describe("nenhum componente conhece cor crua", () => {
  it("o azul da marca so aparece no theme.css", async () => {
    const { readdirSync, readFileSync, statSync } = await import("node:fs");
    const { join } = await import("node:path");

    const raiz = new URL("../", import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1");
    const arquivos: string[] = [];
    const varrer = (dir: string) => {
      for (const nome of readdirSync(dir)) {
        const caminho = join(dir, nome);
        if (statSync(caminho).isDirectory()) varrer(caminho);
        else if (/\.(tsx?|css)$/.test(nome) && !nome.endsWith(".test.ts")) {
          arquivos.push(caminho);
        }
      }
    };
    varrer(raiz);

    const infratores = arquivos.filter((caminho) => {
      if (caminho.endsWith("theme.css")) return false;
      return /#[0-9a-fA-F]{6}\b/.test(readFileSync(caminho, "utf-8"));
    });

    expect(infratores, `hex cru fora do theme.css: ${infratores.join(", ")}`).toEqual([]);
  });
});

// vi importado para manter o padrao dos demais arquivos de teste
void vi;
