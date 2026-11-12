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
    <div className="min-w-0 min-h-[109px] rounded-[14px] border border-border bg-card p-3 shadow-sm sm:min-h-[119px] sm:p-4">
      <div className="flex items-center justify-between gap-2 mb-2">
        <p className="text-[10px] font-bold text-muted-foreground">
          {rotulo}
        </p>
        <span className={`grid size-8 shrink-0 place-items-center rounded-lg bg-primary/10 ${corDoIcone}`}>
          <Icone className="size-4" aria-hidden />
        </span>
      </div>
      <p className="text-[22px] font-extrabold leading-tight tracking-tight text-foreground sm:text-[25px]">
        {temValor ? valor : "--"}
        {temValor && unidade ? (
          <span className="text-sm font-medium text-muted-foreground ml-1">{unidade}</span>
        ) : null}
      </p>
      <p className="mt-1 text-[10px] leading-tight text-muted-foreground">{detalhe ?? " "}</p>
    </div>
  );
}
