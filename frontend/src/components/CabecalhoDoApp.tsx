import { useLocation } from "react-router";

import { itensDeNavegacao } from "./nav";

/** O nome da tela, pela rota, entre os destinos da barra; null fora deles. */
export function secaoDaRota(caminho: string, nativo?: boolean): string | null {
  const item = itensDeNavegacao(nativo).find(({ to }) => caminho === to || caminho.startsWith(`${to}/`));
  return item ? item.label : null;
}

/**
 * O cabeçalho das telas no celular (UI-43, etapa 1): a marca e, embaixo, o nome da tela em
 * maiúsculas, como no celular de exemplo da landing. Só abaixo de `md`; no computador fica o caminho
 * "Smart Dormio / tela" da `BarraDoWorkspace`, que no celular se esconde para não repetir.
 */
export function CabecalhoDoApp({ nativo }: { nativo?: boolean }) {
  const { pathname } = useLocation();
  const secao = secaoDaRota(pathname, nativo);
  return (
    <header className="-mx-4 mb-5 flex items-center gap-3 border-b border-border px-4 pb-3 md:hidden">
      <img src="/icone-192.png" alt="" width={36} height={36} className="size-9 rounded-xl" />
      <div className="min-w-0 leading-tight">
        <p className="text-sm font-extrabold text-foreground">Smart Dormio</p>
        {secao ? (
          <p className="truncate text-[10px] font-bold uppercase tracking-[0.12em] text-primary">{secao}</p>
        ) : null}
      </div>
    </header>
  );
}
