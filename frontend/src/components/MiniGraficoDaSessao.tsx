import { useId } from "react";

import { geometria } from "../lib/geometriaDoGrafico";
import type { PontoDaSerie } from "../lib/metricas";
import { LIMIAR_DE_MOVIMENTO } from "../types/sleep";

/**
 * O gráfico de movimento de uma sessão, pequeno e sem toque (UI-53), para o cartão do
 * Histórico no celular. É a mesma geometria do "Movimento ao longo do tempo" do Início
 * (`geometriaDoGrafico`): a linha da intensidade, a do limite, os pontos com movimento e
 * os trechos sem registro hachurados. Sem eixo e sem leitura por ponto: para isso, o
 * cartão leva ao Início.
 */
export function MiniGraficoDaSessao({ serie }: { serie: PontoDaSerie[] }) {
  const g = geometria(serie, LIMIAR_DE_MOVIMENTO, 300, 64);
  const hachura = useId();
  const comMovimento = g.pontosDeMovimento.length;
  return (
    <svg data-mini-grafico viewBox={`0 0 ${g.largura} ${g.altura}`} preserveAspectRatio="none"
      role="img" aria-label={`Intensidade do movimento na sessão: ${comMovimento} ${comMovimento === 1 ? "registro" : "registros"} com movimento${g.lacunas.length > 0 ? ", com trechos sem registro" : ""}.`}
      className="block h-16 w-full overflow-visible rounded-xl bg-secondary/60">
      <defs>
        <pattern id={hachura} width="6" height="6" patternUnits="userSpaceOnUse">
          <path d="M-1 1L1 -1M0 6L6 0M5 7L7 5" stroke="var(--muted-foreground)" strokeOpacity={0.55} />
        </pattern>
      </defs>
      {g.lacunas.map((l) => (
        <rect key={l.x} data-lacuna x={l.x} width={l.largura} y={0} height={g.altura} fill={`url(#${hachura})`} />
      ))}
      <line x1={0} x2={g.largura} y1={g.yDoLimite} y2={g.yDoLimite} stroke="var(--chart-movimento)"
        strokeDasharray="4 4" strokeWidth={1} vectorEffect="non-scaling-stroke" />
      {g.linhas.map((d) => (
        <path key={d} d={d} fill="none" stroke="var(--chart-repouso)" strokeWidth={1.5}
          strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
      ))}
      {g.pontosDeMovimento.map((p) => (
        <path key={`${p.x}-${p.y}`} d={`M${p.x} ${p.y}h0`} stroke="var(--chart-movimento)" strokeWidth={4}
          strokeLinecap="round" vectorEffect="non-scaling-stroke" />
      ))}
    </svg>
  );
}
