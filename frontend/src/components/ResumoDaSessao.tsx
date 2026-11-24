import type { ReactNode } from "react";

import { CartaoDeMetrica, CartaoEmDestaque, EtiquetaDeRegistro } from "./CartoesDeRegistro";

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
  const movimento = fracaoEmMovimento == null ? null : formatarPorcentagem(fracaoEmMovimento * 100);
  const maiorPeriodo = maiorPeriodoSemMovimentoMs == null ? null : formatarDuracao(maiorPeriodoSemMovimentoMs);
  const totalParadas = paradas.length;
  const valorDeParadas = totalParadas === 0
    ? "Não parou"
    : `Parou ${totalParadas} ${totalParadas === 1 ? "vez" : "vezes"}`;
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
        <h2 id="resumo-da-sessao" className="order-1 leading-none">
          <EtiquetaDeRegistro>{verTudo ? `${sessoes.length} sessões` : "Última sessão"} · {aparelho}</EtiquetaDeRegistro>
        </h2>
      </div>

      <CartaoEmDestaque rotulo="Registrado" valor={formatarDuracao(cobertura.tempoCobertoMs)}>
        {[janela, quando].filter(Boolean).join(" · ")}
      </CartaoEmDestaque>

      <ul aria-label="Métricas da sessão" className="grid gap-2 min-[360px]:grid-cols-3">
        <CartaoDeMetrica valor={movimento ?? "—"}>
          <p>
            {movimento == null
              ? "Sem registro suficiente para calcular o movimento"
              : `Movimento em ${movimento} do tempo registrado`}
          </p>
        </CartaoDeMetrica>
        <CartaoDeMetrica valor={maiorPeriodo ?? "—"}>
          <p>
            {maiorPeriodo == null
              ? "Sem registro suficiente"
              // O valor já está grande no cartão: aqui, só o rótulo, sem repetir o número.
              : "Maior período sem movimento registrado"}
          </p>
        </CartaoDeMetrica>
        <CartaoDeMetrica valor={valorDeParadas}>
          {/* À vista mesmo abaixo dos 5% que abrem o aviso de lacuna. */}
          <p className={totalParadas > 0 ? "font-semibold text-amber-800 dark:text-amber-300" : undefined}>
            {totalParadas === 0
              ? "O registro não parou"
              : totalParadas === 1
                ? <>O registro parou 1 vez, por {maisLonga}</>
                : <>O registro parou {totalParadas} vezes, a mais longa por {maisLonga}</>}
          </p>
        </CartaoDeMetrica>
      </ul>

      {children && <div className="pt-1">{children}</div>}
    </section>
  );
}
