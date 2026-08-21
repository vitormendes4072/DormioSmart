import type { ReactNode } from "react";

/**
 * Elementos de blueprint — a assinatura visual da Dormio Labs (BRAND-01).
 *
 * A identidade do perfil não é só "azul sobre branco": é a estética de
 * desenho técnico — molduras de linha fina, marcações de canto, rótulos de
 * seção numerados. É isso que diferencia a marca de qualquer outro app azul.
 *
 * Vivem aqui, e não espalhados pelas telas, para que a linguagem seja
 * consistente e trocável num lugar só.
 */

/** Marcações de canto, como as de um desenho técnico. */
function Cantos() {
  const base = "absolute w-2.5 h-2.5 border-primary/40 pointer-events-none";
  return (
    <>
      <span className={`${base} top-0 left-0 border-t border-l`} />
      <span className={`${base} top-0 right-0 border-t border-r`} />
      <span className={`${base} bottom-0 left-0 border-b border-l`} />
      <span className={`${base} bottom-0 right-0 border-b border-r`} />
    </>
  );
}

/** Moldura de linha fina com marcações nos cantos. */
export function Moldura({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`relative border border-border/70 p-5 sm:p-6 ${className}`}>
      <Cantos />
      {children}
    </div>
  );
}

/** Rótulo numerado de seção, como "SLIDE 01" nos posts da marca. */
export function RotuloDeSecao({ numero, texto }: { numero: string; texto: string }) {
  return (
    <div className="flex items-center gap-3 mb-3">
      <span className="font-mono text-xs text-primary tracking-widest">{numero}</span>
      <span className="h-px flex-1 bg-border" />
      <span className="font-mono text-xs text-muted-foreground tracking-widest uppercase">
        {texto}
      </span>
    </div>
  );
}

/** Linha de cota, como em desenho técnico — usada como separador. */
export function LinhaDeCota() {
  return (
    <div className="flex items-center gap-2 text-primary/30" aria-hidden>
      <span className="w-px h-2 bg-current" />
      <span className="h-px flex-1 bg-current" />
      <span className="w-px h-2 bg-current" />
    </div>
  );
}
