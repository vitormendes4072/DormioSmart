import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { MoreHorizontal } from "lucide-react";

/**
 * As ações de uma sessão do Histórico atrás de um botão "…" (UI-53).
 *
 * Os botões "Marcar como bancada" e "Excluir…" ficavam à vista em toda linha e pesavam
 * mais que os dados. Aqui eles abrem sob demanda, num painel que é uma divulgação (botão
 * com `aria-expanded` e a lista logo depois), e não um `role="menu"`: as ações seguem
 * sendo botões, com os mesmos nomes que a política de privacidade cita. Fecha pelo Esc,
 * por um toque fora ou depois de escolher, e o foco volta ao "…" quando faz sentido.
 */
export function MenuDaSessao({ rotulo, children }: {
  /** Nome acessível do "…", com a sessão: "Ações da sessão de 26 nov 2026". */
  rotulo: string;
  /** Os botões das ações. Um clique em qualquer um fecha o painel. */
  children: ReactNode;
}) {
  const [aberto, setAberto] = useState(false);
  const raiz = useRef<HTMLDivElement>(null);
  const gatilho = useRef<HTMLButtonElement>(null);
  const id = useId();

  useEffect(() => {
    if (!aberto) return;
    raiz.current?.querySelector<HTMLButtonElement>("[data-acoes] button:not(:disabled)")?.focus();
    const fora = (evento: PointerEvent) => {
      if (!raiz.current?.contains(evento.target as Node)) setAberto(false);
    };
    document.addEventListener("pointerdown", fora);
    return () => document.removeEventListener("pointerdown", fora);
  }, [aberto]);

  return (
    <div ref={raiz} className="relative inline-flex"
      onKeyDown={(evento) => {
        if (evento.key === "Escape" && aberto) {
          evento.stopPropagation();
          setAberto(false);
          gatilho.current?.focus();
        }
      }}>
      <button ref={gatilho} type="button" aria-label={rotulo} aria-expanded={aberto} aria-controls={id}
        onClick={() => setAberto((valor) => !valor)}
        className="grid size-9 place-items-center rounded-lg border border-border text-muted-foreground hover:bg-secondary hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring md:size-8">
        <MoreHorizontal className="size-4" aria-hidden />
      </button>
      {aberto && (
        <div id={id} data-acoes
          // Depois de escolher, o painel fecha; o que a ação abre (o diálogo) cuida do foco.
          onClick={(evento) => { if ((evento.target as HTMLElement).closest("button")) setAberto(false); }}
          className="absolute top-full right-0 z-30 mt-1 flex min-w-48 flex-col gap-1 rounded-xl border border-border bg-card p-1.5 shadow-lg [&>button]:min-h-10 [&>button]:w-full [&>button]:justify-start [&>button]:text-left md:[&>button]:min-h-9">
          {children}
        </div>
      )}
    </div>
  );
}
