import { Layers } from "lucide-react";

/**
 * Alterna entre a última sessão de captação e o histórico inteiro (DASH-10).
 *
 * Só aparece quando há mais de uma sessão — com uma só, não há o que
 * escolher, e um controle com uma opção é ruído.
 *
 * "Sessão", e não "noite": o escopo do projeto registra movimento durante o
 * repouso, sem afirmar sono. Chamar de noite seria afirmar.
 */
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
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
      <span className="inline-flex items-center gap-2 text-muted-foreground">
        <Layers className="w-4 h-4 flex-shrink-0" aria-hidden />
        {verTudo
          ? `Mostrando as ${total} sessões de captação`
          : "Mostrando a última sessão de captação"}
      </span>
      <button
        onClick={aoAlternar}
        className="font-semibold text-primary hover:underline"
      >
        {verTudo ? "Ver só a última" : `Ver todas (${total})`}
      </button>
    </div>
  );
}
