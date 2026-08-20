import { Outlet } from "react-router";

import { MobileNav } from "./MobileNav";
import { Sidebar } from "./Sidebar";

/** Casca das telas autenticadas. A proteção de rota de verdade (redirecionar
 *  quem não tem sessão) é o AUTH-04 — hoje qualquer URL é acessível. */
export function Layout() {
  return (
    <div className="flex bg-background min-h-screen">
      <Sidebar />
      {/* pb-20 no celular abre espaço para a barra inferior não cobrir conteúdo */}
      <main className="flex-1 min-w-0 overflow-y-auto p-4 pb-20 md:p-8">
        <Outlet />
      </main>
      <MobileNav />
    </div>
  );
}
