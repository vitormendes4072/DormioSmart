/** Alterna o recorte do Início quando há mais de uma sessão. */
export function SeletorDeSessao({
  total,
  verTudo,
  aoAlternar,
}: {
  total: number;
  verTudo: boolean;
  aoAlternar: () => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-x-3 text-sm">
      <span className="text-muted-foreground">{verTudo ? `${total} sessões` : "Última sessão"}</span>
      <button
        type="button"
        onClick={aoAlternar}
        className="min-h-9 rounded-sm font-semibold text-primary hover:underline focus-visible:outline-2 focus-visible:outline-ring"
      >
        {verTudo ? "Ver só a última" : `Ver as ${total} sessões`}
      </button>
    </div>
  );
}
