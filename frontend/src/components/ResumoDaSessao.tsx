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
  const janela = verTudo
    ? `em ${sessoes.length} sessões`
    : cobertura.janelaMs > 0 ? `de ${formatarDuracao(cobertura.janelaMs)}` : null;
  const quando = sessoes.length > 0
    ? descreverQuando(sessoes[0].inicio, sessoes[sessoes.length - 1].fim)
    : null;

  return (
    <section aria-labelledby="resumo-da-sessao" className="space-y-3">
      <div className="flex flex-col gap-1">
        <h1 className="order-2 text-2xl font-extrabold tracking-tight text-foreground sm:text-[27px]">
          Seus registros
        </h1>
        <h2 id="resumo-da-sessao" className="order-1 wrap-anywhere text-[11px] font-extrabold uppercase tracking-wider text-primary">
          {verTudo ? `${sessoes.length} sessões` : "Última sessão"} · {aparelho}
        </h2>
      </div>

      <div
        role="group"
        aria-labelledby="tempo-registrado"
        className="relative overflow-hidden rounded-2xl border border-(color:--sessao-destaque-borda) bg-(image:--sessao-destaque-fundo) p-4 text-white shadow-md sm:p-5"
      >
        <span aria-hidden="true" className="pointer-events-none absolute -top-20 -right-10 size-44 rounded-full bg-(image:--sessao-destaque-brilho)" />
        <p id="tempo-registrado" className="text-[11px] font-extrabold uppercase tracking-widest text-(color:--sessao-destaque-rotulo)">
          Registrado
        </p>
        <p className="mt-1">
          <strong className="block text-4xl leading-tight font-extrabold tracking-tight sm:text-[42px]">
            {formatarDuracao(cobertura.tempoCobertoMs)}
          </strong>
          <span className="block text-sm text-(color:--sessao-destaque-legenda)">
            {" "}{[janela, quando].filter(Boolean).join(" · ")}
          </span>
        </p>
      </div>

      <ul aria-label="Métricas da sessão" className="grid gap-2 min-[360px]:grid-cols-3">
        <CartaoDeMetrica titulo="Movimento">
          <p>
            {fracaoEmMovimento == null
              ? "Sem registro suficiente para calcular o movimento"
              : <>Movimento em <strong>{formatarPorcentagem(fracaoEmMovimento * 100)}</strong> do tempo registrado</>}
          </p>
        </CartaoDeMetrica>
        <CartaoDeMetrica titulo="Maior período sem movimento">
          <p>
            {maiorPeriodoSemMovimentoMs == null
              ? "Sem registro suficiente"
              : <>Maior período sem movimento registrado:{" "}
                <strong className="whitespace-nowrap">{formatarDuracao(maiorPeriodoSemMovimentoMs)}</strong></>}
          </p>
        </CartaoDeMetrica>
        <CartaoDeMetrica titulo="Paradas">
          {/* À vista mesmo abaixo dos 5% que abrem o aviso de lacuna. */}
          <p className={paradas.length > 0 ? "font-semibold text-amber-800 dark:text-amber-300" : undefined}>
            {paradas.length === 0
              ? "O registro não parou"
              : paradas.length === 1
                ? <>O registro parou 1 vez, por {maisLonga}</>
                : <>O registro parou {paradas.length} vezes, a mais longa por {maisLonga}</>}
          </p>
        </CartaoDeMetrica>
      </ul>

      {children && <div className="pt-1">{children}</div>}
    </section>
  );
}

function CartaoDeMetrica({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <li className="min-w-0 space-y-1.5 rounded-2xl border border-border bg-card p-2.5 text-xs leading-snug text-foreground sm:p-4 sm:text-sm">
      <h3 className="text-[10px] font-extrabold uppercase tracking-wide text-muted-foreground sm:text-xs">
        {titulo}
      </h3>
      {children}
    </li>
  );
}
