import { AlertTriangle, Check, Copy } from "lucide-react";
import { useState } from "react";

import type { Pareamento } from "../lib/dispositivos";

/**
 * O token aparece UMA VEZ.
 *
 * O banco guarda só o hash, então este é o único momento em que o valor
 * existe. O aviso vem antes do campo, e o bloco não fecha sozinho — fechar
 * automaticamente após copiar seria perder o valor de quem se distraiu.
 */
export function TokenRecemCriado({
  pareamento,
  aoFechar,
  rotuloAoFechar = "Já copiei, pode ocultar",
}: {
  pareamento: Pareamento;
  aoFechar: () => void;
  rotuloAoFechar?: string;
}) {
  const [copia, setCopia] = useState<"copiado" | "manual" | null>(null);

  async function copiar() {
    try {
      await navigator.clipboard.writeText(pareamento.token);
      setCopia("copiado");
    } catch {
      // Sem permissão de área de transferência: o valor segue visível para
      // seleção manual, então não é um caminho sem saída.
      setCopia("manual");
    }
  }

  return (
    <div className="space-y-3 rounded-2xl border border-primary/40 bg-primary/5 p-4">
      <div className="flex items-start gap-2">
        <AlertTriangle className="w-4 h-4 text-primary flex-shrink-0 mt-0.5" />
        <div className="min-w-0">
          <p className="text-sm font-semibold text-foreground">
            Copie agora — este código de conexão não será mostrado de novo
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">
            Não guardamos o código, só uma forma de conferi-lo. Se perder, será preciso parear
            outro dispositivo.
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <code className="flex-1 min-w-0 px-3 py-2 rounded-lg bg-card border border-border text-xs font-mono text-foreground break-all select-all">
          {pareamento.token}
        </code>
        <button
          onClick={copiar}
          aria-label="Copiar código de conexão"
          className="min-h-11 min-w-11 inline-flex items-center justify-center flex-shrink-0 p-2 rounded-lg bg-secondary hover:bg-secondary/70 transition"
        >
          {copia === "copiado" ? (
            <Check className="w-4 h-4 text-primary" />
          ) : (
            <Copy className="w-4 h-4 text-muted-foreground" />
          )}
        </button>
      </div>

      {copia === "manual" && <p role="status">Selecione o código acima e copie manualmente.</p>}
      {copia === "copiado" && <p role="status">Código copiado.</p>}
      <p className="text-xs text-muted-foreground">
        O código precisa ser gravado na placa do travesseiro.
      </p>
      {/* Aberto: sem este passo o travesseiro não conecta. */}
      <details open className="text-xs text-muted-foreground">
        <summary className="flex min-h-11 cursor-pointer items-center font-semibold">Detalhes técnicos</summary>
        <p className="mt-1">
        Cole em <code className="font-mono">firmware/secrets.h</code>, no campo{" "}
        <code className="font-mono">DEVICE_TOKEN</code>. O <code>secrets.h</code> é ignorado pelo Git e nunca deve
        ser commitado. Depois, grave o firmware na placa seguindo o{" "}
        <a className="inline-flex min-h-11 items-center underline" href="https://github.com/vitormendes4072/DormioSmart/blob/main/firmware/README.md">
          firmware/README.md
        </a>.
        </p>
      </details>

      <button
        onClick={aoFechar}
        className="min-h-11 rounded-lg bg-primary px-3 text-sm font-semibold text-primary-foreground focus-visible:outline-2 focus-visible:outline-ring"
      >
        {rotuloAoFechar}
      </button>
    </div>
  );
}
