import { LogOut } from "lucide-react";
import { NavLink, useNavigate } from "react-router";

import { useAuth } from "../contexts/AuthContext";

import { ITENS_NAV } from "./nav";

/** Navegação de celular: barra fixa no rodapé, no alcance do polegar.
 *  Com apenas dois destinos, uma barra inferior é mais direta que uma gaveta
 *  — não esconde a navegação atrás de um toque extra. */
export function MobileNav() {
  const navigate = useNavigate();
  const { sair } = useAuth();

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
      <button
        onClick={async () => {
          await sair();
          navigate("/login");
        }}
        className={`${base} text-muted-foreground`}
      >
        <LogOut className="w-5 h-5" />
        Sair
      </button>
    </nav>
  );
}
