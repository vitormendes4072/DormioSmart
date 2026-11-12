import { Outlet, useLocation } from "react-router";

import { estaEmModoDemo } from "../lib/demo";

import { FaixaDemo } from "./FaixaDemo";
import { MobileNav } from "./MobileNav";
import { Sidebar } from "./Sidebar";

/** Casca das telas autenticadas. A proteção de rota de verdade (redirecionar
 *  quem não tem sessão) é o AUTH-04 — hoje qualquer URL é acessível. */
export function Layout() {
  const { pathname } = useLocation();
  const painel = pathname === "/dashboard" || pathname === "/coletar";
  return (
    <div className="bg-background min-h-screen">
      {estaEmModoDemo() && !painel ? <FaixaDemo /> : null}
      <div className="flex min-h-screen">
        <Sidebar painel={painel} />
        {/* pb-20 no celular abre espaço para a barra inferior não cobrir conteúdo */}
        <main className={painel ? "min-w-0 flex-1 px-4 pb-20 pt-5 md:px-[30px] md:pt-[26px]" : "min-w-0 flex-1 overflow-y-auto p-4 pb-20 md:p-8"}>
          <Outlet />
        </main>
        <MobileNav />
      </div>
    </div>
  );
}
