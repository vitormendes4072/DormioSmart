/**
 * LGPD-01 (b): a política servida no app é o documento versionado, recortado.
 *
 * Os testes leem o `docs/POLITICA-DE-PRIVACIDADE.md` REAL: o que se trava é que
 * o titular vê o texto publicável inteiro, e nada das notas para o autor.
 */
import { describe, expect, it } from "vitest";

import documento from "../../../docs/POLITICA-DE-PRIVACIDADE.md?raw";
import { NAO_INFORMADO, marcadoresPendentes, preencher, textoPublicavel } from "./politica";

const texto = textoPublicavel(documento);

describe("o recorte do documento real", () => {
  it("traz as dez seções da política", () => {
    for (let n = 1; n <= 10; n++) {
      expect(texto, `seção ${n}`).toMatch(new RegExp(`^## ${n}\\. `, "m"));
    }
  });

  it("deixa de fora as notas para o autor", () => {
    expect(texto).not.toContain("Notas de levantamento");
    expect(texto).not.toContain("Lacunas conhecidas");
    expect(texto).not.toContain("Como ler este documento");
    expect(texto).not.toContain("── TEXTO");
    expect(texto).not.toContain("── FIM DO TEXTO");
  });

  it("começa no título e cobre a revisão de 03/11", () => {
    expect(texto.startsWith("# Política de Privacidade")).toBe(true);
    expect(texto).toContain("destinado apenas a maiores de 18 anos");
  });

  it("os únicos marcadores pendentes são o controlador e o contato", () => {
    // Um `[ALGUMA_COISA]` novo no texto publicável chegaria cru ao titular.
    expect(marcadoresPendentes(texto).sort()).toEqual(["[CONTATO]", "[CONTROLADOR]"]);
  });
});

describe("controlador e contato vêm de fora do repositório", () => {
  it("com os valores, troca os marcadores e não sobra nenhum", () => {
    const pronto = preencher(texto, { controlador: "Fulano", contato: "fulano@exemplo.com" });
    expect(pronto).toContain("Fulano");
    expect(pronto).toContain("fulano@exemplo.com");
    expect(marcadoresPendentes(pronto)).toEqual([]);
  });

  it("sem os valores, diz que não foram informados em vez de mostrar o marcador", () => {
    const pronto = preencher(texto, {});
    expect(pronto).toContain(NAO_INFORMADO);
    expect(marcadoresPendentes(pronto)).toEqual([]);
  });

  it("valor só de espaços conta como não informado", () => {
    expect(preencher("a [CONTATO] b", { contato: "   " })).toBe(`a ${NAO_INFORMADO} b`);
  });
});

describe("o recorte é estrito", () => {
  it("documento sem os marcadores de texto é erro, não página vazia", () => {
    expect(() => textoPublicavel("# só um título")).toThrow();
  });
});
