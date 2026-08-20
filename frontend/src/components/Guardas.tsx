import { Loader2 } from "lucide-react";
import type { ReactNode } from "react";
import { Navigate, Outlet, useLocation } from "react-router";

import { useAuth } from "../contexts/AuthContext";
import { decidirDestino } from "../lib/rotas";

function Aguardando() {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center">
      <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      <span className="sr-only">Verificando sua sessão...</span>
    </div>
  );
}

/** Rotas que exigem sessão. Sem ela, vai para o login. */
export function RotaProtegida({ children }: { children?: ReactNode }) {
  const { sessao, carregando } = useAuth();
  const local = useLocation();

  const destino = decidirDestino({
    carregando,
    temSessao: sessao !== null,
    ehRotaDeVisitante: false,
  });

  if (destino === "aguardar") return <Aguardando />;
  if (destino === "ir-para-login") {
    // `state` guarda para onde a pessoa queria ir, para o login devolver ela
    // ao destino em vez de despejar todo mundo no dashboard.
    return <Navigate to="/login" replace state={{ de: local.pathname + local.search }} />;
  }
  return <>{children ?? <Outlet />}</>;
}

/** Login e cadastro: quem já tem sessão não deve ficar aqui. */
export function RotaDeVisitante({ children }: { children?: ReactNode }) {
  const { sessao, carregando } = useAuth();

  const destino = decidirDestino({
    carregando,
    temSessao: sessao !== null,
    ehRotaDeVisitante: true,
  });

  if (destino === "aguardar") return <Aguardando />;
  if (destino === "ir-para-dashboard") return <Navigate to="/dashboard" replace />;
  return <>{children ?? <Outlet />}</>;
}
