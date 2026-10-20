/**
 * Dispositivos do usuário (AUTH-05).
 *
 * Um usuário tem muitos dispositivos; cada dispositivo tem um dono. O backend
 * resolve a posse pelo JWT, então nenhuma chamada daqui envia `user_id`.
 */
import { requisitarJson } from "./api";

/** Classe do instrumento (DATA-05). Nao e o nome: nome e escolha do usuario.
 *  O tipo e o que permite separar acoplamentos diferentes — um travesseiro
 *  mede perto da cabeca; um celular no colchao mede um corpo de massa alta,
 *  amortecido, e compartilhado com quem dorme do lado. */
export type TipoDeDispositivo = "travesseiro" | "celular";

export const TIPOS: { valor: TipoDeDispositivo; rotulo: string; ajuda: string }[] = [
  {
    valor: "travesseiro",
    rotulo: "Travesseiro",
    ajuda: "ESP32 com MPU6050 embarcado no travesseiro.",
  },
  {
    valor: "celular",
    rotulo: "Celular",
    ajuda: "Acelerometro do proprio aparelho, pela tela de coleta.",
  },
];

export type Dispositivo = {
  id: string;
  nome: string;
  /** Ausente nas respostas anteriores ao DATA-05. */
  tipo?: TipoDeDispositivo;
  created_at: string;
  last_seen_at: string | null;
  revoked_at: string | null;
};

/** Resposta do pareamento. `token` só existe aqui, nesta única resposta. */
export type Pareamento = {
  device: Dispositivo;
  token: string;
};

export const NOME_MAXIMO = 60;

export function listarDispositivos(): Promise<Dispositivo[]> {
  return requisitarJson<Dispositivo[]>("/api/devices");
}

export function parearDispositivo(
  nome: string,
  tipo: TipoDeDispositivo = "travesseiro",
): Promise<Pareamento> {
  return requisitarJson<Pareamento>("/api/devices", {
    method: "POST",
    body: JSON.stringify({ nome, tipo }),
  });
}

export function renomearDispositivo(id: string, nome: string): Promise<Dispositivo> {
  return requisitarJson<Dispositivo>(`/api/devices/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ nome }),
  });
}

export function revogarDispositivo(id: string): Promise<Dispositivo> {
  return requisitarJson<Dispositivo>(`/api/devices/${id}/revogar`, { method: "POST" });
}

export function estaAtivo(dispositivo: Dispositivo): boolean {
  return dispositivo.revoked_at === null;
}

/**
 * "nunca" quando o dispositivo ainda não enviou nada.
 *
 * Distinguir "nunca enviou" de "enviou faz tempo" é o que responde a pergunta
 * real do usuário: o pareamento funcionou?
 */
export function descreverUltimoContato(dispositivo: Dispositivo): string {
  if (!dispositivo.last_seen_at) return "nunca enviou dados";

  const quando = new Date(dispositivo.last_seen_at);
  if (Number.isNaN(quando.getTime())) return "data desconhecida";

  const minutos = Math.floor((Date.now() - quando.getTime()) / 60_000);
  if (minutos < 1) return "agora mesmo";
  if (minutos < 60) return `há ${minutos} min`;

  const horas = Math.floor(minutos / 60);
  if (horas < 24) return `há ${horas}h`;

  const dias = Math.floor(horas / 24);
  return dias === 1 ? "ontem" : `há ${dias} dias`;
}

/**
 * Escolha de instrumento no painel (DASH-05).
 *
 * ── POR QUE ISTO EXISTE ─────────────────────────────────────────────────
 *
 * Ate o DASH-05 a leitura filtrava so por dono. Quem pareasse dois
 * dispositivos recebia os dois **misturados na mesma serie e nas mesmas
 * metricas** — dois instrumentos plotados como um. Ninguem esbarrou porque so
 * existe um dispositivo no mundo.
 *
 * As funcoes abaixo sao puras para poderem ser testadas sem montar tela.
 */

/** Valor do seletor quando nenhum dispositivo esta recortado. */
export const TODOS_OS_DISPOSITIVOS = "";

/**
 * Vale mostrar o seletor?
 *
 * Com um dispositivo so — o caso do autor e o de qualquer pessoa comum — o
 * seletor seria um controle com uma opcao. Ruido.
 */
export function precisaEscolherDispositivo(dispositivos: Dispositivo[]): boolean {
  return dispositivos.length > 1;
}

/**
 * A serie exibida esta misturando instrumentos?
 *
 * Quando sim, a tela precisa DIZER isso. Um travesseiro e um celular medem o
 * mesmo fenomeno por acoplamentos diferentes; empilhar os dois numa linha sem
 * avisar e o mesmo problema de honestidade do tracado sintetico da landing.
 */
export function serieMisturaInstrumentos(
  dispositivos: Dispositivo[],
  selecionado: string | null,
): boolean {
  return !selecionado && dispositivos.length > 1;
}

/** Nome legivel do tipo, para exibir na lista de dispositivos. */
export function rotuloDoTipo(tipo: TipoDeDispositivo | undefined): string {
  // Ausente nas respostas anteriores ao DATA-05. Ali, todo dispositivo era um
  // ESP32 — mas afirmar isso seria inventar; "dispositivo" e o que se sabe.
  if (!tipo) return "Dispositivo";
  return TIPOS.find((t) => t.valor === tipo)?.rotulo ?? "Dispositivo";
}

// ── DASH-08: o painel diz de que INSTRUMENTO veio a serie ────────────────
//
// `devices.tipo` e gravado no pareamento desde o DATA-05 e nunca chegou a
// aparecer no painel. O seletor mostrava so o `nome`, que e texto livre
// escolhido pelo usuario: "Quarto", "Teste 2", "meu". Nada na tela dizia que
// duas series vieram de um ESP32 no travesseiro e de um celular no colchao.
//
// Isso importa porque os dois nao medem a mesma coisa. O travesseiro mede
// perto da cabeca; o celular mede um corpo de massa alta, amortecido e
// compartilhado com quem dorme do lado — e o limiar de 1,2 m/s2 nasceu do
// travesseiro (`DATA-06`, aberto). Enquanto a regua for uma so, dizer a
// origem e o minimo que a tela deve ao leitor.

/**
 * "Nome · Tipo", para o seletor e para o cabecalho.
 *
 * O nome vem primeiro porque e por ele que o usuario reconhece o aparelho; o
 * tipo vem depois porque e ele que qualifica a medida.
 */
export function descreverDispositivo(dispositivo: Dispositivo): string {
  return `${dispositivo.nome} · ${rotuloDoTipo(dispositivo.tipo)}`;
}

/** Como o cabecalho do painel nomeia o recorte atual. */
export function descreverRecorte(dispositivos: Dispositivo[], id: string | null): string {
  if (!id) return "Todos os dispositivos";
  const encontrado = dispositivos.find((d) => d.id === id);
  return encontrado ? descreverDispositivo(encontrado) : "Dispositivo desconhecido";
}

/**
 * Os tipos distintos presentes na lista, na ordem de `TIPOS`.
 *
 * Ordem fixa, e nao ordem de chegada: o aviso na tela nao pode trocar de
 * redacao ("celular e travesseiro" / "travesseiro e celular") conforme a
 * ordem em que o banco devolveu as linhas.
 */
export function tiposPresentes(dispositivos: Dispositivo[]): string[] {
  const presentes = new Set(dispositivos.map((d) => rotuloDoTipo(d.tipo)));
  const conhecidos = TIPOS.map((t) => t.rotulo).filter((r) => presentes.has(r));
  // "Dispositivo" (tipo ausente, pre-DATA-05) nao esta em TIPOS e entra por
  // ultimo — e a categoria menos informativa.
  return presentes.has("Dispositivo") ? [...conhecidos, "Dispositivo"] : conhecidos;
}

/**
 * A serie mistura CLASSES de instrumento diferentes?
 *
 * Mais forte que `serieMisturaInstrumentos`, que so pergunta se ha mais de um
 * aparelho. Dois travesseiros do mesmo tipo empilhados sao comparaveis entre
 * si; um travesseiro com um celular, nao — e e essa a mistura que muda o
 * significado dos numeros do painel.
 */
export function serieMisturaTipos(
  dispositivos: Dispositivo[],
  selecionado: string | null,
): boolean {
  return !selecionado && tiposPresentes(dispositivos).length > 1;
}
