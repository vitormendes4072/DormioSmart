import { useId, useState, type KeyboardEvent, type PointerEvent } from "react";

import { geometria, indiceNaPosicao } from "../lib/geometriaDoGrafico";
import { formatarDuracao, type PontoDaSerie } from "../lib/metricas";

/**
 * O gráfico "Movimento ao longo do tempo", desenhado à mão em SVG (UI-43, etapa 1).
 *
 * Substitui o recharts, que pesava ~111 KB comprimidos no painel, com o mesmo comportamento: a linha
 * da intensidade, a área sob ela, o marcador em cada ponto com movimento, a linha tracejada do limite
 * (DASH-07), as colunas hachuradas das lacunas (DASH-09) e, ao passar o dedo ou o mouse, o horário e
 * "Movimento" ou "Repouso", por escrito (a cor nunca é o único sinal). As setas do teclado também
 * percorrem os pontos, o que o gráfico anterior não fazia.
 *
 * O SVG estica na largura (`preserveAspectRatio="none"`); traços e marcadores usam
 * `vector-effect: non-scaling-stroke` para não deformar. As horas do eixo são HTML, fora do SVG,
 * para o texto não esticar.
 */
const COR_MOVIMENTO = "var(--chart-movimento)";
const COR_REPOUSO = "var(--chart-repouso)";

export function GraficoDeMovimento({ serie, limite }: { serie: PontoDaSerie[]; limite: number }) {
  const g = geometria(serie, limite);
  const gradiente = useId();
  const hachura = useId();
  const [ativo, setAtivo] = useState<number | null>(null);
  const comMovimento = g.pontosDeMovimento.length;

  function aoMover(e: PointerEvent<HTMLDivElement>) {
    const r = e.currentTarget.getBoundingClientRect();
    setAtivo(indiceNaPosicao((e.clientX - r.left) / r.width, serie.length));
  }

  function aoTeclar(e: KeyboardEvent<HTMLDivElement>) {
    if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
    e.preventDefault();
    const passo = e.key === "ArrowRight" ? 1 : -1;
    setAtivo((i) => Math.min(serie.length - 1, Math.max(0, (i ?? (passo > 0 ? -1 : serie.length)) + passo)));
  }

  const ponto = ativo === null ? null : serie[ativo];
  const pct = (x: number) => `${(x / g.largura) * 100}%`;

  return (
    <div className="flex h-full flex-col">
      <div
        className="relative min-h-0 flex-1 outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-md"
        tabIndex={0}
        aria-label="Percorrer os registros do gráfico com as setas"
        onPointerMove={aoMover}
        onPointerLeave={() => setAtivo(null)}
        onBlur={() => setAtivo(null)}
        onKeyDown={aoTeclar}
      >
        <svg
          viewBox={`0 0 ${g.largura} ${g.altura}`}
          preserveAspectRatio="none"
          className="h-full w-full overflow-visible"
          role="img"
          aria-label={`Intensidade do movimento em ${serie.length} pontos, ${comMovimento} com movimento, com a linha do limite de movimento.`}
        >
          <defs>
            <linearGradient id={gradiente} x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor={COR_REPOUSO} stopOpacity={0.26} />
              <stop offset="100%" stopColor={COR_REPOUSO} stopOpacity={0} />
            </linearGradient>
            <pattern id={hachura} width="6" height="6" patternUnits="userSpaceOnUse">
              <rect width="6" height="6" fill="var(--muted-foreground)" fillOpacity={0.12} />
              <path d="M-1 1L1 -1M0 6L6 0M5 7L7 5" stroke="var(--muted-foreground)" strokeOpacity={0.65} />
            </pattern>
          </defs>
          {g.grade.map((yy) => (
            <line key={yy} data-grade x1={0} x2={g.largura} y1={yy} y2={yy} stroke="var(--border)"
              strokeDasharray="3 5" vectorEffect="non-scaling-stroke" />
          ))}
          {ativo !== null && (
            <rect x={g.xs[ativo] - g.largura / serie.length / 2} width={g.largura / serie.length} y={0}
              height={g.altura} fill="var(--secondary)" fillOpacity={0.5} />
          )}
          {g.lacunas.map((l) => (
            <rect key={l.x} data-lacuna x={l.x} width={l.largura} y={0} height={g.altura} rx={3}
              fill={`url(#${hachura})`} />
          ))}
          {g.areas.map((d) => <path key={d} data-area d={d} fill={`url(#${gradiente})`} stroke="none" />)}
          <line data-limite x1={0} x2={g.largura} y1={g.yDoLimite} y2={g.yDoLimite} stroke={COR_MOVIMENTO}
            strokeDasharray="5 4" strokeWidth={1.5} vectorEffect="non-scaling-stroke" />
          {g.linhas.map((d) => (
            <path key={d} data-linha d={d} fill="none" stroke={COR_REPOUSO} strokeWidth={2.5}
              strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
          ))}
          {g.pontosDeMovimento.map((p) => (
            <path key={`${p.x}-${p.y}`} data-movimento d={`M${p.x} ${p.y}h0`} stroke={COR_MOVIMENTO}
              strokeWidth={6} strokeLinecap="round" vectorEffect="non-scaling-stroke" />
          ))}
        </svg>
        {ponto && ativo !== null && (
          <div
            role="status"
            className="pointer-events-none absolute top-1 z-10 -translate-x-1/2 rounded-xl border border-border bg-card px-3 py-2 text-sm shadow-2xl"
            style={{ left: `clamp(56px, ${pct(g.xs[ativo])}, calc(100% - 56px))` }}
          >
            {ponto.lacuna ? (
              <>
                <p className="font-semibold text-foreground">Sem registro</p>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {ponto.duracaoDaLacunaMs == null ? "trecho sem registro" : `${formatarDuracao(ponto.duracaoDaLacunaMs)} sem registro`}
                </p>
              </>
            ) : (
              <>
                <p className="mb-0.5 text-xs text-muted-foreground">{ponto.hora}</p>
                <p className="font-semibold text-foreground">
                  {ponto.intensidade == null ? "sem registro" : ponto.movimento ? "Movimento" : "Repouso"}
                </p>
              </>
            )}
          </div>
        )}
      </div>
      <div className="relative mt-2 h-4 text-[11px] text-muted-foreground" aria-hidden="true">
        {g.marcas.map((m) => (
          <span key={m.x} className="absolute -translate-x-1/2 tabular-nums" style={{ left: pct(m.x) }}>
            {m.rotulo}
          </span>
        ))}
      </div>
    </div>
  );
}
