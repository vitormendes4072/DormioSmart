/**
 * Gerador pseudoaleatorio deterministico (LCG).
 *
 * Existe num arquivo proprio porque duas partes do app precisam da mesma
 * garantia: a mesma semente produz sempre a mesma sequencia. A demo
 * (`demo.ts`) depende disso para que uma captura de tela possa ser refeita
 * meses depois; o tracado da landing (`sinal.ts`) depende disso para que o
 * desenho nao mude a cada carregamento da pagina.
 *
 * Nao ha requisito criptografico aqui — o LCG classico basta e cabe em tres
 * linhas. Se um dia houver, este e o unico lugar a trocar.
 */
export function geradorPseudoAleatorio(semente: number): () => number {
  let estado = semente >>> 0;
  return () => {
    estado = (estado * 1664525 + 1013904223) >>> 0;
    return estado / 4294967296;
  };
}
