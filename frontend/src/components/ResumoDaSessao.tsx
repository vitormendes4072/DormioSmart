import { useState, type ReactNode } from "react";

import { CartaoDeMetrica, CartaoEmDestaque } from "./CartoesDeRegistro";
import { COLUNAS_DO_INICIO } from "./colunasDoInicio";
import { DetalheDoTempoRegistrado, hora } from "./DetalheDoTempoRegistrado";

import { calcularCobertura, type Sessao } from "../lib/cobertura";
import {
  calcularMetricas,
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
  metricas,
  titulo = "Seus registros",
  idDoTitulo,
  lateral,
  children,
}: {
  /** As exibidas: a última, ou todas. Em ordem crescente. */
  sessoes: Sessao[];
  verTudo: boolean;
  metricas: ReturnType<typeof calcularMetricas>;
  titulo?: string;
  /** UI-49: o título está fora (no topo do Início); a seção só aponta para ele. */
  idDoTitulo?: string;
  /** O seletor de sessão, quando há mais de uma. */
  children?: ReactNode;
  /** UI-48: em tela larga, o que vai na mesma linha dos cartões (o gráfico de tempo por dia). */
  lateral?: ReactNode;
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
    ? "Sem pausas"
    : `${totalParadas} ${totalParadas === 1 ? "pausa" : "pausas"}`;
  // UI-51: o mesmo texto do celular de exemplo da landing. A data e a janela
  // ficam no detalhe, que o cartão abre.
  const [detalheAberto, setDetalheAberto] = useState(false);
  const quando = sessoes.length === 0
    ? null
    : verTudo
      ? `${sessoes.length} sessões`
      : `${hora(sessoes[0].inicio)} às ${hora(sessoes[sessoes.length - 1].fim)}`;

  const cartoes = (
    <>
      <CartaoEmDestaque
        rotulo="Tempo registrado"
        valor={formatarDuracao(cobertura.tempoCobertoMs)}
        aoAbrir={sessoes.length > 0 ? () => setDetalheAberto(true) : undefined}
      >
        {[quando, sessoes.length > 0 ? "ver detalhes" : null].filter(Boolean).join(" · ")}
      </CartaoEmDestaque>
      {detalheAberto && (
        <DetalheDoTempoRegistrado
          sessoes={sessoes}
          verTudo={verTudo}
          registradoMs={cobertura.tempoCobertoMs}
          aoFechar={() => setDetalheAberto(false)}
        />
      )}

      <ul aria-label="Métricas da sessão" className={`grid gap-2 min-[360px]:grid-cols-3 ${lateral ? "flex-1" : ""}`}>
        <CartaoDeMetrica valor={movimento ?? "—"}>
          <p>
            {movimento == null
              ? "Sem registro suficiente para calcular o movimento"
              : "Com movimento no tempo registrado"}
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
          {totalParadas > 0 && (
            <p className="font-semibold text-amber-800 dark:text-amber-300">
              {totalParadas === 1 ? "Duração:" : "Maior pausa:"} {maisLonga}
            </p>
          )}
        </CartaoDeMetrica>
      </ul>
    </>
  );

  return (
    <section aria-labelledby={idDoTitulo ?? "resumo-da-sessao"} data-resumo-da-sessao className="space-y-3">
      {!idDoTitulo && (
        <h1 id="resumo-da-sessao" className="text-2xl font-extrabold tracking-tight text-foreground sm:text-[27px]">
          {titulo}
        </h1>
      )}

      {lateral ? (
        // A coluna dos cartões e o gráfico ao lado crescem juntos: começam e terminam na mesma altura.
        <div data-linha-dos-cartoes className={`grid ${COLUNAS_DO_INICIO} gap-3.5`}>
          <div className="flex min-w-0 flex-col gap-3">{cartoes}</div>
          {lateral}
        </div>
      ) : cartoes}

      {children && <div className="pt-1">{children}</div>}
    </section>
  );
}
