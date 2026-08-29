import { NavLink } from "react-router";

import { ITENS_NAV } from "./nav";

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
  const base =
    "flex-1 flex flex-col items-center justify-center gap-1 py-2.5 text-xs font-medium transition-colors";

  return (
    <nav className="md:hidden fixed bottom-0 inset-x-0 z-40 bg-card border-t border-border flex items-stretch pb-[env(safe-area-inset-bottom)]">
      {ITENS_NAV.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            `${base} ${isActive ? "text-primary" : "text-muted-foreground"}`
          }
        >
          <Icon className="w-5 h-5" />
          {label}
        </NavLink>
      ))}
    </nav>
  );
}
