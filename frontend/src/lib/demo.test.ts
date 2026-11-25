import { describe, expect, it } from "vitest";

import { ehMovimento, intensidade } from "../types/sleep";
import { LEITURAS_POR_PADRAO, estaEmModoDemo, gerarHistoricoDemo, gerarNoiteDemo } from "./demo";
import { calcularMetricas } from "./metricas";

describe("estaEmModoDemo — salvaguarda de producao", () => {
  it("NUNCA ativa em build de producao, mesmo com o parametro", () => {
    expect(estaEmModoDemo("?demo=1", false)).toBe(false);
    expect(estaEmModoDemo("?demo=true", false)).toBe(false);
  });

  it("ativa em desenvolvimento com o parametro", () => {
    expect(estaEmModoDemo("?demo=1", true)).toBe(true);
    expect(estaEmModoDemo("?demo", true)).toBe(true);
  });

  it("fica inativo sem o parametro", () => {
    expect(estaEmModoDemo("", true)).toBe(false);
    expect(estaEmModoDemo("?outro=1", true)).toBe(false);
  });

  it("aceita desligar explicitamente", () => {
    expect(estaEmModoDemo("?demo=0", true)).toBe(false);
    expect(estaEmModoDemo("?demo=false", true)).toBe(false);
  });
});

describe("gerarHistoricoDemo", () => {
  it("inclui leituras dos dois aparelhos na visão geral", () => {
    const aparelhos = gerarHistoricoDemo(null).map((leitura) => leitura.device_id);
    expect(new Set(aparelhos)).toEqual(new Set(["demo-travesseiro", "demo-celular"]));
  });

  it("gera leituras do celular quando o histórico é filtrado para ele", () => {
    const aparelhos = gerarHistoricoDemo("demo-celular").map((leitura) => leitura.device_id);
    expect(new Set(aparelhos)).toEqual(new Set(["demo-celular"]));
  });
});

describe("gerarNoiteDemo", () => {
  it("e deterministica: mesma semente, mesma captura", () => {
    const fim = new Date("2026-08-19T07:00:00.000Z");
    const a = gerarNoiteDemo({ fim, semente: 42 });
    const b = gerarNoiteDemo({ fim, semente: 42 });
    expect(a).toEqual(b);
  });

  it("sementes diferentes geram noites diferentes", () => {
    const fim = new Date("2026-08-19T07:00:00.000Z");
    expect(gerarNoiteDemo({ fim, semente: 1 })).not.toEqual(gerarNoiteDemo({ fim, semente: 2 }));
  });

  it("devolve do mais recente para o mais antigo, como a API", () => {
    const leituras = gerarNoiteDemo();
    const primeira = new Date(leituras[0].created_at).getTime();
    const ultima = new Date(leituras[leituras.length - 1].created_at).getTime();
    expect(primeira).toBeGreaterThan(ultima);
  });

  it("gera a quantidade pedida", () => {
    expect(gerarNoiteDemo({ quantidade: 12 })).toHaveLength(12);
  });

  it("por padrao gera o mesmo tanto que a API devolve (limit=20)", () => {
    // Mais que isso produziria captura de tela impossivel no app real, e as
    // barras ficariam finas demais para o grafico desenhar.
    expect(gerarNoiteDemo()).toHaveLength(LEITURAS_POR_PADRAO);
  });
});

describe("os dados gerados obedecem ao contrato v1.2.0", () => {
  const leituras = gerarNoiteDemo();

  it("usa apenas os rotulos do contrato — nunca os legados", () => {
    const rotulos = new Set(leituras.map((l) => l.status));
    expect([...rotulos].sort()).toEqual(["Movimento", "Repouso"]);
  });

  it("mantem a magnitude dentro da faixa fisica aceita pelo backend", () => {
    for (const l of leituras) {
      expect(l.movimento_total).toBeGreaterThanOrEqual(0);
      expect(l.movimento_total).toBeLessThanOrEqual(175);
    }
  });

  it("mantem a temperatura do chip na faixa do datasheet", () => {
    for (const l of leituras) {
      expect(l.temp).toBeGreaterThanOrEqual(-40);
      expect(l.temp).toBeLessThanOrEqual(85);
    }
  });

  it("rotula como Movimento exatamente o que passa do limiar de 1,2 m/s²", () => {
    // O rotulo e a intensidade nao podem se contradizer: seria justamente o
    // defeito que o DATA-02 corrigiu, reintroduzido em dado de demonstracao.
    for (const l of leituras) {
      const valor = intensidade(l)!;
      if (ehMovimento(l.status)) expect(valor).toBeGreaterThan(1.2);
      else expect(valor).toBeLessThanOrEqual(1.2);
    }
  });
});

describe("a noite gerada produz um dashboard apresentavel", () => {
  const metricas = calcularMetricas(gerarNoiteDemo());

  it("tem eventos suficientes para o grafico nao ficar plano", () => {
    expect(metricas.eventosDeMovimento).toBeGreaterThanOrEqual(5);
  });

  it("tem repouso predominante, como uma noite real", () => {
    const fracao = metricas.eventosDeMovimento / metricas.totalLeituras;
    expect(fracao).toBeLessThan(0.35);
  });

  it("tem um periodo longo sem movimento para o card mostrar algo util", () => {
    expect(metricas.maiorPeriodoSemMovimentoMs).toBeGreaterThan(30 * 60_000);
  });
});
