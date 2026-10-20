import { describe, expect, it } from "vitest";

import {
  TODOS_OS_DISPOSITIVOS,
  type Dispositivo,
  type TipoDeDispositivo,
  descreverDispositivo,
  descreverRecorte,
  precisaEscolherDispositivo,
  serieMisturaInstrumentos,
  serieMisturaTipos,
  tiposPresentes,
} from "./dispositivos";

function dispositivo(
  id: string,
  nome: string,
  revogado = false,
  tipo?: TipoDeDispositivo,
): Dispositivo {
  return {
    id,
    nome,
    ...(tipo ? { tipo } : {}),
    created_at: "2026-08-01T00:00:00Z",
    last_seen_at: null,
    revoked_at: revogado ? "2026-08-10T00:00:00Z" : null,
  };
}

const TRAVESSEIRO = dispositivo("a", "Travesseiro");
const CELULAR = dispositivo("b", "Celular");

describe("precisaEscolherDispositivo", () => {
  it("nao mostra seletor sem dispositivo nenhum", () => {
    expect(precisaEscolherDispositivo([])).toBe(false);
  });

  it("nao mostra seletor com um dispositivo so", () => {
    // Um controle com uma opcao e ruido — e e o caso de quase todo mundo hoje.
    expect(precisaEscolherDispositivo([TRAVESSEIRO])).toBe(false);
  });

  it("mostra seletor a partir de dois", () => {
    expect(precisaEscolherDispositivo([TRAVESSEIRO, CELULAR])).toBe(true);
  });
});

describe("serieMisturaInstrumentos", () => {
  it("avisa quando ha varios dispositivos e nenhum recorte", () => {
    // E o defeito que o DASH-05 conserta: travesseiro e celular medem o mesmo
    // movimento por acoplamentos diferentes. Empilhar sem dizer e desonesto.
    expect(serieMisturaInstrumentos([TRAVESSEIRO, CELULAR], null)).toBe(true);
  });

  it("nao avisa quando um dispositivo esta recortado", () => {
    expect(serieMisturaInstrumentos([TRAVESSEIRO, CELULAR], "a")).toBe(false);
  });

  it("nao avisa com um dispositivo so — nao ha o que misturar", () => {
    expect(serieMisturaInstrumentos([TRAVESSEIRO], null)).toBe(false);
  });

  it("trata o valor vazio do seletor como ausencia de recorte", () => {
    expect(serieMisturaInstrumentos([TRAVESSEIRO, CELULAR], TODOS_OS_DISPOSITIVOS)).toBe(true);
  });
});

// ── DASH-08 ──────────────────────────────────────────────────────────────

const ESP = dispositivo("a", "Quarto", false, "travesseiro");
const FONE = dispositivo("b", "Teste 2", false, "celular");
/** Pareado antes do DATA-05: a resposta nao traz `tipo`. */
const ANTIGO = dispositivo("c", "meu");

describe("descreverDispositivo", () => {
  it("junta o nome escolhido pelo usuario e a classe do instrumento", () => {
    // O nome sozinho — "Quarto", "Teste 2" — nao diz de que instrumento veio
    // a serie, e e ele que qualifica a medida.
    expect(descreverDispositivo(ESP)).toBe("Quarto · Travesseiro");
    expect(descreverDispositivo(FONE)).toBe("Teste 2 · Celular");
  });

  it("nao inventa o tipo do dispositivo pareado antes do DATA-05", () => {
    // Ali todo dispositivo era um ESP32, mas afirmar isso seria inventar.
    expect(descreverDispositivo(ANTIGO)).toBe("meu · Dispositivo");
  });
});

describe("descreverRecorte", () => {
  it("nomeia o recorte com nome e tipo", () => {
    expect(descreverRecorte([ESP, FONE], "b")).toBe("Teste 2 · Celular");
  });

  it("sem recorte, diz que sao todos", () => {
    expect(descreverRecorte([ESP, FONE], null)).toBe("Todos os dispositivos");
  });

  it("id fora da lista nao quebra a tela", () => {
    // Acontece se o dispositivo for apagado noutra aba com o painel aberto.
    // (Comentario herdado dos testes de `nomeDoDispositivo`, apagada em 20/10
    // com o `UI-16`: era a justificativa do rotulo, e o rotulo sobreviveu
    // aqui.)
    expect(descreverRecorte([ESP], "sumiu")).toBe("Dispositivo desconhecido");
  });
});

describe("tiposPresentes", () => {
  it("nao repete o tipo quando ha dois aparelhos da mesma classe", () => {
    expect(tiposPresentes([ESP, dispositivo("d", "Sala", false, "travesseiro")])).toEqual([
      "Travesseiro",
    ]);
  });

  it("usa ordem fixa, nao a ordem em que o banco devolveu", () => {
    // Sem isso o aviso na tela trocaria de redacao sozinho.
    expect(tiposPresentes([FONE, ESP])).toEqual(["Travesseiro", "Celular"]);
    expect(tiposPresentes([ESP, FONE])).toEqual(["Travesseiro", "Celular"]);
  });

  it("poe a classe desconhecida por ultimo, que e a menos informativa", () => {
    expect(tiposPresentes([ANTIGO, FONE])).toEqual(["Celular", "Dispositivo"]);
  });

  it("lista vazia nao produz tipo nenhum", () => {
    expect(tiposPresentes([])).toEqual([]);
  });
});

describe("serieMisturaTipos", () => {
  it("dois aparelhos da MESMA classe sao comparaveis entre si", () => {
    // `serieMisturaInstrumentos` avisaria aqui; este e mais estrito de
    // proposito — o que muda o significado dos numeros e a classe, nao a
    // contagem de aparelhos.
    const outro = dispositivo("d", "Sala", false, "travesseiro");
    expect(serieMisturaInstrumentos([ESP, outro], null)).toBe(true);
    expect(serieMisturaTipos([ESP, outro], null)).toBe(false);
  });

  it("travesseiro com celular e mistura de classes", () => {
    expect(serieMisturaTipos([ESP, FONE], null)).toBe(true);
  });

  it("com recorte ativo nao ha mistura, qualquer que seja a lista", () => {
    expect(serieMisturaTipos([ESP, FONE], "a")).toBe(false);
  });

  // O contrato que o `AvisoDeMistura` consome: um predicado decide se o aviso
  // APARECE, o outro se ele NOMEIA AS CLASSES. Se alguem trocar um predicado
  // pelo outro na tela, este teste e o unico lugar que explica a diferenca.
  //
  // ✏️ 19/10: o comentario anterior dizia que o componente "nao tem teste"
  // porque o projeto nao tinha testing-library. Isso mudou (`UI-17`,
  // `src/montagem.test.ts`), mas o AvisoDeMistura continua sem assercao de
  // render: ele e condicional, e exercitar as condicoes dele exige serie de
  // leitura construida — e o `UI-18`. Ou seja, o motivo da frase caiu e a
  // conclusao dela segue valendo, por outra razao.
  it("os dois predicados nao sao substituiveis um pelo outro", () => {
    const doisTravesseiros: Dispositivo[] = [ESP, dispositivo("d", "Sala", false, "travesseiro")];
    // Aparece o aviso, mas sem nomear classes: nomear diria "Travesseiro e
    // Travesseiro, que sao instrumentos diferentes", que e falso.
    expect(serieMisturaInstrumentos(doisTravesseiros, null)).toBe(true);
    expect(serieMisturaTipos(doisTravesseiros, null)).toBe(false);
    // Travesseiro com celular: aparece E nomeia.
    expect(serieMisturaInstrumentos([ESP, FONE], null)).toBe(true);
    expect(serieMisturaTipos([ESP, FONE], null)).toBe(true);
    // Um aparelho so: nao aparece, e por isso nomear nem se pergunta.
    expect(serieMisturaInstrumentos([ESP], null)).toBe(false);
    expect(serieMisturaTipos([ESP], null)).toBe(false);
  });
});
