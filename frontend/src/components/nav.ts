import { estaEmModoDemo, PARAMETRO_DEMO } from "../lib/demo";
import { Clock3, Home, Moon, Radio, Settings, Smartphone, type LucideIcon } from "lucide-react";

import { noiteNativaDisponivel } from "../lib/noiteNativa";

type ItemNav = {
  to: string;
  label: string;
  icon: LucideIcon;
};

/** Fonte única da navegação: consumida pela Sidebar (desktop) e pela
 *  MobileNav (celular), para as duas nunca saírem de sincronia. */
const ITENS_NAV: ItemNav[] = [
  { to: "/dashboard", label: "Início", icon: Home },
  { to: "/coletar", label: "Coletar", icon: Smartphone },
  { to: "/historico", label: "Histórico", icon: Clock3 },
  { to: "/dispositivos", label: "Dispositivos", icon: Radio },
  { to: "/configuracoes", label: "Configurações", icon: Settings },
];

/**
 * No app, a tela Noite substitui Coletar na navegação (UI-41).
 */
const ITEM_NOITE: ItemNav = { to: "/noite", label: "Noite", icon: Moon };

const ITENS_NAV_APP = [ITEM_NOITE, ...ITENS_NAV.filter(({ to }) => to !== "/coletar")];

export function itensDeNavegacao(nativo: boolean = noiteNativaDisponivel()): ItemNav[] {
  return nativo ? ITENS_NAV_APP : ITENS_NAV;
}

/** As telas com demonstração própria compartilham a navegação local. */
export function destinoDoWorkspace(to: string, busca: string): string {
  const rota = to.split("#", 1)[0];
  if ((rota !== "/dashboard" && rota !== "/coletar" && rota !== "/dispositivos" && rota !== "/historico" && rota !== "/configuracoes") || !estaEmModoDemo(busca)) return to;

  const fragmento = to.slice(rota.length);
  return `${rota}?${PARAMETRO_DEMO}=1${fragmento}`;
}
