import { GEOMETRIA_PADRAO, caminhoEmLoop, gerarSinal, yDoValor } from "../lib/sinal";
import { GRAVIDADE, LIMIAR_DE_MOVIMENTO } from "../types/sleep";

/**
 * Traçado de aceleração animado do hero (UI-15).
 *
 * A landing descrevia um sensor de movimento inteiramente em texto. Este é o
 * único elemento da página que mostra o critério em vez de afirmá-lo:
 * repouso oscilando perto de 9,81 m/s², e eventos rompendo a faixa de
 * 1,2 m/s² — o mesmo limiar que o firmware aplica (DATA-02).
 *
 * ── O RÓTULO NÃO É OPCIONAL ─────────────────────────────────────────────
 *
 * O sinal é sintético e a legenda diz isso, de forma fixa. Um gráfico que se
 * move numa página de produto é lido como telemetria ao vivo; num trabalho
 * cujo escopo é justamente não afirmar mais do que se mede, deixar essa
 * ambiguidade de pé seria um problema na defesa. A mesma regra vale para a
 * demo do dashboard.
 *
 * ── DUAS CAMADAS ────────────────────────────────────────────────────────
 *
 * A de baixo é fixa: eixo de repouso e faixa de limiar não podem rolar, ou
 * deixam de ser referência. A de cima tem o dobro da largura, contém dois
 * períodos do sinal e desliza metade de si mesma em loop — um `translateX`
 * de CSS, sem nenhum JavaScript rodando depois da montagem.
 *
 * `preserveAspectRatio="none"` nas duas faz cada uma mapear suas unidades
 * sobre a mesma largura de pixel, então as camadas continuam alinhadas em
 * qualquer proporção de tela.
 */

const G = GEOMETRIA_PADRAO;

/* Determinístico e constante: calculado uma vez na importação, nunca a cada
   render. O desenho é o mesmo em toda visita — captura de tela reproduzível. */
const CAMINHO = caminhoEmLoop(gerarSinal(), G);

const Y_REPOUSO = yDoValor(GRAVIDADE, G);
const Y_LIMIAR_ACIMA = yDoValor(GRAVIDADE + LIMIAR_DE_MOVIMENTO, G);
const Y_LIMIAR_ABAIXO = yDoValor(GRAVIDADE - LIMIAR_DE_MOVIMENTO, G);

/** Posição vertical em porcentagem, para rotular sobre o desenho em HTML. */
function emPorcentagem(y: number) {
  return `${(y / G.altura) * 100}%`;
}

function Cota({ y, texto }: { y: number; texto: string }) {
  return (
    <span
      className="absolute right-2 -translate-y-1/2 font-mono text-[10px] text-muted-foreground"
      style={{ top: emPorcentagem(y) }}
    >
      {texto}
    </span>
  );
}

export function TracadoDeMovimento({ className = "" }: { className?: string }) {
  return (
    <figure className={className}>
      <div className="w-full overflow-hidden rounded-xl border border-border/70 bg-card">
        {/* Tarja de titulo, como o carimbo de um desenho tecnico. O rotulo do
            eixo morava dentro da area de plotagem e colidia com os picos em
            tela estreita — aqui ele nunca disputa espaco com o sinal. */}
        <div className="border-b border-border/70 px-3 py-1.5">
          <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
            aceleração · m/s²
          </span>
        </div>

        <div className="relative w-full aspect-[4/1] sm:aspect-[8/1]">
          {/* Camada fixa: referência de repouso e faixa de limiar. */}
          <svg
            viewBox={`0 0 ${G.largura} ${G.altura}`}
            preserveAspectRatio="none"
            className="absolute inset-0 h-full w-full"
            aria-hidden
          >
            <rect
              x="0"
              y={Y_LIMIAR_ACIMA}
              width={G.largura}
              height={Y_LIMIAR_ABAIXO - Y_LIMIAR_ACIMA}
              className="fill-primary/[0.06]"
            />
            <line
              x1="0"
              y1={Y_REPOUSO}
              x2={G.largura}
              y2={Y_REPOUSO}
              className="stroke-border"
              vectorEffect="non-scaling-stroke"
            />
            {[Y_LIMIAR_ACIMA, Y_LIMIAR_ABAIXO].map((y) => (
              <line
                key={y}
                x1="0"
                y1={y}
                x2={G.largura}
                y2={y}
                strokeDasharray="5 5"
                className="stroke-primary/40"
                vectorEffect="non-scaling-stroke"
              />
            ))}
          </svg>

          {/* Camada rolante: o traçado. Dobro da largura, dois períodos. */}
          <svg
            viewBox={`0 0 ${2 * G.largura} ${G.altura}`}
            preserveAspectRatio="none"
            width="200%"
            className="tracado-rolagem absolute left-0 top-0 h-full"
            aria-hidden
          >
            <path
              d={CAMINHO}
              fill="none"
              strokeWidth="1.75"
              strokeLinejoin="round"
              strokeLinecap="round"
              className="stroke-primary"
              vectorEffect="non-scaling-stroke"
            />
          </svg>

          {/* Bordas esmaecidas: o recorte vira janela, e não corte seco. */}
          <div className="pointer-events-none absolute inset-y-0 left-0 w-10 bg-gradient-to-r from-card to-transparent" />
          <div className="pointer-events-none absolute inset-y-0 right-0 w-16 bg-gradient-to-l from-card via-card/80 to-transparent" />

          <div className="pointer-events-none absolute inset-0" aria-hidden>
            <Cota y={Y_LIMIAR_ACIMA} texto="+1,2" />
            <Cota y={Y_REPOUSO} texto="9,81" />
            <Cota y={Y_LIMIAR_ABAIXO} texto="−1,2" />
          </div>
        </div>
      </div>

      <figcaption className="mt-2.5 flex flex-wrap items-center gap-x-4 gap-y-1.5 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
        <span className="inline-flex items-center gap-1.5">
          <span className="h-px w-4 bg-primary" />
          magnitude
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2.5 w-4 border-y border-dashed border-primary/60 bg-primary/[0.08]" />
          faixa de repouso
        </span>
        {/* Fixo e não dispensável. Ver a nota no topo do arquivo. */}
        <span className="text-muted-foreground/80">
          ilustração — sinal sintético, não é leitura de sensor
        </span>
      </figcaption>
    </figure>
  );
}
