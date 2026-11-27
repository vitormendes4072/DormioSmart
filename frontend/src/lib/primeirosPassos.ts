function chaveDaPreferencia(conta: string) {
  return "dormio-primeiros-passos-" + conta;
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
