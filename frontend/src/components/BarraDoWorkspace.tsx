import { Moon, Sun } from "lucide-react";
import { useOutletContext } from "react-router";

import type { useTema } from "../hooks/useTema";
import { estaEmModoDemo } from "../lib/demo";

export function BarraDoWorkspace({ secao }: { secao: string }) {
  const tema = useOutletContext<ReturnType<typeof useTema>>();

  return (
    <div className="mb-6 hidden items-center justify-between gap-3 md:flex">
      <p className="text-[10px] text-muted-foreground">
        Smart Dormio <span className="mx-2">/</span> {secao}
      </p>
      <ControlesDoWorkspace {...tema} />
    </div>
  );
}

export function ControlesDoWorkspace({
  aplicado, definirPreferencia,
}: Pick<ReturnType<typeof useTema>, "aplicado" | "definirPreferencia">) {
  const escuro = aplicado === "dark";

  return (
    <div className="flex items-center justify-end gap-2">
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
  );
}
