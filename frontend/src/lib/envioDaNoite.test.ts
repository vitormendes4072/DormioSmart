import { describe, expect, it, vi } from "vitest";

import type { RespostaDoLote } from "./coleta";
import { ErroDeIngestao, PRAZO_DO_LOTE_MS, enviarLote } from "./coleta";
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

  it("relê a fila depois do envio em curso e inclui uma noite que acabou durante a espera", async () => {
    const noites = { "noite-1.jsonl": 2 };
    const f = fonte(noites);
    let liberar!: () => void;
    const resposta = new Promise<void>((resolve) => { liberar = resolve; });
    let iniciou!: () => void;
    const emCurso = new Promise<void>((resolve) => { iniciou = resolve; });
    const primeiro = enviarNoites(f, async () => {
      iniciou();
      await resposta;
      return { aceitas: [0, 1], rejeitadas: [], pendentes: [] };
    });
    await emCurso;

    const segundoLote: object[][] = [];
    const segundo = enviarNoites(f, async (leituras) => {
      segundoLote.push(leituras);
      return { aceitas: leituras.map((_, i) => i), rejeitadas: [], pendentes: [] };
    });
    Object.assign(noites, { "noite-2.jsonl": 1 });
    liberar();
    await Promise.all([primeiro, segundo]);

    expect(segundoLote).toEqual([[{ arquivo: "noite-2.jsonl", epoca: 0 }]]);
    expect(f.ponto).toEqual({ "noite-1.jsonl": 2, "noite-2.jsonl": 1 });
  });

  it("continua de onde parou, sem reenviar o que ja foi confirmado", async () => {
    const f = fonte({ "noite-1.jsonl": 100 }, { "noite-1.jsonl": 70 });
    const s = servidor();
    const r = await enviarNoites(f, s.enviar);
    expect(s.lotes).toEqual([30]);
    expect(r.confirmadas).toBe(30);
  });

  it("pendente no meio, com avanco: o laco segue do ponto novo, e nada se perde", async () => {
    const f = fonte({ "noite-1.jsonl": 100 });
    let falhou = false;
    const s = servidor((l) => (!falhou && l.epoca === 25 ? ((falhou = true), "pendente") : "aceita"));
    const r = await enviarNoites(f, s.enviar);
    // O primeiro lote resolveu 25; o laco rele a partir da 25, sem pular nenhuma.
    expect(s.lotes).toEqual([60, 60, 15]);
    expect(f.ponto["noite-1.jsonl"]).toBe(100);
    expect(r).toEqual({ confirmadas: 100, rejeitadas: 0, primeiraRejeicao: null, restantes: 0, erro: null });
    expect(s.gravadas.size).toBe(100);
  });

  // APP-10: o servidor para o lote aos 6 s. Na producao (09/11) cabiam 13 de 60.
  it("servidor que so grava 13 por requisicao: a noite de 960 sobe inteira, sozinha", async () => {
    const f = fonte({ "noite-1.jsonl": 960 });
    const s = servidor((_, i) => (i < 13 ? "aceita" : "pendente"));
    const passos: number[] = [];
    const r = await enviarNoites(f, s.enviar, (p) => {
      expect(p.total).toBe(960);
      passos.push(p.confirmadas);
    });
    expect(f.ponto["noite-1.jsonl"]).toBe(960);
    expect(s.gravadas.size).toBe(960);
    expect(r).toEqual({ confirmadas: 960, rejeitadas: 0, primeiraRejeicao: null, restantes: 0, erro: null });
    expect(s.lotes.length).toBe(Math.ceil(960 / 13));
    // O progresso so cresce, de 13 em 13, ate o total.
    expect(passos[0]).toBe(13);
    expect(passos[passos.length - 1]).toBe(960);
    expect(passos.every((v, i) => i === 0 || v > passos[i - 1])).toBe(true);
  });

  it("requisicao sem nenhum avanco: para na primeira, e o ponto fica onde estava", async () => {
    const f = fonte({ "noite-1.jsonl": 100 }, { "noite-1.jsonl": 20 });
    const s = servidor(() => "pendente");
    const r = await enviarNoites(f, s.enviar);
    expect(s.lotes).toEqual([60]);
    expect(f.ponto["noite-1.jsonl"]).toBe(20);
    expect(r.confirmadas).toBe(0);
    expect(r.restantes).toBe(80);
    expect(r.erro).toMatch(/60 épocas ficaram pendentes/);
  });

  it("o servidor para de avancar no meio: o laco para ali, com o que ja entrou marcado", async () => {
    const f = fonte({ "noite-1.jsonl": 100 });
    // As 26 primeiras entram, de 13 em 13; dali em diante, nada.
    const s = servidor((l, i) => (l.epoca < 26 && i < 13 ? "aceita" : "pendente"));
    const r = await enviarNoites(f, s.enviar);
    expect(s.lotes).toEqual([60, 60, 60]);
    expect(f.ponto["noite-1.jsonl"]).toBe(26);
    expect(r.confirmadas).toBe(26);
    expect(r.erro).toMatch(/ficaram pendentes/);
  });

  it("o aparelho nao move o ponto: para, em vez de reenviar o mesmo lote para sempre", async () => {
    const f = fonte({ "noite-1.jsonl": 100 });
    f.marcarEnviadas = async () => ({ enviadas: 0 });
    const s = servidor();
    const r = await enviarNoites(f, s.enviar);
    expect(s.lotes).toEqual([60]);
    expect(r.erro).not.toBeNull();
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

it("sincroniza a gravação normal e a legada, mas nunca lê a de teste", async () => {
  const noites = [
    { arquivo: "teste", epocas: 1, enviadas: 0, teste: true },
    { arquivo: "normal", epocas: 1, enviadas: 0, teste: false },
    { arquivo: "legada", epocas: 1, enviadas: 0 },
  ];
  const fonte: FonteDaNoite = {
    noites: async () => ({ noites }),
    lerEpocas: vi.fn(async ({ arquivo }) => ({ epocas: [JSON.stringify({ arquivo })] })),
    marcarEnviadas: vi.fn(async ({ arquivo, ate }) => {
      noites.find((n) => n.arquivo === arquivo)!.enviadas = ate;
      return { enviadas: ate };
    }),
  };
  expect(await contarRestantes(fonte)).toBe(2);
  const enviar = vi.fn(async () => ({ aceitas: [0], rejeitadas: [], pendentes: [] }));
  expect((await enviarNoites(fonte, enviar)).restantes).toBe(0);
  expect(enviar.mock.calls).toEqual([[ [{ arquivo: "normal" }] ], [ [{ arquivo: "legada" }] ]]);
  expect(fonte.lerEpocas).not.toHaveBeenCalledWith({ arquivo: "teste", de: 0 });
});

describe("a fila de envios por aparelho (APP-16)", () => {
  it("uma tentativa feita durante um envio que falhou no aparelho ainda envia e marca", async () => {
    const f = fonte({ "noite-1.jsonl": 2 });
    const marcar = f.marcarEnviadas;
    let liberar!: () => void;
    const segura = new Promise<void>((resolve) => { liberar = resolve; });
    let primeira = true;
    f.marcarEnviadas = async (args) => {
      if (primeira) {
        primeira = false;
        await segura;
        throw new Error("o plugin falhou ao gravar o ponto");
      }
      return marcar(args);
    };
    const s = servidor();
    const primeiro = enviarNoites(f, s.enviar);
    await vi.waitFor(() => expect(s.lotes).toEqual([2]));
    const segundo = enviarNoites(f, s.enviar);
    liberar();
    await expect(primeiro).rejects.toThrow(/plugin falhou/);
    const r = await segundo;
    expect({ lotes: s.lotes, ponto: f.ponto, restantes: r.restantes })
      .toEqual({ lotes: [2, 2], ponto: { "noite-1.jsonl": 2 }, restantes: 0 });
  });

  it("um lote que não responde não prende a tentativa seguinte além do prazo", async () => {
    vi.useFakeTimers();
    try {
      const f = fonte({ "noite-1.jsonl": 1 });
      const pedidos: number[] = [];
      vi.stubGlobal("fetch", (_u: string, init: RequestInit) => {
        pedidos.push(Date.now());
        if (pedidos.length === 1) {
          return new Promise<never>((_, rejeitar) => {
            init.signal?.addEventListener("abort", () => rejeitar(new DOMException("abortado", "AbortError")));
          });
        }
        return Promise.resolve({
          status: 200, json: async () => ({ aceitas: [0], rejeitadas: [], pendentes: [] }),
        } as unknown as Response);
      });
      const enviar = (leituras: object[]) => enviarLote(leituras, "aparelho", "jwt");
      const primeiro = enviarNoites(f, enviar);
      await vi.advanceTimersByTimeAsync(0);
      const segundo = enviarNoites(f, enviar);
      await vi.advanceTimersByTimeAsync(PRAZO_DO_LOTE_MS - 1);
      expect(pedidos, "a segunda espera a primeira").toHaveLength(1);
      await vi.advanceTimersByTimeAsync(1);
      expect((await primeiro).erro).toMatch(/a tempo/);
      expect((await segundo).restantes).toBe(0);
      expect(pedidos).toHaveLength(2);
      expect(f.ponto).toEqual({ "noite-1.jsonl": 1 });
    } finally {
      vi.useRealTimers();
      vi.unstubAllGlobals();
    }
  });
});
