import type { LucideIcon } from "lucide-react";

/**
 * Card de metrica.
 *
 * `valor` aceita null de proposito: sem dado ele mostra "--", nunca zero.
 * Zero e uma medicao ("contamos e deu zero"); ausencia e outra coisa, e
 * confundir as duas num painel de sensor e enganoso.
 */
export function CardMetrica({
  rotulo,
  valor,
  unidade,
  detalhe,
  icone: Icone,
  corDoIcone = "text-muted-foreground",
}: {
  rotulo: string;
  valor: string | number | null;
  unidade?: string;
  detalhe?: string;
  icone: LucideIcon;
  corDoIcone?: string;
}) {
  const temValor = valor !== null && valor !== undefined;

  return (
    <div className="min-w-0 rounded-2xl border border-border bg-card p-3 shadow-sm sm:p-4">
      <div className="flex items-center justify-between gap-2 mb-4">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          {rotulo}
        </p>
        <span className={`grid size-8 shrink-0 place-items-center rounded-lg bg-primary/10 ${corDoIcone}`}>
          <Icone className="size-4" aria-hidden />
        </span>
      </div>
      <p className="text-2xl font-bold text-foreground">
        {temValor ? valor : "--"}
        {temValor && unidade ? (
          <span className="text-sm font-medium text-muted-foreground ml-1">{unidade}</span>
        ) : null}
      </p>
      <p className="text-xs text-muted-foreground mt-1">{detalhe ?? " "}</p>
    </div>
  );
}
