import { describe, expect, it } from "vitest";

import { GRAVIDADE, ehMovimento, instanteDaLeitura, intensidade } from "./sleep";

describe("intensidade", () => {
  it("e zero em repouso exato", () => {
    expect(intensidade({ created_at: "", movimento_total: GRAVIDADE, temp: null, status: null })).toBe(0);
  });

  it("e simetrica: mesmo desvio para os dois lados da gravidade", () => {
    const acima = intensidade({ created_at: "", movimento_total: GRAVIDADE + 1.3, temp: null, status: null });
    const abaixo = intensidade({ created_at: "", movimento_total: GRAVIDADE - 1.3, temp: null, status: null });
    expect(acima).toBeCloseTo(abaixo!, 10);
  });

  it("devolve null quando nao ha leitura, para o grafico abrir lacuna", () => {
    expect(intensidade(null)).toBeNull();
    expect(intensidade(undefined)).toBeNull();
    expect(intensidade({ created_at: "", movimento_total: null, temp: null, status: null })).toBeNull();
  });

  it("nao confunde ausencia de dado com repouso", () => {
    // Zero seria "medimos e nao houve movimento"; null e "nao medimos".
    expect(intensidade({ created_at: "", movimento_total: null, temp: null, status: null })).not.toBe(0);
  });
});

describe("ehMovimento", () => {
  it("reconhece o rotulo do contrato v1.1.0", () => {
    expect(ehMovimento("Movimento")).toBe(true);
    expect(ehMovimento("Repouso")).toBe(false);
  });

  it("reconhece o rotulo legado ja gravado no banco", () => {
    expect(ehMovimento("Movimento Detectado!")).toBe(true);
    expect(ehMovimento("Dormindo")).toBe(false);
  });

  it("trata ausencia de status como repouso, nao como erro", () => {
    expect(ehMovimento(null)).toBe(false);
    expect(ehMovimento(undefined)).toBe(false);
    expect(ehMovimento("")).toBe(false);
  });
});

describe("instanteDaLeitura (DASH-12)", () => {
  const base = { movimento_total: null, temp: null, status: null };

  it("prefere o instante da MEDICAO ao da chegada", () => {
    // A diferenca entre os dois e latencia de rede. Descrever a captacao pela
    // chegada faz a latencia virar irregularidade de cadencia.
    expect(
      instanteDaLeitura({
        ...base,
        created_at: "2026-08-25T14:00:03.000Z",
        captured_at: "2026-08-25T14:00:00.000Z",
      }),
    ).toBe("2026-08-25T14:00:00.000Z");
  });

  it("cai para a chegada nas linhas gravadas antes do campo existir", () => {
    expect(instanteDaLeitura({ ...base, created_at: "2026-08-25T14:00:03.000Z" })).toBe(
      "2026-08-25T14:00:03.000Z",
    );
  });

  it("trata `captured_at` nulo ou vazio como ausente", () => {
    const chegada = "2026-08-25T14:00:03.000Z";
    expect(instanteDaLeitura({ ...base, created_at: chegada, captured_at: null })).toBe(chegada);
    expect(instanteDaLeitura({ ...base, created_at: chegada, captured_at: "" })).toBe(chegada);
  });

  it("devolve vazio quando nao ha instante nenhum, em vez de inventar um", () => {
    // String vazia sinaliza "descarte esta linha". `new Date(null)` daria
    // 1970 e arrastaria a janela do painel por decadas.
    expect(instanteDaLeitura({ ...base, created_at: "" })).toBe("");
    expect(
      instanteDaLeitura({ ...base, created_at: null as unknown as string }),
    ).toBe("");
  });
});
