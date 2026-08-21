import { Monitor, Moon, Sun } from "lucide-react";

import { useTema } from "../hooks/useTema";
import type { PreferenciaDeTema } from "../lib/tema";

const OPCOES: { valor: PreferenciaDeTema; rotulo: string; icone: typeof Sun }[] = [
  { valor: "claro", rotulo: "Claro", icone: Sun },
  { valor: "escuro", rotulo: "Escuro", icone: Moon },
  { valor: "sistema", rotulo: "Sistema", icone: Monitor },
];

export function SeletorDeTema() {
  const { preferencia, aplicado, definirPreferencia } = useTema();

  return (
    <div>
      <div
        role="radiogroup"
        aria-label="Tema da interface"
        className="grid grid-cols-3 gap-2"
      >
        {OPCOES.map(({ valor, rotulo, icone: Icone }) => {
          const ativo = preferencia === valor;
          return (
            <button
              key={valor}
              role="radio"
              aria-checked={ativo}
              onClick={() => definirPreferencia(valor)}
              className={`flex flex-col items-center gap-2 rounded-xl border px-3 py-4 text-sm font-medium transition
                ${
                  ativo
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-border text-muted-foreground hover:bg-secondary hover:text-foreground"
                }`}
            >
              <Icone className="w-5 h-5" />
              {rotulo}
            </button>
          );
        })}
      </div>

      {preferencia === "sistema" ? (
        <p className="text-xs text-muted-foreground mt-3">
          Acompanhando o sistema — no momento, {aplicado === "dark" ? "escuro" : "claro"}.
        </p>
      ) : null}
    </div>
  );
}
