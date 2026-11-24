import { useId, type ReactNode } from "react";

export const SUPERFICIE_DO_CARTAO_DE_REGISTRO = "rounded-2xl border border-border bg-card";

export function EtiquetaDeRegistro({ children, cor = "text-primary" }: {
  children: ReactNode;
  cor?: string;
}) {
  return (
    <span className={`wrap-anywhere text-[11px] font-extrabold uppercase tracking-wider ${cor}`}>
      {children}
    </span>
  );
}

export function CartaoEmDestaque({ rotulo, valor, children }: {
  rotulo: string;
  valor: string;
  children?: ReactNode;
}) {
  const id = useId();
  return (
    <div
      role="group"
      aria-labelledby={id}
      className="relative overflow-hidden rounded-2xl border border-(color:--sessao-destaque-borda) bg-(image:--sessao-destaque-fundo) p-4 text-white shadow-md sm:p-5"
    >
      <span aria-hidden="true" className="pointer-events-none absolute -top-20 -right-10 size-44 rounded-full bg-(image:--sessao-destaque-brilho)" />
      <p id={id} className="text-[11px] font-extrabold uppercase tracking-widest text-(color:--sessao-destaque-rotulo)">
        {rotulo}
      </p>
      <p className="mt-1">
        <strong className="block text-4xl leading-tight font-extrabold tracking-tight sm:text-[42px]">
          {valor}
        </strong>
        {children && (
          <span className="block text-sm text-(color:--sessao-destaque-legenda)">
            {" "}{children}
          </span>
        )}
      </p>
    </div>
  );
}

export function CartaoDeMetrica({ valor, children }: { valor: string | number; children: ReactNode }) {
  return (
    <li className={`${SUPERFICIE_DO_CARTAO_DE_REGISTRO} min-w-0 space-y-1.5 p-2.5 text-xs leading-snug text-muted-foreground sm:p-4 sm:text-sm`}>
      <strong className="block text-xl leading-tight font-extrabold tracking-tight text-foreground sm:text-2xl">
        {valor}
      </strong>
      {children}
    </li>
  );
}
