import { Home, Moon, Settings, Smartphone, type LucideIcon } from "lucide-react";

import { noiteNativaDisponivel } from "../lib/noiteNativa";

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

/**
 * APP-02, etapa 4: no app Android, a noite inteira tem tela própria, e ela vem
 * primeiro. No site, a navegação é a de sempre — o registro da noite só
 * existe no app.
 */
export const ITEM_NOITE: ItemNav = { to: "/noite", label: "Noite", icon: Moon };

export function itensDeNavegacao(nativo: boolean = noiteNativaDisponivel()): ItemNav[] {
  return nativo ? [ITEM_NOITE, ...ITENS_NAV] : ITENS_NAV;
}
