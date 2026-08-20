import { describe, expect, it } from "vitest";

import type { LeituraSono } from "../types/sleep";
import { COLUNAS, gerarCsv, nomeDoArquivo } from "./exportar";

const leitura = (extra: Partial<LeituraSono> = {}): LeituraSono => ({
  created_at: "2026-08-19T03:00:00.000Z",
  movimento_total: 9.81,
  temp: 32,
  status: "Repouso",
  ...extra,
});

describe("gerarCsv", () => {
  it("comeca pelo cabecalho com todas as colunas", () => {
    const linhas = gerarCsv([]).split("\r\n");
    expect(linhas[0]).toBe(COLUNAS.join(","));
  });

  it("gera so o cabecalho quando nao ha leitura", () => {
    expect(gerarCsv([]).split("\r\n")).toHaveLength(1);
  });

  it("usa CRLF, que e o que o Excel espera", () => {
    expect(gerarCsv([leitura()])).toContain("\r\n");
  });

  it("inclui a intensidade derivada, que e a coluna util para actigrafia", () => {
    const csv = gerarCsv([leitura({ movimento_total: 11.81 })]);
    expect(csv).toContain("2.0000");
  });

  it("marca movimento com 1 e repouso com 0", () => {
    const csv = gerarCsv([leitura({ status: "Movimento" }), leitura({ status: "Repouso" })]);
    const [, primeira, segunda] = csv.split("\r\n");
    expect(primeira.endsWith(",1")).toBe(true);
    expect(segunda.endsWith(",0")).toBe(true);
  });

  it("reconhece o rotulo legado ao marcar movimento", () => {
    const csv = gerarCsv([leitura({ status: "Movimento Detectado!" })]);
    expect(csv.split("\r\n")[1].endsWith(",1")).toBe(true);
  });

  it("deixa a celula vazia quando o campo e nulo, sem escrever 'null'", () => {
    const csv = gerarCsv([leitura({ movimento_total: null, temp: null, status: null })]);
    const linha = csv.split("\r\n")[1];
    expect(linha).not.toContain("null");
    expect(linha).toBe("2026-08-19T03:00:00.000Z,,,,,0");
  });

  it("escapa campo com virgula para nao desalinhar as colunas", () => {
    const csv = gerarCsv([leitura({ status: "Movimento, forte" })]);
    expect(csv).toContain('"Movimento, forte"');
    // 6 colunas: o campo escapado nao pode ter virado duas.
    expect(csv.split("\r\n")[1].split(",").length).toBeGreaterThan(6);
    expect(csv).toMatch(/"Movimento, forte"/);
  });

  it("duplica aspas dentro do campo, conforme a RFC 4180", () => {
    const csv = gerarCsv([leitura({ status: 'diz "movimento"' })]);
    expect(csv).toContain('"diz ""movimento"""');
  });

  it("escapa quebra de linha embutida", () => {
    const csv = gerarCsv([leitura({ status: "linha1\nlinha2" })]);
    expect(csv).toContain('"linha1\nlinha2"');
  });
});

describe("nomeDoArquivo", () => {
  it("carrega data e hora para nao sobrescrever exportacao anterior", () => {
    const nome = nomeDoArquivo(new Date(2026, 7, 19, 22, 45));
    expect(nome).toBe("dormio-smart-leituras-2026-08-19-2245.csv");
  });

  it("preenche mes e dia com zero a esquerda", () => {
    expect(nomeDoArquivo(new Date(2026, 0, 5, 9, 7))).toContain("2026-01-05-0907");
  });
});
