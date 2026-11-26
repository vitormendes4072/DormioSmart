import { useId, useState } from "react";

import { MarcaDoDiaSelecionado } from "./MarcaDoDiaSelecionado";
import { serieDaSemana } from "../lib/calendarioDoSono";

const DATA = new Intl.DateTimeFormat("pt-BR", { weekday: "long", day: "numeric", month: "long" });
const HORA = 3_600_000;
const ALTURA = 144;
const LARGURA_DIA = 100;

type Props = {
  registros: ReadonlyMap<number, number>;
  referencia: Date;
  hoje: Date;
  selecionado: Date | null;
  aoSelecionarDia: (dia: Date) => void;
  carregando: boolean;
  falhou: boolean;
  parcial: boolean;
  recarregar: () => void;
};

function duracao(tempoMs: number) {
  const minutos = Math.floor(tempoMs / 60_000);
  return Math.floor(minutos / 60) + "h " + String(minutos % 60).padStart(2, "0") + "m";
}

function valorDoDia(dia: ReturnType<typeof serieDaSemana>["dias"][number]) {
  if (dia.estado === "registrado") return duracao(dia.tempoMs) + " registrados";
  return dia.estado === "incompleto" ? "dados incompletos" : "sem registro";
}

function contornoDaBarra(indice: number, topo: number) {
  const esquerda = indice * LARGURA_DIA + 25;
  const direita = esquerda + 50;
  const raio = Math.min(9, ALTURA - topo);
  return [
    "M", esquerda, ALTURA, "V", topo + raio,
    "Q", esquerda, topo, esquerda + raio, topo,
    "H", direita - raio, "Q", direita, topo, direita, topo + raio,
    "V", ALTURA, "Z",
  ].join(" ");
}

export function GraficoDeTempoPorDia({
  registros, referencia, hoje, selecionado, aoSelecionarDia, carregando, falhou, parcial, recarregar,
}: Props) {
  const titulo = useId();
  const [diaInspecionado, setDiaInspecionado] = useState<number | null>(null);
  const { dias, comRegistro, media, maiores, menores } = serieDaSemana(registros, referencia, hoje, parcial);
  const escolhido = selecionado?.getTime();
  const escolhaNaSemana = dias.some((dia) => dia.estado !== "futuro" && dia.data.getTime() === escolhido);
  const existeDadoIndeterminado = dias.some((dia) => dia.estado === "incompleto");
  const indiceDoTooltip = dias.findIndex((dia) => dia.data.getTime() === diaInspecionado && dia.estado !== "futuro");
  const diaDoTooltip = dias[indiceDoTooltip];
  const maximo = maiores[0]?.tempoMs ?? 0;
  const passo = Math.max(1, Math.ceil(maximo / (3 * HORA)));
  const y = (tempoMs: number) => ALTURA * (1 - tempoMs / (passo * 3 * HORA));
  const ticks = [3 * passo, 2 * passo, passo, 0];

  function resumo(grupo: typeof maiores) {
    return grupo.map((dia) => dia.rotulo).join(", ") + " · " + duracao(grupo[0].tempoMs);
  }

  return (
    <section aria-labelledby={titulo} className="min-w-0 rounded-2xl border border-border bg-card px-3 py-3 shadow-sm sm:px-4">
      <h2 id={titulo} className="text-sm font-extrabold tracking-tight sm:text-base">Tempo registrado por dia</h2>
      {carregando && <p role="status" className="mt-2 text-sm text-muted-foreground">Carregando registros da semana…</p>}
      {falhou && (
        <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
          <p role="alert">Não foi possível carregar os registros da semana.</p>
          <button type="button" onClick={recarregar} className="min-h-9 rounded-lg border border-border px-2.5 text-xs font-semibold text-primary hover:bg-secondary focus-visible:outline-2 focus-visible:outline-ring">
            Tentar novamente
          </button>
        </div>
      )}
      {!carregando && !falhou && (
        <>
          {parcial && <p role="status" className="mt-1 text-xs font-semibold text-muted-foreground">Histórico parcial. A semana está incompleta.</p>}
          {media === null && !existeDadoIndeterminado ? (
            <p className="mt-2 text-sm text-muted-foreground">
              {parcial ? "Nenhum registro da semana nos dados carregados" : "Sem registros nesta semana"}
            </p>
          ) : (
            <>
              {media !== null && <ul aria-label="Resumo do tempo registrado" className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground">
                {comRegistro.length === 1 ? (
                  <li>{resumo(comRegistro)}</li>
                ) : (
                  <>
                    {maiores.length === comRegistro.length ? (
                      <li><strong>Mesmo tempo:</strong> {resumo(maiores)}</li>
                    ) : (
                      <>
                        <li><strong>Mais tempo:</strong> {resumo(maiores)}</li>
                        <li><strong>Menos tempo:</strong> {resumo(menores)}</li>
                      </>
                    )}
                    <li><strong>Média dos dias com registro:</strong> {duracao(media)}</li>
                  </>
                )}
              </ul>}
              <div className="mt-3 grid grid-cols-[1.75rem_minmax(0,1fr)]">
                <div aria-hidden="true" className="relative h-36 text-[10px] tabular-nums text-muted-foreground">
                  {ticks.map((valor, i) => (
                    <span key={valor} className="absolute right-2 -translate-y-1/2" style={{ top: i * 100 / 3 + "%" }}>
                      {valor}h
                    </span>
                  ))}
                </div>
                <div className="relative min-w-0">
                  <svg aria-hidden="true" className="pointer-events-none absolute inset-0 h-36 w-full overflow-visible" viewBox="0 0 700 144" preserveAspectRatio="none">
                    {ticks.map((valor) => (
                      <line key={valor} x1="0" x2="700" y1={y(valor * HORA)} y2={y(valor * HORA)}
                        className="stroke-border" vectorEffect="non-scaling-stroke" />
                    ))}
                    {dias.map((dia, indice) => dia.estado === "registrado" && (
                      <path key={dia.rotulo} data-barra={dia.rotulo} d={contornoDaBarra(indice, y(dia.tempoMs))}
                        className={escolhaNaSemana && escolhido !== dia.data.getTime() ? "fill-primary opacity-35" : "fill-primary"} />
                    ))}
                    {media !== null && <line x1="0" x2="700" y1={y(media)} y2={y(media)} className="stroke-muted-foreground"
                      strokeDasharray="4 4" vectorEffect="non-scaling-stroke" />}
                  </svg>
                  <div className="relative grid grid-cols-7">
                    {dias.map((dia) => {
                      const instante = dia.data.getTime();
                      const ativo = instante === escolhido;
                      if (dia.estado === "futuro") {
                        return <span key={instante} className="pt-36 text-center text-xs text-muted-foreground"><span className="block pt-1">{dia.rotulo}</span></span>;
                      }
                      return (
                        <button key={instante} type="button" aria-pressed={ativo}
                          aria-label={DATA.format(dia.data) + ", " + valorDoDia(dia)}
                          onPointerEnter={(evento) => { if (evento.pointerType === "mouse") setDiaInspecionado(instante); }}
                          onPointerLeave={(evento) => { if (evento.pointerType === "mouse") setDiaInspecionado(null); }}
                          onFocus={() => setDiaInspecionado(instante)}
                          onBlur={() => setDiaInspecionado(null)}
                          onClick={() => {
                            setDiaInspecionado(ativo ? null : instante);
                            aoSelecionarDia(dia.data);
                          }}
                          className="relative flex min-w-0 cursor-pointer items-end justify-center rounded-sm pt-36 text-xs font-semibold text-muted-foreground focus-visible:z-10 focus-visible:outline-2 focus-visible:outline-ring aria-pressed:text-primary">
                          <span className="block pt-1.5"><span className="relative inline-block rounded-full px-1 leading-5">{dia.rotulo}{ativo && <MarcaDoDiaSelecionado justa />}</span></span>
                        </button>
                      );
                    })}
                  </div>
                  {diaDoTooltip && (
                    <div role="tooltip" aria-hidden="true" className="pointer-events-none absolute top-2 z-20 -translate-x-1/2 whitespace-nowrap rounded-lg border border-border bg-card px-2 py-1 text-xs text-foreground shadow-md"
                      style={{ left: "clamp(4.25rem, " + (indiceDoTooltip + 0.5) * 100 / 7 + "%, calc(100% - 4.25rem))" }}>
                      <strong>{diaDoTooltip.rotulo}</strong> · {valorDoDia(diaDoTooltip)}
                    </div>
                  )}
                </div>
              </div>
              {media !== null && <p className="mt-2 flex items-center gap-1.5 text-[11px] text-muted-foreground">
                <span aria-hidden="true" className="w-4 border-t border-dashed border-current" /> Média
              </p>}
            </>
          )}
        </>
      )}
    </section>
  );
}
