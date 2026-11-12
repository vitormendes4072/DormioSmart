import { Moon, Sun } from "lucide-react";

import { useTema } from "../hooks/useTema";
import { estaEmModoDemo } from "../lib/demo";

export function BarraDoWorkspace({ secao }: { secao: string }) {
  const { aplicado, definirPreferencia } = useTema();
  const escuro = aplicado === "dark";

  return (
    <div className="mb-6 flex items-center justify-between gap-3">
      <p className="text-[10px] text-muted-foreground">
        Smart Dormio <span className="mx-2">/</span> {secao}
      </p>
      <div className="flex items-center gap-2">
        {estaEmModoDemo() && (
          <span className="rounded-full bg-amber-500/15 px-2.5 py-1.5 text-[9px] font-bold uppercase tracking-wide text-amber-800 dark:text-amber-300">
            <span aria-hidden="true">● </span> Dados de demonstração
          </span>
        )}
        <button
          type="button"
          aria-label={escuro ? "Ativar tema claro" : "Ativar tema escuro"}
          onClick={() => definirPreferencia(escuro ? "claro" : "escuro")}
          className="grid size-9 shrink-0 place-items-center rounded-xl border border-border bg-card text-muted-foreground hover:text-primary"
        >
          {escuro ? <Sun className="size-4" aria-hidden /> : <Moon className="size-4" aria-hidden />}
        </button>
      </div>
    </div>
  );
}
