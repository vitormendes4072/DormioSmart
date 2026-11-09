import { describe, expect, it } from "vitest";

import type { RespostaDoLote } from "./coleta";
import { ErroDeIngestao } from "./coleta";
import { type FonteDaNoite, contarRestantes, enviarNoites, prefixoResolvido } from "./envioDaNoite";

/** O arquivo da noite em memoria, com a regra do nativo: o ponto so avanca. */
function fonte(noites: Record<string, number>, enviadas: Record<string, number> = {}) {
  const ponto: Record<string, number> = { ...enviadas };
  const linha = (arquivo: string, i: number) => JSON.stringify({ arquivo, epoca: i });
  const f: FonteDaNoite & { ponto: Record<string, number>; leituras: number } = {
    ponto,
    leituras: 0,
    noites: async () => ({
      noites: Object.entries(noites).map(([arquivo, epocas]) => ({ arquivo, epocas, enviadas: ponto[arquivo] ?? 0 })),
    }),
    lerEpocas: async ({ arquivo, de }) => {
      f.leituras++;
      const fim = Math.min(noites[arquivo], de + 60);
      return { epocas: Array.from({ length: Math.max(0, fim - de) }, (_, k) => linha(arquivo, de + k)) };
    },
    marcarEnviadas: async ({ arquivo, ate }) => {
      ponto[arquivo] = Math.min(noites[arquivo], Math.max(ponto[arquivo] ?? 0, ate));
      return { enviadas: ponto[arquivo] };
    },
  };
  return f;
}

/** Um servidor que deduplica por (arquivo, epoca), como a migracao 011. */
function servidor(regra: (leitura: { arquivo: string; epoca: number }, i: number) => "aceita" | "rejeitada" | "pendente" = () => "aceita") {
  const gravadas = new Set<string>();
  const lotes: number[] = [];
  const enviar = async (leituras: object[]): Promise<RespostaDoLote> => {
    lotes.push(leituras.length);
    const r: RespostaDoLote = { aceitas: [], rejeitadas: [], pendentes: [] };
    for (let i = 0; i < leituras.length; i++) {
      const l = leituras[i] as { arquivo: string; epoca: number };
      const d = regra(l, i);
      if (d === "pendente") {
        r.pendentes.push(...Array.from({ length: leituras.length - i }, (_, k) => i + k));
        break;
      }
      if (d === "rejeitada") r.rejeitadas.push({ indice: i, erro: "campo total fora da faixa" });
      else {
        gravadas.add(`${l.arquivo}#${l.epoca}`);
        r.aceitas.push(i);
      }
    }
    return r;
  };
  return { enviar, gravadas, lotes };
}

describe("prefixoResolvido (APP-02, etapa 3)", () => {
  it("conta aceitas e rejeitadas do comeco ate a primeira pendente", () => {
    expect(prefixoResolvido({ aceitas: [0, 1, 3], rejeitadas: [{ indice: 2, erro: "x" }], pendentes: [4, 5] }, 6)).toBe(4);
    expect(prefixoResolvido({ aceitas: [1, 2], rejeitadas: [], pendentes: [0] }, 3)).toBe(0);
    expect(prefixoResolvido({ aceitas: [0, 1, 2], rejeitadas: [], pendentes: [] }, 3)).toBe(3);
  });
});

describe("enviarNoites (APP-02, etapa 3)", () => {
  it("manda a noite inteira em lotes de 60 e marca tudo", async () => {
    const f = fonte({ "noite-1.jsonl": 130 });
    const s = servidor();
    const r = await enviarNoites(f, s.enviar);
    expect(s.lotes).toEqual([60, 60, 10]);
    expect(f.ponto["noite-1.jsonl"]).toBe(130);
    expect(r).toEqual({ confirmadas: 130, rejeitadas: 0, primeiraRejeicao: null, restantes: 0, erro: null });
    expect(s.gravadas.size).toBe(130);
  });

  it("continua de onde parou, sem reenviar o que ja foi confirmado", async () => {
    const f = fonte({ "noite-1.jsonl": 100 }, { "noite-1.jsonl": 70 });
    const s = servidor();
    const r = await enviarNoites(f, s.enviar);
    expect(s.lotes).toEqual([30]);
    expect(r.confirmadas).toBe(30);
  });

  it("pendente no meio: o ponto para antes dela, e nada se perde", async () => {
    const f = fonte({ "noite-1.jsonl": 100 });
    let falhou = false;
    const s = servidor((l) => (!falhou && l.epoca === 25 ? ((falhou = true), "pendente") : "aceita"));
    const r = await enviarNoites(f, s.enviar);
    expect(f.ponto["noite-1.jsonl"]).toBe(25);
    expect(r.restantes).toBe(75);
    expect(r.erro).toMatch(/35 épocas ficaram pendentes/);
    // A proxima tentativa termina a noite.
    const r2 = await enviarNoites(f, s.enviar);
    expect(f.ponto["noite-1.jsonl"]).toBe(100);
    expect(r2.restantes).toBe(0);
    expect(s.gravadas.size).toBe(100);
  });

  it("rejeitada e resolvida: o envio segue, e o motivo e contado", async () => {
    const f = fonte({ "noite-1.jsonl": 10 });
    const s = servidor((l) => (l.epoca === 3 || l.epoca === 7 ? "rejeitada" : "aceita"));
    const r = await enviarNoites(f, s.enviar);
    expect(f.ponto["noite-1.jsonl"]).toBe(10);
    expect(r.rejeitadas).toBe(2);
    expect(r.primeiraRejeicao).toBe("campo total fora da faixa");
    expect(r.erro).toBeNull();
  });

  it("sessao vencida ou sem rede: nada e marcado", async () => {
    for (const status of [401, 0]) {
      const f = fonte({ "noite-1.jsonl": 40 });
      const r = await enviarNoites(f, async () => {
        throw new ErroDeIngestao(status === 401 ? "Sua sessao expirou." : "Sem conexao.", status);
      });
      expect(f.ponto["noite-1.jsonl"] ?? 0).toBe(0);
      expect(r.confirmadas).toBe(0);
      expect(r.restantes).toBe(40);
      expect(r.erro).not.toBeNull();
    }
  });

  it("queda depois de gravar e antes de marcar: o reenvio e deduplicado", async () => {
    const f = fonte({ "noite-1.jsonl": 60 });
    const s = servidor();
    // O servidor grava, mas a resposta se perde.
    let primeira = true;
    const r = await enviarNoites(f, async (l) => {
      const resp = await s.enviar(l);
      if (primeira) {
        primeira = false;
        throw new ErroDeIngestao("Sem conexao.", 0);
      }
      return resp;
    });
    expect(r.confirmadas).toBe(0);
    await enviarNoites(f, s.enviar);
    expect(f.ponto["noite-1.jsonl"]).toBe(60);
    expect(s.gravadas.size).toBe(60);
  });

  it("varias noites, da mais antiga para a mais nova", async () => {
    const f = fonte({ "noite-1.jsonl": 5, "noite-2.jsonl": 3 });
    const vistas: string[] = [];
    const s = servidor((l) => {
      vistas.push(l.arquivo);
      return "aceita";
    });
    await enviarNoites(f, s.enviar);
    expect(vistas).toEqual([...Array(5).fill("noite-1.jsonl"), ...Array(3).fill("noite-2.jsonl")]);
    expect(await contarRestantes(f)).toBe(0);
  });

  it("noite ja toda enviada nao gera requisicao", async () => {
    const f = fonte({ "noite-1.jsonl": 20 }, { "noite-1.jsonl": 20 });
    const s = servidor();
    await enviarNoites(f, s.enviar);
    expect(s.lotes).toEqual([]);
    expect(f.leituras).toBe(0);
  });
});
