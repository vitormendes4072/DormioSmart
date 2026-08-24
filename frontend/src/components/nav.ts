import { Home, Settings, Smartphone, type LucideIcon } from "lucide-react";

export type ItemNav = {
  to: string;
  label: string;
  icon: LucideIcon;
};

/** Fonte única da navegação: consumida pela Sidebar (desktop) e pela
 *  MobileNav (celular), para as duas nunca saírem de sincronia. */
export const ITENS_NAV: ItemNav[] = [
  { to: "/dashboard", label: "Início", icon: Home },
  { to: "/coletar", label: "Coletar", icon: Smartphone },
  { to: "/configuracoes", label: "Configurações", icon: Settings },
];
