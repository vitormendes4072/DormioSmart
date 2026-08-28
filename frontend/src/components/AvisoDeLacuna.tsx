import { AlertTriangle } from "lucide-react";

import type { Cobertura } from "../lib/cobertura";
import { formatarDuracao } from "../lib/metricas";

/**
 * A coleta teve buracos? (DASH-09)
 *
 * Aparece ANTES dos números, e não depois, porque é o que decide se eles
 * significam alguma coisa. Uma captação com 3% de cobertura produz métricas
 * que parecem tão sólidas quanto as de uma captação completa.
 *
 * O limiar de 95% é folgado de propósito: arredondamento e jitter de rede
 * produzem lacunas de segundos que não são perda real. O que se quer marcar é
 * o buraco que muda a leitura dos números.
 */

const COBERTURA_ACEITAVEL = 0.95;

export function AvisoDeLacuna({ cobertura }: { cobertura: Cobertura }) {
  if (cobertura.janelaMs <= 0) return null;

  const fracao = cobertura.tempoCobertoMs / cobertura.janelaMs;
  if (fracao >= COBERTURA_ACEITAVEL) return null;

  const perdido = cobertura.janelaMs - cobertura.tempoCobertoMs;
  const maior = cobertura.lacunas.reduce((m, l) => Math.max(m, l.fim - l.inicio), 0);

  return (
    <div className="flex gap-3 rounded-xl border border-amber-500/40 bg-amber-500/5 p-4">
      <AlertTriangle className="w-5 h-5 flex-shrink-0 text-amber-500" aria-hidden />
      <div className="text-sm text-muted-foreground space-y-1.5">
        <p className="font-semibold text-foreground">
          Faltou medição em {formatarDuracao(perdido)} desta janela.
        </p>
        <p>
          {cobertura.lacunas.length === 1
            ? "Há um trecho sem leitura nenhuma"
            : `Há ${cobertura.lacunas.length} trechos sem leitura nenhuma`}
          {maior > 0 ? `, o maior de ${formatarDuracao(maior)}` : ""}. Os números abaixo
          valem para o tempo <strong className="font-semibold">que foi medido</strong> —
          nada se afirma sobre o resto.
          {cobertura.cadenciaInferida
            ? " A duração de cada leitura foi estimada pelo intervalo entre elas, porque o dispositivo não a declarou."
            : ""}
        </p>
      </div>
    </div>
  );
}
