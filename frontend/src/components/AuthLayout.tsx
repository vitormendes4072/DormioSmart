import { Moon } from "lucide-react";
import type { ReactNode } from "react";

import { NOME_PRODUTO } from "../lib/ui";

/** Casca compartilhada de login e cadastro — as duas telas do protótipo
 *  repetiam o mesmo cabeçalho e os mesmos borrões de fundo. */
export function AuthLayout({
  subtitulo,
  children,
}: {
  subtitulo: string;
  children: ReactNode;
}) {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4 relative overflow-hidden">
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] max-w-[100vw] rounded-full bg-primary/8 blur-3xl pointer-events-none" />
      <div className="absolute bottom-0 right-0 w-72 h-72 rounded-full bg-accent/5 blur-3xl pointer-events-none" />

      <div className="relative w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-primary/20 border border-primary/20 mb-4">
            <Moon className="w-7 h-7 text-primary" />
          </div>
          <h1 className="text-2xl font-semibold text-foreground tracking-tight">
            {NOME_PRODUTO}
          </h1>
          <p className="text-sm text-muted-foreground mt-1">{subtitulo}</p>
        </div>

        <div className="bg-card border border-border rounded-2xl p-6 sm:p-7 space-y-5">
          {children}
        </div>
      </div>
    </div>
  );
}
