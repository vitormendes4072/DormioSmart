import { Monitor, Moon, Sun } from "lucide-react";
import { useId } from "react";

import { useTema } from "../hooks/useTema";
import type { PreferenciaDeTema } from "../lib/tema";
import { LINHA_DE_CONFIGURACAO } from "../lib/ui";

const OPCOES: { valor: PreferenciaDeTema; rotulo: string; icone: typeof Sun }[] = [
  { valor: "claro", rotulo: "Claro", icone: Sun },
  { valor: "escuro", rotulo: "Escuro", icone: Moon },
  { valor: "sistema", rotulo: "Sistema", icone: Monitor },
];

export function SeletorDeTema() {
  const { preferencia, aplicado, definirPreferencia } = useTema();
  const grupo = useId();

  return (
    <div>
      <div
        role="radiogroup"
        aria-label="Tema da interface"
        className="divide-y divide-border"
      >
        {OPCOES.map(({ valor, rotulo, icone: Icone }) => {
          const ativo = preferencia === valor;
          return (
            <label
              key={valor}
              className={`${LINHA_DE_CONFIGURACAO} cursor-pointer text-sm font-medium transition hover:text-primary
                ${ativo ? "text-primary" : "text-foreground"}`}
            >
              <span className="flex items-center gap-2.5">
                <Icone className="size-4 shrink-0 text-muted-foreground" aria-hidden />
                {rotulo}
              </span>
              <input
                type="radio"
                name={grupo}
                value={valor}
                checked={ativo}
                onChange={() => definirPreferencia(valor)}
                className="size-4 shrink-0 accent-primary"
              />
            </label>
          );
        })}
      </div>

      {preferencia === "sistema" ? (
        <p className="border-t border-border py-3 text-xs text-muted-foreground">
          Acompanhando o sistema — no momento, {aplicado === "dark" ? "escuro" : "claro"}.
        </p>
      ) : null}
    </div>
  );
}
