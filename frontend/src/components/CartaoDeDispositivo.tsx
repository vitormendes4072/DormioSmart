import { Cpu, Radio, Smartphone } from "lucide-react";
import type { ReactNode } from "react";

import type { TipoDeDispositivo } from "../lib/dispositivos";
import { EtiquetaDeRegistro, SUPERFICIE_DO_CARTAO_DE_REGISTRO } from "./CartoesDeRegistro";

export function CartaoDeDispositivo({ tipo, children }: { tipo?: TipoDeDispositivo; children: ReactNode }) {
  return (
    <li className={`${SUPERFICIE_DO_CARTAO_DE_REGISTRO} flex min-w-0 items-start gap-3 p-4 sm:items-center`}>
      <IconeDoDispositivo tipo={tipo} />
      {children}
    </li>
  );
}

export function IconeDoDispositivo({ tipo }: { tipo?: TipoDeDispositivo }) {
  const Icone = tipo === "celular" ? Smartphone : tipo === "travesseiro" ? Radio : Cpu;
  return (
    <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-primary/10 text-primary">
      <Icone className="size-4" aria-hidden />
    </span>
  );
}

const TONS_DO_ESTADO = {
  Conectado: "bg-emerald-500/10 text-emerald-800 dark:text-emerald-300",
  Pausado: "bg-amber-500/10 text-amber-800 dark:text-amber-300",
  Inativo: "bg-secondary text-muted-foreground",
  Revogado: "bg-secondary text-muted-foreground",
};

export function EstadoDoDispositivo({ estado }: { estado: keyof typeof TONS_DO_ESTADO }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 ${TONS_DO_ESTADO[estado]}`}>
      <span className="size-1.5 shrink-0 rounded-full bg-current" aria-hidden />
      <EtiquetaDeRegistro cor="text-inherit">{estado}</EtiquetaDeRegistro>
    </span>
  );
}
