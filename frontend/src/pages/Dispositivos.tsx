import { useState } from "react";
import { useLocation } from "react-router";

import { BarraDoWorkspace } from "../components/BarraDoWorkspace";
import { CartaoDeDispositivo, EstadoDoDispositivo, MeusDispositivos } from "../components/MeusDispositivos";
import { estaEmModoDemo } from "../lib/demo";
import type { TipoDeDispositivo } from "../lib/dispositivos";

export function Dispositivos() {
  const { search } = useLocation();
  const demo = estaEmModoDemo(search);
  const [pareamentoAberto, setPareamentoAberto] = useState(false);

  return (
    <div className="mx-auto max-w-[1540px] space-y-4">
      <header>
        <BarraDoWorkspace secao="Dispositivos" />
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-2xl font-extrabold tracking-tight text-foreground sm:text-[27px]">Dispositivos</h1>
            <p className="mt-0.5 text-xs text-muted-foreground">Gerencie os aparelhos vinculados à sua conta.</p>
          </div>
          <button
            type="button"
            aria-expanded={pareamentoAberto}
            aria-controls="pareamento-dispositivo"
            onClick={() => setPareamentoAberto((aberto) => !aberto)}
            className="rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90"
          >
            {pareamentoAberto ? "Ocultar pareamento" : "Parear dispositivo"}
          </button>
        </div>
      </header>

      {demo ? (
        <DispositivosDemonstrativos mostrarPareamento={pareamentoAberto} />
      ) : (
        <MeusDispositivos mostrarPareamento={pareamentoAberto} />
      )}

      <section className="rounded-[14px] border border-border bg-card p-4 shadow-sm">
        <h2 className="text-sm font-bold text-foreground">Sobre o pareamento</h2>
        <p className="mt-2 text-xs text-muted-foreground">
          Cada dispositivo pareado recebe uma credencial própria. Guarde-a ao concluir o pareamento.
        </p>
      </section>
    </div>
  );
}

const EXEMPLOS = [
  { nome: "Dormio Pillow Sensor", tipo: "travesseiro", detalhe: "Sensor no travesseiro · Último envio há 2 minutos", ativo: true },
  { nome: "Celular de teste", tipo: "celular", detalhe: "Smartphone · Último registro em 02 nov", ativo: false },
] satisfies Array<{ nome: string; tipo: TipoDeDispositivo; detalhe: string; ativo: boolean }>;

function DispositivosDemonstrativos({ mostrarPareamento }: { mostrarPareamento: boolean }) {
  const [ativos, setAtivos] = useState(() => EXEMPLOS.map(({ ativo }) => ativo));

  return (
    <div className="space-y-4">
      <ul className="space-y-3" aria-label="Dispositivos de demonstração">
        {EXEMPLOS.map(({ nome, tipo, detalhe }, indice) => (
          <CartaoDeDispositivo key={tipo} tipo={tipo}>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-foreground">{nome}</p>
              <p className="mt-0.5 text-xs text-muted-foreground">{detalhe}</p>
              <EstadoDoDispositivo ativo={ativos[indice]}>{ativos[indice] ? "Conectado" : "Inativo"}</EstadoDoDispositivo>
            </div>
            <button
              type="button"
              role="switch"
              aria-label={`Ativar ${nome} na demonstração`}
              aria-checked={ativos[indice]}
              onClick={() => setAtivos((atuais) => atuais.map((ativo, i) => i === indice ? !ativo : ativo))}
              className="grid size-11 shrink-0 place-items-center rounded-lg"
            >
              <span aria-hidden className={`flex h-5 w-9 items-center rounded-full p-0.5 transition-colors ${ativos[indice] ? "justify-end bg-primary" : "bg-muted-foreground/25"}`}>
                <span className="size-4 rounded-full bg-white shadow-sm" />
              </span>
            </button>
          </CartaoDeDispositivo>
        ))}
      </ul>
      <section id="pareamento-dispositivo" hidden={!mostrarPareamento} className="rounded-xl border border-border bg-card p-4">
        <h2 className="text-sm font-semibold text-foreground">Parear novo dispositivo</h2>
        <p className="mt-2 text-xs text-muted-foreground">Entre na sua conta para parear um aparelho real.</p>
      </section>
    </div>
  );
}
