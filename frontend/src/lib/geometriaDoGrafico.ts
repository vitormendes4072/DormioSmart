// UI-43 (etapa 1): a geometria do gráfico "Movimento ao longo do tempo", sem biblioteca.
//
// Até 23/11 o gráfico era do recharts, que sozinho pesava ~111 KB comprimidos no pacote do painel
// (quase metade dele). O desenho é simples o bastante para ser feito à mão, como o da landing, e
// esta parte é a conta pura, testável sem DOM. Ela reproduz o que o gráfico já fazia:
//
// - **Eixo categórico:** cada ponto ocupa a mesma largura, no centro da sua faixa, como o recharts
//   fazia. Uma lacuna de duas horas ocupa uma faixa só, e por isso ela é desenhada (DASH-09).
// - **A linha quebra onde não há intensidade** (`connectNulls={false}`), e a área também.
// - **O limite de movimento sempre aparece** (`ifOverflow="extendDomain"`, DASH-07): o topo do eixo é
//   o maior entre o limite e a maior intensidade.
// - **Lacuna é uma coluna da altura toda**, hachurada no componente.
// - **Ponto com movimento** ganha um marcador.
// - **Horas no eixo:** só de pontos com hora ("sem dados" não), uma por minuto, espaçadas, no máximo
//   `MAX_MARCAS`.
import type { PontoDaSerie } from "./metricas";

const LARGURA = 600;
const ALTURA = 200;
/** Folga acima do maior valor, para a linha não encostar no topo. */
const FOLGA = 1.1;
export const MAX_MARCAS = 6;

type Geometria = {
  /** Um trecho de linha por sequência de pontos com intensidade. */
  linhas: string[];
  /** A área sob cada trecho, até a base. */
  areas: string[];
  pontosDeMovimento: { x: number; y: number }[];
  lacunas: { x: number; largura: number }[];
  yDoLimite: number;
  /** Linhas de grade horizontais. */
  grade: number[];
  /** O centro de cada faixa, na ordem da série. */
  xs: number[];
  marcas: { x: number; rotulo: string }[];
  largura: number;
  altura: number;
};

const arredondar = (v: number) => Math.round(v * 100) / 100;

export function geometria(
  serie: PontoDaSerie[],
  limite: number,
  largura = LARGURA,
  altura = ALTURA,
): Geometria {
  const n = serie.length;
  const faixa = n > 0 ? largura / n : largura;
  const xs = serie.map((_, i) => arredondar((i + 0.5) * faixa));
  const maior = Math.max(limite, ...serie.map((p) => p.intensidade ?? 0));
  const topo = maior > 0 ? maior * FOLGA : 1;
  const y = (v: number) => arredondar(altura - (v / topo) * altura);

  const linhas: string[] = [];
  const areas: string[] = [];
  let trecho: number[] = [];
  const fechar = () => {
    if (trecho.length === 0) return;
    const pts = trecho.map((i) => `${xs[i]} ${y(serie[i].intensidade as number)}`);
    linhas.push("M" + pts.join(" L"));
    areas.push(`M${xs[trecho[0]]} ${altura} L${pts.join(" L")} L${xs[trecho[trecho.length - 1]]} ${altura} Z`);
    trecho = [];
  };
  serie.forEach((p, i) => {
    if (p.intensidade == null) fechar();
    else trecho.push(i);
  });
  fechar();

  const pontosDeMovimento = serie.flatMap((p, i) =>
    p.movimento && p.intensidade != null ? [{ x: xs[i], y: y(p.intensidade) }] : [],
  );
  const lacunas = serie.flatMap((p, i) =>
    p.lacuna ? [{ x: arredondar(xs[i] - faixa * 0.4), largura: arredondar(faixa * 0.8) }] : [],
  );

  // Uma marca por minuto: dois pontos no mesmo minuto dariam "23:00" duas vezes, lado a lado.
  const comHora = serie.flatMap((p, i) =>
    /^\d/.test(p.hora) && (i === 0 || p.hora.slice(0, 5) !== serie[i - 1].hora.slice(0, 5)) ? [i] : []);
  const passo = Math.max(1, Math.ceil(comHora.length / MAX_MARCAS));
  const marcas = comHora
    .filter((_, k) => k % passo === 0)
    .map((i) => ({ x: xs[i], rotulo: serie[i].hora.slice(0, 5) }));

  return {
    linhas,
    areas,
    pontosDeMovimento,
    lacunas,
    yDoLimite: y(limite),
    grade: [0.25, 0.5, 0.75, 1].map((f) => arredondar(altura - f * altura)),
    xs,
    marcas,
    largura,
    altura,
  };
}

/** A faixa (índice da série) sob uma posição horizontal de 0 a 1. */
export function indiceNaPosicao(fracao: number, n: number): number | null {
  if (n === 0 || !Number.isFinite(fracao)) return null;
  return Math.min(n - 1, Math.max(0, Math.floor(fracao * n)));
}
