import type { ReactNode } from "react";

import { useRevelacao } from "../hooks/useRevelacao";

/**
 * Envolve um bloco para que ele entre suavemente ao aparecer na tela (UI-15).
 *
 * `atraso` escalona elementos irmaos. O escalonamento e curto de proposito
 * — passa a sensacao de que a pagina se monta, sem virar espera.
 *
 * A logica toda vive em `useRevelacao`; isto e apenas o involucro para
 * quem nao precisa de um ref proprio.
 */
export function Revelar({
  children,
  atraso = 0,
  className = "",
}: {
  children: ReactNode;
  atraso?: number;
  className?: string;
}) {
  const ref = useRevelacao<HTMLDivElement>(atraso);
  return (
    <div ref={ref} className={className}>
      {children}
    </div>
  );
}
