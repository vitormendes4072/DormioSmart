import { LogOut, User } from "lucide-react";
import { NavLink, useNavigate } from "react-router";

import { useAuth } from "../contexts/AuthContext";

import { ITENS_NAV } from "./nav";
import { MarcaDoProduto } from "./MarcaDoProduto";

/** Navegação de desktop. Em telas menores que `md` dá lugar à MobileNav —
 *  uma barra lateral de 224px fixa não cabe num celular. */
export function Sidebar() {
  const navigate = useNavigate();
  const { usuario, carregando, sair } = useAuth();

  // `nome` vem do metadado gravado no cadastro; o e-mail e sempre garantido.
  const nome = (usuario?.user_metadata?.nome as string | undefined)?.trim();

  return (
    <aside className="hidden md:flex w-56 flex-shrink-0 bg-card border-r border-border flex-col h-screen sticky top-0">
      <div className="p-6 border-b border-border">
        {/* Ocupa a largura util da sidebar (176px), o que dá ~30px de altura —
            o tamanho em que o "SMART" foi verificado como legível. */}
        <MarcaDoProduto className="h-[30px]" />
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
          <div className="min-w-0">
            <p className="text-sm font-medium text-foreground truncate">
              {carregando ? "..." : (nome || "Conta")}
            </p>
            <p className="text-xs text-muted-foreground truncate">
              {carregando ? "" : (usuario?.email ?? "não autenticada")}
            </p>
          </div>
        </div>
        <button
          onClick={async () => {
            await sair();
            navigate("/login");
          }}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-sm text-muted-foreground hover:text-foreground hover:bg-secondary transition-all duration-150"
        >
          <LogOut className="w-4 h-4" />
          Sair
        </button>
      </div>
    </aside>
  );
}
