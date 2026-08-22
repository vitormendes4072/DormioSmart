/**
 * Marca do produto (BRAND-03).
 *
 * Substitui o par "icone generico + texto" que existia antes. O icone de lua
 * vinha da biblioteca lucide e nao dizia nada sobre o projeto — era o
 * espaco reservado que ficou desde o prototipo do Figma.
 *
 * Dimensionada pela ALTURA: a proporcao e 5,89:1, entao a largura sai sozinha.
 * A 30px de altura o "SMART" fica com 8px de letra e traco tipico de 2px, que
 * foi o criterio verificado antes de adotar o arquivo.
 */
export function MarcaDoProduto({ className = "h-8" }: { className?: string }) {
  return (
    <img
      src="/smart-dormio.svg"
      alt="Smart Dormio"
      className={`w-auto ${className}`}
    />
  );
}
