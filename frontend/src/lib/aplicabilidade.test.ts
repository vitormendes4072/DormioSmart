import { describe, expect, it } from "vitest";

import {
  IDADE_DE_ADOLESCENTE,
  IDADE_DE_MAIORIDADE,
  IDADE_DE_PESSOA_IDOSA,
  aplicabilidadeDaIdade,
  faixaDaIdade,
} from "./aplicabilidade";

describe("faixaDaIdade — fronteiras legais, nao clinicas", () => {
  it("classifica cada faixa", () => {
    expect(faixaDaIdade(0)).toBe("crianca");
    expect(faixaDaIdade(11)).toBe("crianca");
    expect(faixaDaIdade(12)).toBe("adolescente");
    expect(faixaDaIdade(17)).toBe("adolescente");
    expect(faixaDaIdade(18)).toBe("adulto");
    expect(faixaDaIdade(59)).toBe("adulto");
    expect(faixaDaIdade(60)).toBe("pessoa-idosa");
    expect(faixaDaIdade(120)).toBe("pessoa-idosa");
  });

  it("as fronteiras sao as da lei, e estao onde o cabecalho diz", () => {
    // Procedencia, nao decoracao (§3 das licoes): 12 e a fronteira
    // crianca/adolescente do ECA e do art. 14 da LGPD; 18 e a maioridade do
    // Codigo Civil; 60 e a Lei 10.741/2003. Se alguem "arredondar" um destes,
    // este teste cai e obriga a justificar com fonte.
    expect([IDADE_DE_ADOLESCENTE, IDADE_DE_MAIORIDADE, IDADE_DE_PESSOA_IDOSA]).toEqual([
      12, 18, 60,
    ]);
  });
});

describe("aplicabilidadeDaIdade", () => {
  it("sem idade nao ha aviso, e esse e o caso normal", () => {
    // A idade e opcional (art. 6, III). `null` nao e erro: e ausencia.
    expect(aplicabilidadeDaIdade(null)).toBeNull();
    expect(aplicabilidadeDaIdade(undefined)).toBeNull();
  });

  it("valor que nao e inteiro conta como ausente, e nao como zero", () => {
    // Ler numero de corpo JSON alheio e confiar e como `0` vira idade.
    expect(aplicabilidadeDaIdade(22.5)).toBeNull();
    expect(aplicabilidadeDaIdade(-3)).toBeNull();
    expect(aplicabilidadeDaIdade(Number.NaN)).toBeNull();
  });

  it("adulto e a faixa coberta pelas coortes citadas", () => {
    const r = aplicabilidadeDaIdade(30);
    expect(r?.cobertura).toBe("coberta");
    expect(r?.menorDeIdade).toBe(false);
  });

  it("pessoa idosa NAO e coberta, e o aviso diz extrapolacao", () => {
    // O ponto do item inteiro: registrar a idade e o que permite DIZER que
    // aplicar aqui e extrapolar, em vez de calar.
    const r = aplicabilidadeDaIdade(70);
    expect(r?.cobertura).toBe("nao-coberta");
    expect(r?.aviso).toContain("extrapolar");
  });

  it("crianca e adolescente tem cobertura parcial, com a ressalva dita", () => {
    for (const idade of [9, 15]) {
      const r = aplicabilidadeDaIdade(idade);
      expect(r?.cobertura, String(idade)).toBe("parcial");
      // A coorte citada para a faixa e pediatrica e de PUNHO, nao de
      // travesseiro — a ressalva tem de estar no aviso, nao so no documento.
      expect(r?.aviso, String(idade)).toContain("punho");
      expect(r?.aviso, String(idade)).toContain("8 a 16");
    }
  });

  it("menor de idade e sinalizado — e por que isso importa", () => {
    // Art. 14 da LGPD: dado de crianca e adolescente exige melhor interesse e,
    // para crianca, consentimento de um dos pais. O sistema NAO trata isso de
    // forma diferente hoje, e isso e lacuna declarada na politica e no
    // `LGPD-05`. A flag existe para que a lacuna tenha onde ser fechada.
    expect(aplicabilidadeDaIdade(11)?.menorDeIdade).toBe(true);
    expect(aplicabilidadeDaIdade(17)?.menorDeIdade).toBe(true);
    expect(aplicabilidadeDaIdade(18)?.menorDeIdade).toBe(false);
  });

  it("nenhum aviso promete diagnostico nem fala de doenca", () => {
    // O aviso e sobre APLICABILIDADE de coorte. Um texto que dissesse
    // "o seu sono esta alterado para a sua idade" seria afirmacao clinica, que
    // este trabalho nao faz e nao pode fazer (ver LIMITACOES-TCC.md X.1).
    for (const idade of [5, 14, 30, 80]) {
      const aviso = aplicabilidadeDaIdade(idade)?.aviso ?? "";
      for (const proibido of ["diagnóstic", "doença", "transtorno", "normal para"]) {
        expect(aviso.toLowerCase(), `${idade}: ${proibido}`).not.toContain(proibido);
      }
    }
  });
});
