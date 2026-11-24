import { NavLink, useLocation } from "react-router";

import { destinoDoWorkspace, itensDeNavegacao } from "./nav";

/**
 * Navegação de celular: barra fixa no rodapé, no alcance do polegar.
 *
 * ── SO DESTINOS, NENHUMA ACAO ──────────────────────────────────────────
 *
 * "Sair" ficava aqui e ocupava um quarto da barra — um slot permanente para
 * uma acao que se usa uma vez por sessao, ao lado de tres lugares que se
 * visita o tempo todo. Pior, uma barra de navegacao ensina que cada item e
 * um lugar; um botao destrutivo no meio quebra essa expectativa.
 *
 * Foi para o fim de Configuracoes, que e onde se procura por ele.
 */
export function MobileNav() {
  const { search } = useLocation();
  const base =
    "group min-w-0 flex-1 flex flex-col items-center justify-center gap-1 px-0.5 py-2 text-[10px] min-[440px]:text-xs font-medium transition-colors";

  return (
    <nav aria-label="Navegação móvel" className="md:hidden fixed bottom-0 inset-x-0 z-40 bg-card border-t border-border flex items-stretch pb-[env(safe-area-inset-bottom)]">
      {itensDeNavegacao().map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={destinoDoWorkspace(to, search)}
          className={({ isActive }) =>
            `${base} ${isActive ? "text-primary font-semibold" : "text-muted-foreground"}`
          }
        >
          {/* UI-43: a aba ativa ganha uma pílula atrás do ícone, como no celular de exemplo da
              landing. Atrás só do ícone, e não do rótulo, para "Configurações" caber a 360 px. */}
          <span data-pilula className="grid h-7 w-12 place-items-center rounded-full transition-colors group-aria-[current=page]:bg-secondary">
            <Icon className="w-5 h-5" />
          </span>
          <span className="max-w-full text-center leading-tight whitespace-nowrap">{label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
