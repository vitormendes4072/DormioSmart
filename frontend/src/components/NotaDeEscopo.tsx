import { Info } from "lucide-react";

/**
 * Nota de escopo — permanente e visivel.
 *
 * O dispositivo registra indicios de movimento ancorados em actigrafia. Ele
 * NAO faz estadiamento de sono nem diagnostico. Deixar isso na tela nao e
 * excesso de zelo: e o que separa o que o projeto afirma do que ele nao
 * afirma, e a diferenca precisa estar visivel para quem olha o dashboard —
 * inclusive numa banca.
 */
export function NotaDeEscopo() {
  return (
    <p className="flex items-start gap-2 text-xs text-muted-foreground bg-secondary/40 border border-border rounded-xl px-3.5 py-2.5">
      <Info className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
      <span>
        Registra <strong className="font-medium text-foreground">indícios de movimento</strong>{" "}
        durante o repouso, por acelerometria. Não realiza estadiamento de sono (REM, profundo)
        nem diagnóstico clínico.
      </span>
    </p>
  );
}
