export function SeletorSegmentado<T extends string | number>({
  rotulo, opcoes, selecionado, aoSelecionar,
}: {
  rotulo: string;
  opcoes: readonly { valor: T; rotulo: string }[];
  selecionado: T;
  aoSelecionar: (valor: T) => void;
}) {
  return (
    <div role="group" aria-label={rotulo} className="grid grid-cols-3 gap-1 rounded-xl bg-secondary p-1">
      {opcoes.map(({ valor, rotulo: texto }) => (
        <button
          key={valor}
          type="button"
          aria-pressed={selecionado === valor}
          onClick={() => aoSelecionar(valor)}
          className="min-h-9 rounded-lg px-1 text-xs font-semibold text-muted-foreground hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring aria-pressed:bg-card aria-pressed:text-primary aria-pressed:shadow-sm"
        >
          {texto}
        </button>
      ))}
    </div>
  );
}
