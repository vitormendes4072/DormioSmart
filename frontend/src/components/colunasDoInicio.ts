/**
 * As duas colunas do Início em tela larga (UI-48/UI-49): o topo, a linha dos cartões, a linha do
 * gráfico de movimento e os estados sem sessão usam a mesma grade, para as bordas coincidirem.
 *
 * A coluna da direita (calendário, tempo por dia, "Seu dispositivo") não fica abaixo de 320 px:
 * com 220 px de mínimo ela chegava a 262 px numa tela de 1 100 px, o título do calendário quebrava
 * e os rótulos do gráfico se encostavam (UI-49, ajuste).
 *
 * Os textos ficam inteiros, e não montados, para o Tailwind achar as classes.
 */
export const COLUNAS_DO_INICIO = "grid-cols-[minmax(0,1.8fr)_minmax(320px,0.9fr)]";
