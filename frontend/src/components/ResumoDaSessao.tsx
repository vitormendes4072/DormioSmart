import type { ReactNode } from "react";

import { calcularCobertura, type Sessao } from "../lib/cobertura";
import {
  calcularMetricas,
  descreverQuando,
  formatarDuracao,
  formatarPorcentagem,
} from "../lib/metricas";

/**
 * O topo do Início: o que a sessão registrou, em quatro frases (UI-40).
 *
 * Cada frase é uma conta que já existia, sem interpretação: nada de nota, de
 * qualidade nem de "você". O que é fórmula fica em "Detalhes técnicos".
 *
 * A parada é contada DENTRO de cada sessão. Em "todas as sessões", a tarde
 * entre duas noites não é o registro parando, e por isso também não entra no
 * "X de Y": ali o denominador vira o número de sessões.
 */
export function ResumoDaSessao({
  sessoes,
  verTudo,
  aparelho,
  metricas,
  children,
}: {
  /** As exibidas: a última, ou todas. Em ordem crescente. */
  sessoes: Sessao[];
  verTudo: boolean;
  aparelho: string;
  metricas: ReturnType<typeof calcularMetricas>;
  /** O seletor de sessão, quando há mais de uma. */
  children?: ReactNode;
}) {
  const { cobertura, fracaoEmMovimento, maiorPeriodoSemMovimentoMs } = metricas;
  const paradas = sessoes
    .flatMap((sessao) => calcularCobertura(sessao.leituras).interrupcoes)
    .map(({ inicio, fim }) => fim - inicio)
    .filter((duracao) => duracao > 0);
  // Sem quebra no meio da duração: "6m" numa linha e "30s" na outra se lê errado.
  const maisLonga = <span className="whitespace-nowrap">{formatarDuracao(Math.max(0, ...paradas))}</span>;

  return (
    <section aria-labelledby="resumo-da-sessao" className="rounded-[14px] border border-border bg-card p-4 shadow-sm sm:p-5">
      <h2 id="resumo-da-sessao" className="break-words text-sm font-semibold text-muted-foreground">
        {verTudo ? `${sessoes.length} sessões` : "Última sessão"} · {aparelho}
      </h2>
      {sessoes.length > 0 && (
        <p className="mt-0.5 text-sm text-foreground">
          {descreverQuando(sessoes[0].inicio, sessoes[sessoes.length - 1].fim)}
        </p>
      )}

      <p className="mt-4 text-xs text-muted-foreground">Registrado</p>
      <p className="text-2xl font-extrabold leading-tight tracking-tight text-foreground sm:text-3xl">
        {formatarDuracao(cobertura.tempoCobertoMs)}
        <span className="text-base font-medium text-muted-foreground">
          {verTudo
            ? ` em ${sessoes.length} sessões`
            : cobertura.janelaMs > 0 ? ` de ${formatarDuracao(cobertura.janelaMs)}` : ""}
        </span>
      </p>

      <ul className="mt-3 space-y-1.5 text-sm text-foreground">
        <li>
          {/* À vista mesmo abaixo dos 5% que abrem o aviso de lacuna. */}
          <p className={paradas.length > 0 ? "font-semibold text-amber-800 dark:text-amber-300" : undefined}>
            {paradas.length === 0
              ? "O registro não parou"
              : paradas.length === 1
                ? <>O registro parou 1 vez, por {maisLonga}</>
                : <>O registro parou {paradas.length} vezes, a mais longa por {maisLonga}</>}
          </p>
        </li>
        <li>
          {fracaoEmMovimento == null
            ? "Sem registro suficiente para calcular o movimento"
            : `Movimento em ${formatarPorcentagem(fracaoEmMovimento * 100)} do tempo registrado`}
        </li>
        {maiorPeriodoSemMovimentoMs != null && (
          // "registrado", e não "houve": a afirmação é sobre o registro. E a
          // conta nunca atravessa uma parada (DASH-09).
          <li>
            Maior período sem movimento registrado:{" "}
            <span className="whitespace-nowrap">{formatarDuracao(maiorPeriodoSemMovimentoMs)}</span>
          </li>
        )}
      </ul>

      {children && <div className="mt-4 border-t border-border pt-3">{children}</div>}
    </section>
  );
}
