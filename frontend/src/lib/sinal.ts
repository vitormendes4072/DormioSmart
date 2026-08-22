/**
 * Tracado de aceleracao da landing (UI-15).
 *
 * ── O QUE ISSO E, E O QUE NAO E ─────────────────────────────────────────
 *
 * E uma ILUSTRACAO. O sinal e sintetico, gerado aqui mesmo, e nao tem
 * nenhuma relacao com leitura de sensor. Nao ha telemetria ao vivo na pagina
 * publica, e nao deve haver: a landing inteira e construida sobre nao afirmar
 * mais do que se mede, e um grafico animado sem rotulo passaria exatamente a
 * impressao contraria. Por isso o componente que consome estas funcoes exibe
 * a legenda de "sinal sintetico" de forma fixa, nao dispensavel — a mesma
 * regra que a demo do dashboard segue (`demo.ts`).
 *
 * O que a ilustracao comunica com honestidade e o CRITERIO: repouso oscila
 * perto de 9,81 m/s2, evento de movimento rompe a faixa de 1,2 m/s2. E o
 * mesmo criterio que o firmware aplica (DATA-02) — desenhado, nao alegado.
 *
 * ── POR QUE E DETERMINISTICO ────────────────────────────────────────────
 *
 * Mesma semente, mesmo desenho. O tracado nao muda a cada carregamento, entao
 * captura de tela de devlog e do texto do TCC continua reproduzivel, e o teste
 * pode afirmar propriedades do resultado.
 *
 * ── POR QUE O CAMINHO TEM DOIS PERIODOS ─────────────────────────────────
 *
 * A animacao e um unico `translateX` em CSS, sem JavaScript rodando depois da
 * montagem: nada de requestAnimationFrame, nada de estado de React a 60 fps.
 * Para o loop nao ter emenda visivel, o caminho contem o sinal repetido duas
 * vezes; deslocar exatamente um periodo devolve o desenho a um quadro
 * identico ao inicial. `caminhoEmLoop` garante essa propriedade.
 */
import { GRAVIDADE, LIMIAR_DE_MOVIMENTO } from "../types/sleep";
import { geradorPseudoAleatorio } from "./pseudoAleatorio";

export const PONTOS_PADRAO = 180;
export const SEMENTE_PADRAO = 20260821;

/**
 * Faixas [inicio, fim], em fracao do eixo, onde ha evento de movimento.
 *
 * Nenhuma encosta nas bordas de proposito: a emenda do loop cai em repouso,
 * onde a diferenca entre o ultimo ponto e o primeiro e ruido de baixa
 * amplitude e passa despercebida.
 */
export const EVENTOS_PADRAO: ReadonlyArray<readonly [number, number]> = [
  [0.1, 0.16],
  [0.33, 0.37],
  [0.52, 0.61],
  [0.78, 0.83],
];

export type OpcoesDoSinal = {
  pontos?: number;
  semente?: number;
  eventos?: ReadonlyArray<readonly [number, number]>;
};

/**
 * Gera a magnitude do vetor de aceleracao ponto a ponto, em m/s2.
 *
 * Repouso: ruido de baixa amplitude em torno de 9,81, sempre abaixo do
 * limiar. Evento: envelope senoidal dentro da propria faixa — movimento na
 * cama comeca, cresce e termina, nao liga e desliga em degrau.
 */
export function gerarSinal(opcoes: OpcoesDoSinal = {}): number[] {
  const {
    pontos = PONTOS_PADRAO,
    semente = SEMENTE_PADRAO,
    eventos = EVENTOS_PADRAO,
  } = opcoes;

  const total = Math.max(2, Math.floor(pontos));
  const aleatorio = geradorPseudoAleatorio(semente);
  const valores: number[] = [];

  for (let i = 0; i < total; i++) {
    const fracao = i / total;
    const faixa = eventos.find(([a, b]) => fracao >= a && fracao <= b);

    let desvio: number;
    if (faixa) {
      const [a, b] = faixa;
      const progresso = (fracao - a) / Math.max(b - a, 1e-6);
      const envelope = Math.sin(Math.PI * progresso);
      const pico = LIMIAR_DE_MOVIMENTO + 0.4 + aleatorio() * 1.8;
      desvio = pico * envelope + aleatorio() * 0.2;
    } else {
      // Teto do repouso fica confortavelmente abaixo do limiar: a faixa de
      // 1,2 m/s2 desenhada no grafico so e rompida por evento.
      desvio = aleatorio() * (LIMIAR_DE_MOVIMENTO * 0.3);
    }

    const orientacao = aleatorio() < 0.5 ? -1 : 1;
    valores.push(GRAVIDADE + orientacao * desvio);
  }

  return valores;
}

/** Sistema de coordenadas do desenho. `largura` cobre UM periodo do sinal. */
export type Geometria = {
  largura: number;
  altura: number;
  /** Quantos m/s2 vao do centro ate a borda vertical. */
  amplitude: number;
};

export const GEOMETRIA_PADRAO: Geometria = { largura: 600, altura: 120, amplitude: 4 };

/** Converte uma magnitude em m/s2 para a coordenada y do viewBox. */
export function yDoValor(valor: number, g: Geometria = GEOMETRIA_PADRAO): number {
  const meio = g.altura / 2;
  const y = meio - ((valor - GRAVIDADE) / g.amplitude) * meio;
  // Grampeado: valor extremo encosta na borda em vez de desenhar fora dela.
  return Number(Math.min(g.altura, Math.max(0, y)).toFixed(2));
}

/**
 * Caminho SVG com DOIS periodos do sinal, para o loop sem emenda.
 *
 * O ponto de indice `i + n` tem o mesmo `y` do ponto `i` e o `x` deslocado de
 * exatamente `largura`. Logo, `translateX(-largura)` devolve um quadro
 * identico ao inicial — e a animacao pode reiniciar sem salto.
 */
export function caminhoEmLoop(valores: number[], g: Geometria = GEOMETRIA_PADRAO): string {
  const n = valores.length;
  if (n === 0) return "";

  const passo = g.largura / n;
  const partes: string[] = [];

  for (let i = 0; i <= 2 * n; i++) {
    const x = Number((i * passo).toFixed(2));
    const y = yDoValor(valores[i % n], g);
    partes.push(`${i === 0 ? "M" : "L"}${x},${y}`);
  }

  return partes.join(" ");
}
