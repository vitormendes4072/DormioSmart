import { lazy, type ComponentType } from "react";

function FalhaAoCarregarRota() {
  return (
    <div className="p-6">
      <p role="alert">Não foi possível carregar esta página.</p>
      <button type="button" className="mt-2 font-semibold text-primary" onClick={() => window.location.reload()}>
        Recarregar
      </button>
    </div>
  );
}

export async function carregarModulo<T>(
  carregar: () => Promise<T>,
  chave: string,
  armazenamento: Pick<Storage, "getItem" | "setItem" | "removeItem">,
  recarregar: () => void,
): Promise<T | { default: typeof FalhaAoCarregarRota }> {
  let modulo: T;
  try {
    modulo = await carregar();
  } catch {
    try {
      if (!armazenamento.getItem(chave)) {
        armazenamento.setItem(chave, "1");
        recarregar();
      }
    } catch {
      // Sem armazenamento, a recarga automática poderia entrar em laço.
    }
    return { default: FalhaAoCarregarRota };
  }
  try {
    armazenamento.removeItem(chave);
  } catch {
    // A rota carregada funciona mesmo com armazenamento bloqueado.
  }
  return modulo;
}

export function rotaSobDemanda(nome: string, carregar: () => Promise<{ default: ComponentType }>) {
  return lazy<ComponentType>(() => carregarModulo(carregar, `dormio:recarga:${nome}`, {
    getItem: (chave) => window.sessionStorage.getItem(chave),
    setItem: (chave, valor) => window.sessionStorage.setItem(chave, valor),
    removeItem: (chave) => window.sessionStorage.removeItem(chave),
  }, () => window.location.reload()));
}
