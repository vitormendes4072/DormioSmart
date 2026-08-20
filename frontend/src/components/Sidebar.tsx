import { LogOut, Moon, User } from "lucide-react";
import { NavLink, useNavigate } from "react-router";

import { NOME_PRODUTO } from "../lib/ui";
import { ITENS_NAV } from "./nav";

/** Navegação de desktop. Em telas menores que `md` dá lugar à MobileNav —
 *  uma barra lateral de 224px fixa não cabe num celular. */
export function Sidebar() {
  const navigate = useNavigate();

  return (
    <aside className="hidden md:flex w-56 flex-shrink-0 bg-card border-r border-border flex-col h-screen sticky top-0">
      <div className="p-6 border-b border-border">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-primary/20 flex items-center justify-center">
            <Moon className="w-5 h-5 text-primary" />
          </div>
          <span className="font-semibold text-foreground text-lg tracking-tight">
            {NOME_PRODUTO}
          </span>
        </div>
      </div>

      <nav className="flex-1 p-4 space-y-0.5">
        {ITENS_NAV.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 ${
                isActive
                  ? "bg-primary/15 text-primary"
                  : "text-muted-foreground hover:text-foreground hover:bg-secondary"
              }`
            }
          >
            <Icon className="w-4 h-4" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="p-4 border-t border-border space-y-3">
        <div className="flex items-center gap-3 px-1">
          <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0">
            <User className="w-4 h-4 text-primary" />
          </div>
          {/* Nome e e-mail reais chegam com a sessao (AUTH-01). Ate la, nao
              inventamos um usuario: "Rafael Silva / rafael@email.com" era
              persona do prototipo e nao pode aparecer como se fosse conta. */}
          <div className="min-w-0">
            <p className="text-sm font-medium text-foreground truncate">Conta</p>
            <p className="text-xs text-muted-foreground truncate">não autenticada</p>
          </div>
        </div>
        <button
          onClick={() => navigate("/login")}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-sm text-muted-foreground hover:text-foreground hover:bg-secondary transition-all duration-150"
        >
          <LogOut className="w-4 h-4" />
          Sair
        </button>
      </div>
    </aside>
  );
}
