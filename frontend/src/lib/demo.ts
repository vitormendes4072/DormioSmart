/**
 * Dados de demonstracao (DEMO-01).
 *
 * Existe para uma necessidade concreta: gerar captura de tela do dashboard
 * populado para devlog, apresentacao e o texto do TCC, sem depender de banco,
 * dispositivo pareado ou de esperar uma noite inteira de coleta.
 *
 * ── DUAS SALVAGUARDAS, DE PROPOSITO ─────────────────────────────────────
 *
 * 1. So funciona em build de desenvolvimento (`import.meta.env.DEV`). Em
 *    producao o parametro e ignorado — nao existe URL no ar capaz de exibir
 *    medicao fabricada como se fosse real.
 * 2. Quando ativo, a interface mostra uma faixa fixa e nao dispensavel
 *    dizendo que os dados sao simulados. Assim QUALQUER captura de tela sai
 *    com o aviso dentro dela.
 *
 * A segunda importa mais que a primeira. Uma imagem de dado inventado
 * circulando sem rotulo, num trabalho cujo escopo e justamente nao afirmar
 * mais do que se mede, seria um problema serio na defesa.
 *
 * Uso:  http://localhost:5173/dashboard?demo=1
 */
import { GRAVIDADE, type LeituraSono } from "../types/sleep";
import { geradorPseudoAleatorio } from "./pseudoAleatorio";

export const PARAMETRO_DEMO = "demo";

/**
 * Quantas leituras a demo gera, por padrao.
 *
 * E o mesmo `limit=20` de `get_latest_data` no backend. Gerar mais do que a
 * API devolve produziria uma captura de tela que o app real nunca consegue
 * exibir — alem de espremer as barras a menos de 1px, ponto em que o grafico
 * simplesmente nao desenha.
 */
export const LEITURAS_POR_PADRAO = 20;

export type OpcoesDaNoite = {
  /** Instante da ultima leitura. Padrao: agora. */
  fim?: Date;
  /** Duracao da captacao em minutos. Padrao: 460 (7h40). */
  duracaoEmMinutos?: number;
  /** Quantas leituras gerar. O intervalo e derivado da duracao. */
  quantidade?: number;
  semente?: number;
};

/**
 * Gera uma noite plausivel: repouso predominante, com alguns blocos de
 * movimento agrupados — virar na cama produz varias leituras seguidas, nao
 * um pico isolado. Os valores respeitam o contrato de dados v1.2.0.
 */
export function gerarNoiteDemo(opcoes: OpcoesDaNoite = {}): LeituraSono[] {
  const {
    fim = new Date(),
    duracaoEmMinutos = 460,
    quantidade = LEITURAS_POR_PADRAO,
    semente = 20260819,
  } = opcoes;

  const aleatorio = geradorPseudoAleatorio(semente);
  const total = Math.max(1, quantidade);
  const intervaloEmMinutos = duracaoEmMinutos / total;
  const inicio = fim.getTime() - duracaoEmMinutos * 60_000;

  // Blocos de movimento como fracao da noite, para a distribuicao nao mudar
  // se a duracao mudar. Mais agitacao no comeco e perto do fim, que e o
  // padrao tipico de actigrafia.
  const blocos: [number, number][] = [
    [0.0, 0.06],
    [0.28, 0.34],
    [0.62, 0.66],
    [0.9, 1.0],
  ];

  const leituras: LeituraSono[] = [];
  let tempDoChip = 31.4;

  for (let i = 0; i < total; i++) {
    const fracao = i / total;
    const emMovimento = blocos.some(([a, b]) => fracao >= a && fracao <= b);

    // O chip aquece devagar e estabiliza — nao e temperatura ambiente.
    tempDoChip = Math.min(33.2, tempDoChip + (aleatorio() - 0.35) * 0.08);

    const desvio = emMovimento
      ? 1.3 + aleatorio() * 2.6 // acima do limiar de 1,2 m/s²
      : aleatorio() * 0.45; // ruido de repouso

    const sinal = aleatorio() < 0.5 ? -1 : 1;

    leituras.push({
      created_at: new Date(inicio + i * intervaloEmMinutos * 60_000).toISOString(),
      movimento_total: Number((GRAVIDADE + sinal * desvio).toFixed(2)),
      temp: Number(tempDoChip.toFixed(1)),
      status: emMovimento ? "Movimento" : "Repouso",
    });
  }

  // A API devolve do mais recente para o mais antigo (contrato, secao 6).
  return leituras.reverse();
}

/**
 * Modo demo ativo?
 *
 * Exige build de desenvolvimento E o parametro na URL. Em producao devolve
 * false mesmo com `?demo=1`, entao nao ha como publicar dado fabricado.
 */
export function estaEmModoDemo(
  busca: string = typeof window === "undefined" ? "" : window.location.search,
  ehDesenvolvimento: boolean = import.meta.env.DEV,
): boolean {
  if (!ehDesenvolvimento) return false;
  const valor = new URLSearchParams(busca).get(PARAMETRO_DEMO);
  return valor !== null && valor !== "0" && valor !== "false";
}
