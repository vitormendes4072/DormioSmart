import { Layers } from "lucide-react";

/**
 * Alterna entre a última sessão de captação e o histórico inteiro (DASH-10).
 *
 * Só aparece quando há mais de uma sessão — com uma só, não há o que
 * escolher, e um controle com uma opção é ruído.
 *
 * "Sessão", e não "noite": o escopo do projeto registra movimento durante o
 * repouso, sem afirmar sono. Chamar de noite seria afirmar.
 *
 * ── POR QUE ELE DIZ O QUE FICOU DE FORA (DASH-11) ───────────────────────
 *
 * O DASH-09 pôs o aviso de lacuna antes dos números porque é ele que decide se
 * os números significam algo. O DASH-10 desligou isso do caminho padrão sem
 * perceber: uma sessão é, por construção, um trecho sem buraco — logo o aviso
 * âmbar é estruturalmente impossível no modo padrão. Quem abrisse o painel na
 * noite em que o sensor caiu não veria aviso nenhum; veria uma janela curta e
 * limpa, e nada dizendo que o resto existiu.
 *
 * O recorte é uma escolha da tela, e a tela tem que declará-la. Por isso este
 * controle diz quantas leituras ficaram fora — não é decoração do botão, é a
 * informação que o aviso de lacuna não tem mais como dar aqui.
 */
export function SeletorDeSessao({
  total,
  verTudo,
  leiturasFora,
  aoAlternar,
}: {
  total: number;
  verTudo: boolean;
  /** Leituras recebidas que o recorte atual não está mostrando. */
  leiturasFora: number;
  aoAlternar: () => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
      <span className="inline-flex items-center gap-2 text-muted-foreground">
        <Layers className="w-4 h-4 flex-shrink-0" aria-hidden />
        {verTudo ? (
          `Mostrando as ${total} sessões de captação`
        ) : (
          <span>
            Mostrando a última de {total} sessões de captação
            {leiturasFora > 0 && (
              <>
                {" "}
                — {leiturasFora} {leiturasFora === 1 ? "leitura ficou" : "leituras ficaram"} de
                fora
              </>
            )}
          </span>
        )}
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
