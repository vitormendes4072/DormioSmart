function chaveDaPreferencia(conta: string) {
  return "dormio-primeiros-passos-" + conta;
}

export type PassoDaJornada = "inicio" | "escolha" | "conectar" | "bateria" | "notificacao" | "preparado" |
  "codigo" | "espera" | "sinal" | "meta" | "fim";

export type Jornada = {
  passo: PassoDaJornada;
  caminho?: "celular" | "travesseiro";
  aparelho?: string;
};

const passos: readonly PassoDaJornada[] = [
  "inicio", "escolha", "conectar", "bateria", "notificacao", "preparado",
  "codigo", "espera", "sinal", "meta", "fim",
];

function chaveDaJornada(conta: string) {
  return "dormio-jornada-" + conta;
}

export function lerJornada(conta: string): Jornada | null {
  try {
    const dados = JSON.parse(localStorage.getItem(chaveDaJornada(conta)) ?? "null") as Partial<Jornada> | null;
    if (!dados?.passo || !passos.includes(dados.passo)) return null;
    return {
      passo: dados.passo,
      caminho: dados.caminho === "celular" || dados.caminho === "travesseiro" ? dados.caminho : undefined,
      aparelho: typeof dados.aparelho === "string" ? dados.aparelho : undefined,
    };
  } catch {
    return null;
  }
}

export function guardarJornada(conta: string, jornada: Jornada): boolean {
  try {
    localStorage.setItem(chaveDaJornada(conta), JSON.stringify(jornada));
    return true;
  } catch {
    return false;
  }
}

export function estadoDoAviso(conta: string): string | null {
  try {
    return localStorage.getItem("dormio-primeira-sessao-" + conta);
  } catch {
    return null;
  }
}

export function anotarAviso(conta: string, estado: "aguardando" | "mostrado"): boolean {
  try {
    localStorage.setItem("dormio-primeira-sessao-" + conta, estado);
    return true;
  } catch {
    return false;
  }
}

export function guiaDispensado(conta: string | undefined) {
  try {
    return conta !== undefined && localStorage.getItem(chaveDaPreferencia(conta)) === "dispensado";
  } catch {
    return false;
  }
}

export function salvarPreferenciaDoGuia(conta: string | undefined, dispensado: boolean) {
  if (!conta) return;
  try {
    const chave = chaveDaPreferencia(conta);
    if (dispensado) localStorage.setItem(chave, "dispensado");
    else localStorage.removeItem(chave);
  } catch {
    // O painel pode continuar aberto com o armazenamento indisponível.
  }
}
