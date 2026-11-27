import { useId } from "react";

export function CampoMetaDiaria({ valor, alterar }: { valor: string; alterar: (valor: string) => void }) {
  const id = useId();
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="block text-xs text-muted-foreground">Meta de tempo registrado por dia</label>
      <input id={id} value={valor} onChange={(e) => alterar(e.target.value)} aria-describedby={id + "-ajuda"}
        className="min-h-11 w-full rounded-lg border border-border bg-input-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
      <p id={id + "-ajuda"} className="text-xs text-muted-foreground">
        Use horas e minutos (H:MM), em passos de 15 minutos. Deixe em branco para ficar sem meta.
      </p>
      <p className="text-xs text-muted-foreground">É uma meta sua. O Smart Dormio não recomenda quantas horas dormir.</p>
    </div>
  );
}
