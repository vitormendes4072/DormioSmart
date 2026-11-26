/** Identifica a data escolhida também quando ela está dentro de uma sequência. */
export function MarcaDoDiaSelecionado() {
  return <span aria-hidden="true" data-marca-dia className="pointer-events-none absolute right-0.5 top-0.5 size-1.5 rotate-45 rounded-[1px] bg-primary ring-1 ring-card outline outline-1 outline-primary" />;
}
