import { ChevronDown, ChevronLeft, ChevronRight, Moon } from "lucide-react";
import { useId, useLayoutEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { GraficoDeTempoPorDia } from "./GraficoDeTempoPorDia";
import { MarcaDoDiaSelecionado } from "./MarcaDoDiaSelecionado";
import { SeletorSegmentado } from "./SeletorSegmentado";
import { useHistoricoPaginado } from "../hooks/useHistoricoPaginado";
import {
  DIAS_DA_SEMANA,
  janelaDoCalendario,
  limitesDaConsulta,
  registrosDoCalendario,
  segundaDaSemana,
  sequenciasDoCalendario,
  somarDias,
} from "../lib/calendarioDoSono";
import { formatarDuracao } from "../lib/metricas";

const VISOES = [
  { valor: "semana", rotulo: "Semana" },
  { valor: "mes", rotulo: "Mês" },
  { valor: "sequencias", rotulo: "Sequências" },
] as const;
type Visao = typeof VISOES[number]["valor"];


const DATA = new Intl.DateTimeFormat("pt-BR", { weekday: "long", day: "numeric", month: "long" });
const CURTA = new Intl.DateTimeFormat("pt-BR", { day: "numeric", month: "short" });
const MES = new Intl.DateTimeFormat("pt-BR", { month: "long", year: "numeric" });
const BOTAO = "inline-flex min-h-9 items-center justify-center gap-1 rounded-lg border border-border px-2.5 text-xs font-semibold text-primary hover:bg-secondary focus-visible:outline-2 focus-visible:outline-ring disabled:opacity-40";

function intervalo(inicio: Date, fim: Date) {
  return inicio.getTime() === fim.getTime()
    ? CURTA.format(inicio)
    : `${CURTA.format(inicio)} – ${CURTA.format(fim)}`;
}

function diasEmSequencia(total: number, podeSerMaior = false) {
  // "Pelo menos 1 dia consecutivo" soa estranho: um dia só não é sequência.
  if (podeSerMaior) return total === 1 ? "Pelo menos 1 dia" : `Pelo menos ${total} dias consecutivos`;
  return total === 1 ? "1 dia consecutivo" : `${total} dias consecutivos`;
}

export function CalendarioDoSono({ dispositivo, demo, selecionado, aoSelecionarDia, ancora, aoNavegar, destinoDoGrafico = null }: {
  dispositivo: string | null;
  demo: boolean;
  selecionado: Date | null;
  aoSelecionarDia: (dia: Date | null) => void;
  ancora: Date;
  aoNavegar: (dia: Date) => void;
  /** UI-48: em tela larga, o gráfico vai para a coluna da direita do Início; sem destino, fica abaixo do calendário. */
  destinoDoGrafico?: HTMLElement | null;
}) {
  const hoje = somarDias(new Date(), 0);
  const [aberto, setAberto] = useState(false);
  const [visao, setVisao] = useState<Visao>("semana");
  const [inicioDaSequencia, setInicioDaSequencia] = useState<number | null>(null);
  const titulo = useId();
  const painel = useId();
  const alternador = useRef<HTMLButtonElement>(null);
  const destinoInline = useRef<HTMLDivElement>(null);
  const [suporteDoGrafico] = useState(() => {
    const suporte = document.createElement("div");
    suporte.className = "flex min-w-0 flex-1 flex-col *:flex-1";
    return suporte;
  });

  // O portal mantém a mesma raiz quando muda de lugar, preservando a instância do gráfico.
  useLayoutEffect(() => {
    (destinoDoGrafico ?? destinoInline.current)?.append(suporteDoGrafico);
    return () => suporteDoGrafico.remove();
  }, [destinoDoGrafico, suporteDoGrafico]);

  const data = aberto ? ancora : selecionado ?? hoje;
  const janela = janelaDoCalendario(data);
  const semana = segundaDaSemana(data);
  const fimDaSemana = somarDias(semana, 6);
  // Uma semana pode atravessar o mês da data selecionada. A janela do mês
  // inclui as semanas de borda para manter a seleção e as sequências juntas.
  const inicioMs = janela.inicio.getTime();
  const fimMs = janela.fim.getTime();
  const ultimoDiaRegistrado = Math.min(hoje.getTime(), fimMs);
  const { dados, carregando, recarregar } = useHistoricoPaginado(
    limitesDaConsulta(janela.inicio, janela.fim), dispositivo, demo,
  );
  const registros = useMemo(() => dados
    ? registrosDoCalendario(dados.leituras, new Date(inicioMs), new Date(ultimoDiaRegistrado))
    : new Map<number, number>(), [dados, inicioMs, ultimoDiaRegistrado]);
  const sequencias = useMemo(() => sequenciasDoCalendario(registros), [registros]);
  const atual = sequencias.find((grupo) => {
    const fim = grupo[grupo.length - 1].getTime();
    return fim === hoje.getTime() || fim === somarDias(hoje, -1).getTime();
  });
  const atualDias = new Set(atual?.map(Number));
  const passadas = new Set(sequencias.filter((grupo) => grupo !== atual && grupo.length > 1).flat().map(Number));
  const porMes = sequencias.filter((grupo) => grupo.length > 1 && grupo.some((dia) => dia.getMonth() === data.getMonth()));
  const ativa = porMes.find((grupo) => grupo[0].getTime() === inicioDaSequencia) ?? porMes[0];
  const melhor = Math.max(0, ...sequencias.map((grupo) => grupo.length));
  // Um grupo que toca a borda esquerda pode ter começado antes dos dias
  // exibidos. Isso também pode mudar qual é a melhor sequência.
  const comecaNaBorda = (grupo?: Date[]) => grupo?.[0].getTime() === inicioMs;
  const textoAtual = diasEmSequencia(atual?.length ?? 0, comecaNaBorda(atual));
  const textoMelhor = diasEmSequencia(melhor, registros.has(inicioMs));
  const tempo = registros.get(data.getTime());
  const ehSemana = visao === "semana" || !aberto;
  const dias = ehSemana
    ? Array.from({ length: 7 }, (_, i) => somarDias(semana, i))
    : Array.from({ length: janela.deslocamento + janela.diasNoMes }, (_, i) =>
      i < janela.deslocamento ? null : somarDias(janela.inicio, i));
  const recorteAtual = hoje.getTime() >= inicioMs && hoje.getTime() <= fimMs;

  function navegar(direcao: number) {
    aoNavegar(ehSemana
      ? somarDias(data, direcao * 7)
      : new Date(data.getFullYear(), data.getMonth() + direcao, 1, 12));
  }

  function alternar() {
    if (!aberto) {
      aoNavegar(selecionado ?? hoje);
      setVisao("semana");
    }
    setAberto(!aberto);
  }

  function selecionarDia(dia: Date) {
    aoNavegar(dia);
    aoSelecionarDia(selecionado?.getTime() === dia.getTime() ? null : dia);
  }

  const grafico = (
    <GraficoDeTempoPorDia registros={registros} referencia={data} hoje={hoje} selecionado={selecionado}
      aoSelecionarDia={selecionarDia} carregando={carregando} falhou={dados === null}
      parcial={dados?.truncada ?? false} recarregar={recarregar} />
  );

  const grade = (
    <>
      <div className="grid grid-cols-7 text-center text-[11px] font-semibold text-muted-foreground" aria-hidden="true">
        {DIAS_DA_SEMANA.map((dia) => <span key={dia}>{dia}</span>)}
      </div>
      <div className="mt-1 grid grid-cols-7 gap-y-1">
        {dias.map((dia, indice) => {
          if (dia === null) return <span key={indice} aria-hidden="true" />;
          const instante = dia.getTime();
          const temRegistro = registros.has(instante);
          const eHoje = instante === hoje.getTime();
          const atual = atualDias.has(instante);
          const passada = passadas.has(instante) && aberto;
          const emFaixa = atual || passada;
          const marcados = atual ? atualDias : passadas;
          const inicioFaixa = indice % 7 === 0 || (!ehSemana && indice === janela.deslocamento)
            || !marcados.has(somarDias(dia, -1).getTime());
          const fimFaixa = indice % 7 === 6 || indice === dias.length - 1
            || !marcados.has(somarDias(dia, 1).getTime());
          return (
            <button
              key={instante}
              type="button"
              aria-label={`${DATA.format(dia)}${temRegistro ? ", com registro" : ""}${atual ? ", sequência atual" : passada ? ", sequência encerrada" : ""}`}
              aria-current={eHoje ? "date" : undefined}
              aria-pressed={instante === selecionado?.getTime()}
              onClick={() => selecionarDia(dia)}
              className={`group relative grid min-h-9 min-w-0 place-content-center justify-items-center text-xs font-semibold focus-visible:z-10 focus-visible:outline-2 focus-visible:outline-ring sm:text-sm ${aberto ? "min-h-12" : ""} ${atual ? "border-(color:--sessao-destaque-borda) bg-(color:--sessao-destaque-borda) text-white" : passada ? "bg-accent text-accent-foreground" : "rounded-xl text-foreground hover:bg-secondary"} ${emFaixa && inicioFaixa ? "rounded-s-2xl" : ""} ${emFaixa && fimFaixa ? "rounded-e-2xl" : ""}`}
            >
              <span className={`relative grid size-6 place-items-center rounded-full ${eHoje ? "ring-1 ring-inset ring-current" : ""} group-aria-pressed:font-extrabold`}>
                {dia.getDate()}
                {instante === selecionado?.getTime() && <MarcaDoDiaSelecionado />}
              </span>
              {temRegistro && (
                <span className={`size-1.5 rounded-full ${atual ? "bg-white" : "bg-primary"}`} aria-hidden="true" />
              )}
            </button>
          );
        })}
      </div>
    </>
  );

  return (
    <div data-calendario-do-inicio className={`w-full min-w-0 ${aberto && destinoDoGrafico ? "col-span-full" : ""}`}>
      <section aria-labelledby={titulo} className="@container min-w-0 rounded-2xl border border-border bg-card shadow-sm">
        <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-2 px-3 py-2.5 sm:px-4 @[450px]:grid-cols-[minmax(9rem,1fr)_minmax(10rem,1.5fr)_auto]">
          <div>
            <h2 id={titulo} className="text-sm font-extrabold tracking-tight sm:text-base">Calendário do sono</h2>
            {!aberto && (
              <p role="status" className="mt-0.5 text-xs text-muted-foreground">
                {carregando ? "Carregando registros…" : dados === null ? "Falha ao carregar registros" : dados?.truncada ? "Histórico parcial" : atual ? textoAtual : "Sem sequência ativa no período"}
              </p>
            )}
          </div>
          {!aberto && <div aria-label={selecionado ? "Semana selecionada" : "Semana atual"} role="group" className="col-span-2 row-start-2 min-w-0 @[450px]:col-span-1 @[450px]:col-start-2 @[450px]:row-start-1">{grade}</div>}
          <button ref={alternador} type="button" aria-expanded={aberto} aria-controls={painel} onClick={alternar} className={`${BOTAO} col-start-2 row-start-1 justify-self-end @[450px]:col-start-3`}>
            {aberto ? "Recolher" : "Expandir"}
            <ChevronDown size={14} className={aberto ? "rotate-180" : undefined} aria-hidden="true" />
          </button>
        </div>

        <div id={painel} hidden={!aberto} onKeyDown={(evento) => {
          if (evento.key === "Escape") {
            setAberto(false);
            alternador.current?.focus();
          }
        }} className="border-t border-border p-3 sm:p-4">
          {aberto && (
            <div className="grid gap-4 @[640px]:grid-cols-[minmax(0,1fr)_minmax(13rem,28%)]">
              <div className="min-w-0">
                <div className="mb-3 sm:max-w-xs">
                  <SeletorSegmentado rotulo="Visualização do calendário" opcoes={VISOES} selecionado={visao} aoSelecionar={setVisao} />
                </div>
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                  <h3 aria-live="polite" className="text-sm font-bold first-letter:uppercase sm:text-base">{ehSemana ? intervalo(semana, fimDaSemana) : MES.format(data)}</h3>
                  <div className="flex gap-1">
                    <button type="button" className={BOTAO} onClick={() => navegar(-1)} aria-label="Período anterior"><ChevronLeft size={16} aria-hidden="true" /></button>
                    <button type="button" className={BOTAO} onClick={() => {
                      aoNavegar(hoje);
                      aoSelecionarDia(null);
                    }}>Hoje</button>
                    <button type="button" className={BOTAO} onClick={() => navegar(1)} aria-label="Próximo período" disabled={ehSemana ? fimDaSemana >= hoje : data.getFullYear() * 12 + data.getMonth() >= hoje.getFullYear() * 12 + hoje.getMonth()}><ChevronRight size={16} aria-hidden="true" /></button>
                  </div>
                </div>
                {carregando && <p role="status" className="mb-2 text-sm text-muted-foreground">Carregando registros…</p>}
                {dados === null && (
                  <div className="mb-2 flex flex-wrap items-center gap-2 text-sm">
                    <p role="alert">Falha ao carregar registros.</p>
                    <button type="button" className={BOTAO} onClick={recarregar}>Tentar novamente</button>
                  </div>
                )}
                {dados?.truncada && <p role="status" className="mb-2 text-sm text-muted-foreground">Histórico parcial. Parte dos registros do período ficou fora da consulta.</p>}
                {visao === "sequencias" ? (
                  <div>
                    {dados && porMes.length === 0 && <p className="text-sm text-muted-foreground">Nenhuma sequência de dois ou mais dias nos registros carregados.</p>}
                    <ul className="space-y-1">
                      {porMes.map((grupo) => (
                        <li key={grupo[0].getTime()}>
                          <button type="button" aria-pressed={grupo === ativa} onClick={() => setInicioDaSequencia(grupo[0].getTime())} className={`${BOTAO} w-full flex-wrap justify-between aria-pressed:bg-accent`}>
                            <span>{intervalo(grupo[0], grupo[grupo.length - 1])}</span>
                            <span>{diasEmSequencia(grupo.length, comecaNaBorda(grupo))}</span>
                          </button>
                        </li>
                      ))}
                    </ul>
                    {ativa && <p className="mt-2 text-xs text-muted-foreground" aria-live="polite">Dias com registro em sequência: {ativa.map((dia) => CURTA.format(dia)).join(", ")}.</p>}
                  </div>
                ) : (
                  <>
                    {grade}
                    <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
                      <span className="flex items-center gap-1"><span className="size-1.5 rounded-full bg-primary" /> Dia com registro</span>
                      <span className="flex items-center gap-1"><span className="h-2 w-4 rounded-full bg-(color:--sessao-destaque-borda)" /> Sequência atual</span>
                      <span className="flex items-center gap-1"><span className="h-2 w-4 rounded-full border border-border bg-accent" /> Sequência encerrada</span>
                    </div>
                    <div aria-live="polite" className="mt-3 flex flex-wrap items-center justify-between gap-1 rounded-lg bg-secondary px-3 py-2 text-sm">
                      <strong className="first-letter:uppercase">{DATA.format(data)}</strong>
                      {dados && <span>{tempo === undefined ? (dados.truncada ? "Sem informação na consulta parcial" : "Sem registros") : `Tempo registrado · ${formatarDuracao(tempo)}`}</span>}
                    </div>
                  </>
                )}
              </div>
              <aside aria-label="Resumo das sequências" className="self-start rounded-xl border border-(color:--sessao-destaque-borda) bg-(image:--sessao-destaque-fundo) p-4 text-white">
                <p className="flex items-center gap-2 text-xs font-semibold text-(color:--sessao-destaque-rotulo)"><Moon size={14} aria-hidden="true" /> {recorteAtual ? "Sequência atual" : "Melhor sequência"}</p>
                <p className="mt-1 text-lg font-extrabold tracking-tight">{dados && !dados.truncada ? (recorteAtual ? textoAtual : textoMelhor) : "—"}</p>
                {recorteAtual && <p className="mt-2 border-t border-white/25 pt-2 text-xs">Melhor sequência no período · {dados && !dados.truncada ? textoMelhor : "—"}</p>}
                <p className="mt-2 text-xs text-(color:--sessao-destaque-legenda)">Período consultado: {intervalo(janela.inicio, janela.fim)}</p>
              </aside>
            </div>
          )}
        </div>
      </section>
      <div ref={destinoInline} className={destinoDoGrafico ? "hidden" : "mt-2"} />
      {createPortal(grafico, suporteDoGrafico)}
    </div>
  );
}
