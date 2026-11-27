import { useId, useState } from "react";

import { CartaoDeMetrica } from "./CartoesDeRegistro";
import { GraficoDeMovimento } from "./GraficoDeMovimento";

import { formatarDuracao, formatarPorcentagem, type PontoDaSerie } from "../lib/metricas";
import { escalaEmHoras, resumirPeriodo, rotuloVisivel, type ParteDaSessao, type SessaoDoPeriodo } from "../lib/resumoDoPeriodo";
import { LIMIAR_DE_MOVIMENTO } from "../types/sleep";

const DIA = new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "2-digit" });
const DIA_E_HORA = new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
const ALTURA = 144;
const LARGURA = 100;
const MINIMO_DE_POSICOES = 7;

/** Barra com o topo arredondado, do chão até `topo` (coordenadas do SVG). */
function contorno(indice: number, topo: number, parte = 0, partes = 1) {
  // Com mais de um aparelho, as barras dividem a mesma faixa de 50, com 4 de folga entre elas.
  const largura = (50 - 4 * (partes - 1)) / partes;
  const esquerda = indice * LARGURA + 25 + parte * (largura + 4);
  const direita = esquerda + largura;
  const raio = Math.min(largura / 2, 9, ALTURA - topo);
  return ["M", esquerda, ALTURA, "V", topo + raio, "Q", esquerda, topo, esquerda + raio, topo,
    "H", direita - raio, "Q", direita, topo, direita, topo + raio, "V", ALTURA, "Z"].join(" ");
}

function descrever(sessao: SessaoDoPeriodo): string {
  if (sessao.partes && sessao.partes.length > 1) {
    return `${sessao.partes.length} aparelhos: ` + sessao.partes.map((parte) => `${parte.rotulo}, ${descrever({ ...parte, chave: "", inicio: 0, fim: 0 })}`).join("; ");
  }
  const registrado = formatarDuracao(sessao.tempo);
  return sessao.periodo === null ? `${registrado} registrados` : `${registrado} registrados de ${formatarDuracao(sessao.periodo)}`;
}

/**
 * O topo do Histórico (UI-52): os números do período escolhido e um gráfico dele.
 *
 * O gráfico tem uma barra por sessão, da mais antiga à mais recente. A parte cheia é o
 * tempo registrado e a parte clara, o que faltou entre o primeiro e o último registro.
 * Tocar numa barra leva à sessão na lista. Em "Últimas 24 horas", com um aparelho só, o
 * gráfico é o de movimento do Início, porque uma ou duas barras não dizem nada.
 */
export function ResumoDoPeriodo({ sessoes, parcial = false, movimento, aoEscolherSessao }: {
  /** As sessões do período (sem as de bancada), em qualquer ordem. */
  sessoes: readonly SessaoDoPeriodo[];
  /** A consulta bateu no teto: o período pode estar incompleto. */
  parcial?: boolean;
  /** Em "Últimas 24 horas", a série de movimento do aparelho; ausente, ficam as barras. */
  movimento?: PontoDaSerie[];
  aoEscolherSessao?: (chave: string) => void;
}) {
  const titulo = useId();
  const resumo = resumirPeriodo(sessoes);
  const porcentagem = resumo.fracaoRegistrada === null ? "—" : formatarPorcentagem(resumo.fracaoRegistrada * 100);

  return (
    <section aria-label="Resumo do período" data-resumo-do-periodo className="space-y-3">
      <ul aria-label="Números do período" className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <CartaoDeMetrica valor={resumo.sessoes}>
          <p>{resumo.sessoes === 1 ? "Sessão" : "Sessões"}</p>
          {resumo.comVariosAparelhos > 0 && (
            <p data-varios-aparelhos className="text-[11px]">
              {resumo.comVariosAparelhos === 1 ? "1 registrada" : `${resumo.comVariosAparelhos} registradas`} com mais de um aparelho
            </p>
          )}
        </CartaoDeMetrica>
        <CartaoDeMetrica valor={formatarDuracao(resumo.tempoMs)}><p>Tempo registrado</p></CartaoDeMetrica>
        <CartaoDeMetrica valor={resumo.mediaMs === null ? "—" : formatarDuracao(resumo.mediaMs)}><p>Média por sessão</p></CartaoDeMetrica>
        <CartaoDeMetrica valor={porcentagem}><p>Do período foi registrado</p></CartaoDeMetrica>
      </ul>

      <figure aria-labelledby={titulo} className="min-w-0 rounded-2xl border border-border bg-card px-3 py-3 shadow-sm sm:px-4">
        <h2 id={titulo} className="text-sm font-extrabold tracking-tight sm:text-base">
          {movimento ? "Movimento nas últimas 24 horas" : "Tempo registrado por sessão"}
        </h2>
        {parcial && (
          <p role="status" className="mt-1 text-xs font-semibold text-muted-foreground">
            Período incompleto: há mais registros do que esta tela consegue carregar.
          </p>
        )}
        {movimento
          ? <div className="mt-3 h-40 sm:h-56"><GraficoDeMovimento serie={movimento} limite={LIMIAR_DE_MOVIMENTO} /></div>
          : <BarrasDasSessoes sessoes={sessoes} mediaMs={resumo.mediaMs} aoEscolherSessao={aoEscolherSessao} />}
      </figure>
    </section>
  );
}

function BarrasDasSessoes({ sessoes, mediaMs, aoEscolherSessao }: {
  sessoes: readonly SessaoDoPeriodo[];
  mediaMs: number | null;
  aoEscolherSessao?: (chave: string) => void;
}) {
  const [inspecionada, setInspecionada] = useState<number | null>(null);
  const ordem = [...sessoes].sort((a, b) => a.inicio - b.inicio);
  const total = ordem.length;
  // Com poucas sessões, a barra não estica: pelo menos 7 posições, e as sessões à direita,
  // a mais recente no fim, como numa linha do tempo.
  const posicoes = Math.max(MINIMO_DE_POSICOES, total);
  const vazias = posicoes - total;
  const largura = posicoes * LARGURA;
  const { topoMs, ticks } = escalaEmHoras(Math.max(0, ...ordem.flatMap((s) => [s, ...(s.partes ?? [])])
    .map((s) => Math.max(s.tempo, s.periodo ?? 0))));
  // A legenda de cores só existe quando alguma barra tem mais de um aparelho.
  const aparelhos = [...new Map(ordem.flatMap((s) => (s.partes && s.partes.length > 1 ? s.partes : []))
    .map((parte) => [parte.rotulo, parte.cor])).entries()];
  const y = (ms: number) => ALTURA * (1 - ms / topoMs);
  const temFalta = ordem.some((s) => s.periodo !== null && s.periodo > s.tempo);
  const dica = inspecionada === null ? null : ordem[inspecionada];

  return (
    <>
      <div className="mt-3 grid grid-cols-[1.75rem_minmax(0,1fr)]">
        <div aria-hidden="true" className="relative h-36 text-[10px] tabular-nums text-muted-foreground">
          {ticks.map((valor, i) => (
            <span key={valor} className="absolute right-2 -translate-y-1/2" style={{ top: i * 100 / 3 + "%" }}>{valor}h</span>
          ))}
        </div>
        <div className="relative min-w-0">
          <svg aria-hidden="true" className="pointer-events-none absolute inset-0 h-36 w-full overflow-visible"
            viewBox={`0 0 ${largura} ${ALTURA}`} preserveAspectRatio="none">
            {ticks.map((valor) => (
              <line key={valor} x1="0" x2={largura} y1={y(valor * 3_600_000)} y2={y(valor * 3_600_000)}
                className="stroke-border" vectorEffect="non-scaling-stroke" />
            ))}
            {ordem.map((sessao, i) => (
              <g key={sessao.chave} data-barra={sessao.chave} className={inspecionada !== null && inspecionada !== i ? "opacity-50" : undefined}>
                {(sessao.partes && sessao.partes.length > 1 ? sessao.partes : [null]).map((parte, p, todas) => {
                  const medida: Pick<ParteDaSessao, "tempo" | "periodo"> = parte ?? sessao;
                  return (
                    <g key={parte?.rotulo ?? "sessao"} data-parte={parte?.rotulo}>
                      {medida.periodo !== null && medida.periodo > medida.tempo && (
                        <path data-sem-registro d={contorno(vazias + i, y(medida.periodo), p, todas.length)} className="fill-muted-foreground/25" />
                      )}
                      <path data-registrado d={contorno(vazias + i, y(medida.tempo), p, todas.length)}
                        className={parte ? undefined : "fill-primary"} style={parte ? { fill: parte.cor } : undefined} />
                    </g>
                  );
                })}
              </g>
            ))}
            {mediaMs !== null && total > 1 && (
              <line data-media x1="0" x2={largura} y1={y(mediaMs)} y2={y(mediaMs)} className="stroke-muted-foreground"
                strokeDasharray="4 4" vectorEffect="non-scaling-stroke" />
            )}
          </svg>
          <div className="relative grid" style={{ gridTemplateColumns: `repeat(${posicoes}, minmax(0, 1fr))` }}>
            {vazias > 0 && <span aria-hidden="true" style={{ gridColumn: `span ${vazias}` }} />}
            {ordem.map((sessao, i) => (
              <button
                key={sessao.chave}
                type="button"
                aria-label={`${DIA_E_HORA.format(sessao.inicio)}, ${descrever(sessao)}`}
                onPointerEnter={(evento) => { if (evento.pointerType === "mouse") setInspecionada(i); }}
                onPointerLeave={(evento) => { if (evento.pointerType === "mouse") setInspecionada(null); }}
                onFocus={() => setInspecionada(i)}
                onBlur={() => setInspecionada(null)}
                onClick={() => aoEscolherSessao?.(sessao.chave)}
                className="relative flex min-w-0 cursor-pointer items-end justify-center rounded-sm pt-36 text-[11px] font-semibold text-muted-foreground focus-visible:z-10 focus-visible:outline-2 focus-visible:outline-ring"
              >
                <span aria-hidden="true" className="block truncate pt-1.5">{rotuloVisivel(i, total) ? DIA.format(sessao.inicio) : " "}</span>
              </button>
            ))}
          </div>
          {dica && (
            <div role="tooltip" aria-hidden="true"
              className="pointer-events-none absolute top-2 z-20 -translate-x-1/2 whitespace-nowrap rounded-lg border border-border bg-card px-2 py-1 text-xs text-foreground shadow-md"
              style={{ left: `clamp(5rem, ${(vazias + inspecionada! + 0.5) * 100 / posicoes}%, calc(100% - 5rem))` }}>
              <strong>{DIA_E_HORA.format(dica.inicio)}</strong> · {descrever(dica)}
            </div>
          )}
        </div>
      </div>
      <p className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
        {aparelhos.length > 0
          ? aparelhos.map(([rotulo, cor]) => (
            <span key={rotulo} data-legenda-aparelho className="flex items-center gap-1.5">
              <span aria-hidden="true" className="size-2.5 rounded-sm" style={{ background: cor }} /> {rotulo}
            </span>
          ))
          : <span className="flex items-center gap-1.5"><span aria-hidden="true" className="size-2.5 rounded-sm bg-primary" /> Registrado</span>}
        {temFalta && <span className="flex items-center gap-1.5"><span aria-hidden="true" className="size-2.5 rounded-sm bg-muted-foreground/25" /> Sem registro</span>}
        {mediaMs !== null && total > 1 && <span className="flex items-center gap-1.5"><span aria-hidden="true" className="w-4 border-t border-dashed border-current" /> Média</span>}
        {aoEscolherSessao && <span>Toque numa barra para ver a sessão</span>}
      </p>
    </>
  );
}
