import { FlaskConical } from "lucide-react";

/**
 * Aviso de modo demonstracao.
 *
 * Fixo no topo e sem botao de fechar, de proposito: o objetivo do modo demo e
 * gerar captura de tela, entao o aviso precisa aparecer DENTRO da imagem.
 * Um banner dispensavel some justamente na hora do print.
 */
export function FaixaDemo() {
  return (
    <div className="sticky top-0 z-50 flex items-center justify-center gap-2 bg-destructive px-4 py-2 text-center text-xs font-semibold text-destructive-foreground">
      <FlaskConical className="w-3.5 h-3.5 flex-shrink-0" />
      <span>
        MODO DEMONSTRAÇÃO — dados simulados, não são medições reais do dispositivo
      </span>
    </div>
  );
}
