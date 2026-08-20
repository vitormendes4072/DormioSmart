/**
 * Preferencia de tema (BRAND-01).
 *
 * Sao tres opcoes para o usuario — claro, escuro e sistema — mas apenas DUAS
 * chegam ao CSS: o `data-theme` na raiz e sempre "light" ou "dark". "sistema"
 * e resolvido aqui, o que mantem o CSS simples (sem media query duplicando
 * tokens) e permite alternar sem recarregar.
 */

export type PreferenciaDeTema = "claro" | "escuro" | "sistema";
export type TemaAplicado = "light" | "dark";

export const CHAVE_ARMAZENAMENTO = "dormio-tema";

const PREFERENCIAS: PreferenciaDeTema[] = ["claro", "escuro", "sistema"];

export function ehPreferenciaValida(valor: unknown): valor is PreferenciaDeTema {
  return typeof valor === "string" && (PREFERENCIAS as string[]).includes(valor);
}

/** Le a preferencia salva. Qualquer valor estranho vira "sistema". */
export function lerPreferencia(armazenamento: Pick<Storage, "getItem">): PreferenciaDeTema {
  try {
    const salvo = armazenamento.getItem(CHAVE_ARMAZENAMENTO);
    return ehPreferenciaValida(salvo) ? salvo : "sistema";
  } catch {
    // localStorage pode lancar em navegacao privada ou com cookies bloqueados.
    // Preferencia e conforto, nao funcionalidade: cair no padrao e suficiente.
    return "sistema";
  }
}

export function salvarPreferencia(
  armazenamento: Pick<Storage, "setItem">,
  preferencia: PreferenciaDeTema,
) {
  try {
    armazenamento.setItem(CHAVE_ARMAZENAMENTO, preferencia);
  } catch {
    // idem: falhar em salvar nao pode quebrar a troca de tema na tela
  }
}

/** Converte a preferencia no tema que de fato vai para o `data-theme`. */
export function resolverTema(
  preferencia: PreferenciaDeTema,
  sistemaPrefereEscuro: boolean,
): TemaAplicado {
  if (preferencia === "claro") return "light";
  if (preferencia === "escuro") return "dark";
  return sistemaPrefereEscuro ? "dark" : "light";
}

export function aplicarTema(tema: TemaAplicado, raiz: HTMLElement) {
  raiz.dataset.theme = tema;
}
