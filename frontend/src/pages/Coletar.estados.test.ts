import { describe, expect, it } from "vitest";

import type { EstadoDoEnvio, Registro } from "../hooks/useColeta";

/**
 * Guarda contra o defeito do APP-10 (25/08/2026).
 *
 * O registro entra na lista ANTES de a requisicao terminar. A versao anterior
 * guardava `enviada: boolean` mais `falha: string | null` — tres situacoes em
 * dois campos — e a tela leu como duas: `enviada ? check : X`.
 *
 * Resultado: a epoca aparecia com X VERMELHO enquanto ainda estava sendo
 * enviada, e virava check um segundo depois. Alarme falso que parece perda de
 * dado.
 */

const ESTADOS: EstadoDoEnvio[] = ["enviando", "gravada", "falhou"];

function registro(envio: EstadoDoEnvio, falha: string | null = null): Registro {
  return {
    agregado: { ax: 0, ay: 0, az: 9.81, total: 9.81, amostras: 600,
                epocaSegundos: 10, fimEmMs: Date.now() },
    envio,
    falha,
  };
}

describe("estado do envio (APP-10)", () => {
  it("sao TRES estados, nao um booleano", () => {
    // O tipo e o que impede o defeito voltar: esquecer um caso agora e erro
    // de compilacao, nao susto na tela.
    expect(ESTADOS).toHaveLength(3);
    expect(new Set(ESTADOS).size).toBe(3);
  });

  it("enviando nao e falha", () => {
    // O coracao do defeito. Enquanto a requisicao esta no ar, o registro nao
    // esta gravado E nao falhou.
    const r = registro("enviando");
    expect(r.envio).not.toBe("falhou");
    expect(r.envio).not.toBe("gravada");
    expect(r.falha).toBeNull();
  });

  it("so o estado de falha carrega motivo", () => {
    expect(registro("enviando").falha).toBeNull();
    expect(registro("gravada").falha).toBeNull();
    expect(registro("falhou", "Sem conexao.").falha).toBe("Sem conexao.");
  });
});

describe("a tela distingue os tres estados", () => {
  it("cada estado tem seu proprio desenho, e a falha mostra o texto", async () => {
    // Guarda de fonte: o defeito era exatamente a tela colapsar tres estados
    // em dois. Se alguem voltar a escrever `enviada ? ... : ...`, quebra aqui.
    const { readFileSync } = await import("node:fs");
    const fonte = readFileSync(new URL("./Coletar.tsx", import.meta.url), "utf-8");

    for (const estado of ESTADOS) {
      expect(fonte).toContain(`"${estado}"`);
    }
    // O indicador de progresso precisa existir; sem ele, "enviando" volta a
    // ser desenhado como uma das outras duas coisas.
    expect(fonte).toContain("Loader2");

    // `title` e tooltip de mouse; esta tela e para celular.
    expect(fonte).not.toContain("title={r.falha");
  });
});
