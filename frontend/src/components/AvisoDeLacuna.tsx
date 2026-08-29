import { AlertTriangle } from "lucide-react";

import { avaliarCobertura, type Cobertura } from "../lib/cobertura";
import { formatarDuracao } from "../lib/metricas";

/**
 * A coleta teve buracos? (DASH-09, refeito no DASH-11)
 *
 * Aparece ANTES dos números, e não depois, porque é o que decide se eles
 * significam alguma coisa. Uma captação com 3% de cobertura produz métricas
 * que parecem tão sólidas quanto as de uma captação completa.
 *
 * A decisão de avisar mora em `avaliarCobertura`, e não aqui, porque é
 * exatamente onde a primeira tentativa errou — e não havia teste sobre ela.
 * Este componente só escolhe as palavras.
 *
 * ── DUAS CAUSAS, DUAS FRASES ────────────────────────────────────────────
 *
 * Faltar medição não é uma coisa só, e dizer a frase errada é pior que não
 * dizer nada:
 *
 * - **O aparelho parou.** Há um silêncio citável — "um trecho de 1h47m".
 * - **O aparelho nunca parou, mas mede menos tempo do que passa.** Resume 30 s
 *   e envia a cada 45 s: 33% da janela sem medição, em buracos de 15 s que
 *   nenhum filtro de tamanho pega e que não fazem sentido citar um a um.
 *
 * O segundo caso é o que a primeira tentativa deixou invisível: ela passou a
 * disparar pelo tamanho dos buracos em vez da perda real, e a tela mostrava
 * uma captação limpa com um terço da janela não medida.
 */
export function AvisoDeLacuna({ cobertura }: { cobertura: Cobertura }) {
  const aviso = avaliarCobertura(cobertura);
  if (aviso === null) return null;

  const { perdidoMs, interrupcoes, maiorInterrupcaoMs, perdaDistribuida } = aviso;

  return (
    <div className="flex gap-3 rounded-xl border border-amber-500/40 bg-amber-500/5 p-4">
      <AlertTriangle className="w-5 h-5 flex-shrink-0 text-amber-500" aria-hidden />
      <div className="text-sm text-muted-foreground space-y-1.5">
        <p className="font-semibold text-foreground">
          Faltou medição em {formatarDuracao(perdidoMs)} desta janela.
        </p>
        <p>
          {interrupcoes.length === 0 ? (
            <>
              O aparelho não parou em nenhum momento — cada leitura resume menos tempo do
              que o intervalo até a próxima, então o que faltou está espalhado por toda a
              janela.
            </>
          ) : (
            <>
              {interrupcoes.length === 1
                ? "O aparelho parou de enviar uma vez"
                : `O aparelho parou de enviar ${interrupcoes.length} vezes`}
              {maiorInterrupcaoMs > 0
                ? `, o silêncio mais longo de ${formatarDuracao(maiorInterrupcaoMs)}`
                : ""}
              {perdaDistribuida
                ? ", e o restante do que faltou está espalhado entre as leituras"
                : ""}
              .
            </>
          )}{" "}
          Os números abaixo valem para o tempo{" "}
          <strong className="font-semibold">que foi medido</strong> — nada se afirma sobre
          o resto.
        </p>
      </div>
    </div>
  );
}

/**
 * A duração das leituras foi estimada? (DASH-11)
 *
 * Vive fora do aviso de lacuna de propósito. Estava embutido nele, e o aviso
 * de lacuna só aparece quando há perda — então numa captação de ESP32 com
 * cobertura perfeita, que é justamente onde tudo é inferido, a tela não dizia
 * nada. Era o único lugar da interface inteira em que `cadenciaInferida`
 * aparecia.
 */
export function NotaDeInferencia({ cobertura }: { cobertura: Cobertura }) {
  if (!cobertura.cadenciaInferida) return null;

  return (
    <p className="text-xs text-muted-foreground">
      A duração das leituras que não a declaram foi estimada pelo intervalo entre elas —
      o dispositivo não informa quanto tempo cada amostra resume.
    </p>
  );
}
