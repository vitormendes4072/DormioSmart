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
 * Conta só lacuna MATERIAL — a que significa leitura perdida (ver
 * `lib/cobertura.ts`). A versão anterior somava também o jitter de rede, e
 * podia disparar anunciando "há 0 trechos sem leitura nenhuma": a fração caía
 * abaixo do limiar por acúmulo de décimos de segundo, sem que existisse buraco
 * algum para citar.
 *
 * O limiar de 5% é folgado de propósito: o que se quer marcar é o buraco que
 * muda a leitura dos números, não todo desvio de cadência.
 */

const PERDA_TOLERAVEL = 0.05;

export function AvisoDeLacuna({ cobertura }: { cobertura: Cobertura }) {
  if (cobertura.janelaMs <= 0) return null;

  const perdido = cobertura.lacunasMateriais.reduce((s, l) => s + (l.fim - l.inicio), 0);
  if (perdido <= 0) return null;
  if (perdido / cobertura.janelaMs < PERDA_TOLERAVEL) return null;

  const maior = cobertura.lacunasMateriais.reduce((m, l) => Math.max(m, l.fim - l.inicio), 0);

  return (
    <div className="flex gap-3 rounded-xl border border-amber-500/40 bg-amber-500/5 p-4">
      <AlertTriangle className="w-5 h-5 flex-shrink-0 text-amber-500" aria-hidden />
      <div className="text-sm text-muted-foreground space-y-1.5">
        <p className="font-semibold text-foreground">
          Faltou medição em {formatarDuracao(perdido)} desta janela.
        </p>
        <p>
          {cobertura.lacunasMateriais.length === 1
            ? "Há um trecho sem leitura nenhuma"
            : `Há ${cobertura.lacunasMateriais.length} trechos sem leitura nenhuma`}
          {maior > 0 ? `, o maior de ${formatarDuracao(maior)}` : ""}. Os números abaixo
          valem para o tempo <strong className="font-semibold">que foi medido</strong> —
          nada se afirma sobre o resto.
          {cobertura.cadenciaInferida
            ? " A duração das leituras que não a declaram foi estimada pelo intervalo entre elas."
            : ""}
        </p>
      </div>
    </div>
  );
}
