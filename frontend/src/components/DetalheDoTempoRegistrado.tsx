import { useEffect, useId, useRef } from "react";
import { X } from "lucide-react";

import { calcularCobertura, type Sessao } from "../lib/cobertura";
import { formatarDuracao, formatarPorcentagem } from "../lib/metricas";

/**
 * UI-51: o que está por trás do "Tempo registrado" do Início, num painel que
 * sobe de baixo no celular e fica no centro no computador. É o mesmo detalhe
 * que o celular de exemplo da landing abre (`landing-prototipo.html`,
 * `openDetail('duration')`): início, fim, o período e quanto dele foi
 * registrado, com a mesma frase sobre o que o número é e o que ele não é.
 * Na tela, "janela" é "período" e "cobertura" é "do período foi registrado"
 * (glossário do UI-39, `PADRAO-VISUAL.md` §10).
 *
 * O período é somado sessão a sessão: em "todas as sessões", o tempo entre uma
 * noite e outra não é o registro parando e não entra na conta (como no UI-40).
 */
function detalharTempoRegistrado(sessoes: Sessao[], registradoMs: number) {
  const janelaMs = sessoes.reduce((soma, sessao) => soma + calcularCobertura(sessao.leituras).janelaMs, 0);
  const inicio = sessoes.length > 0 ? sessoes[0].inicio : null;
  const fim = sessoes.length > 0 ? sessoes[sessoes.length - 1].fim : null;
  const cobertura = janelaMs > 0 ? formatarPorcentagem(Math.min(1, registradoMs / janelaMs) * 100) : null;
  return { janelaMs, inicio, fim, cobertura };
}

const HORA = new Intl.DateTimeFormat("pt-BR", { hour: "2-digit", minute: "2-digit" });
const DIA = new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "2-digit" });

export const hora = (ms: number) => HORA.format(ms);
const dia = (ms: number) => DIA.format(ms);
const mesmoDia = (a: number, b: number) => new Date(a).toDateString() === new Date(b).toDateString();

export function DetalheDoTempoRegistrado({ sessoes, verTudo, registradoMs, aoFechar }: {
  sessoes: Sessao[];
  verTudo: boolean;
  registradoMs: number;
  aoFechar: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const idDoTitulo = useId();
  const { janelaMs, inicio, fim, cobertura } = detalharTempoRegistrado(sessoes, registradoMs);

  useEffect(() => {
    const dialogo = ref.current;
    if (!dialogo) return;
    const origem = document.activeElement;
    dialogo.showModal();
    dialogo.querySelector<HTMLElement>("[data-foco-inicial]")?.focus();
    return () => {
      dialogo.close();
      if (origem instanceof HTMLElement && origem.isConnected) origem.focus();
    };
  }, []);

  // Em "todas as sessões" o início e o fim caem em dias diferentes: a data vai junto.
  const comData = verTudo;
  const quando = (ms: number) => (comData ? `${dia(ms)}, ${hora(ms)}` : hora(ms));
  const periodo = inicio == null || fim == null
    ? null
    : verTudo
      ? `${sessoes.length} sessões, de ${dia(inicio)} a ${dia(fim)}.`
      : mesmoDia(inicio, fim) ? `Sessão de ${dia(inicio)}.` : `Sessão de ${dia(inicio)} a ${dia(fim)}.`;

  const dados: Array<[string, string]> = [
    ["Início", inicio == null ? "—" : quando(inicio)],
    ["Fim", fim == null ? "—" : quando(fim)],
    [verTudo ? "Períodos somados" : "Período", janelaMs > 0 ? formatarDuracao(janelaMs) : "—"],
    ["Do período foi registrado", cobertura ?? "—"],
  ];

  return (
    <dialog
      ref={ref}
      aria-labelledby={idDoTitulo}
      data-detalhe-do-tempo
      onCancel={(evento) => { evento.preventDefault(); aoFechar(); }}
      // Clique fora do painel (no fundo escurecido) fecha, como na landing.
      onClick={(evento) => { if (evento.target === evento.currentTarget) aoFechar(); }}
      className="mx-0 mt-auto mb-0 max-h-[85dvh] w-full max-w-none overflow-y-auto rounded-t-3xl border border-border bg-card p-0 text-foreground shadow-xl backdrop:bg-black/60 sm:m-auto sm:max-w-md sm:rounded-2xl"
    >
      {/* No celular, a folga de baixo não fica atrás da barra de gestos. */}
      <div className="space-y-3 px-4 pt-3 pb-[max(1.5rem,env(safe-area-inset-bottom))] sm:p-5">
        <div aria-hidden="true" className="mx-auto h-1 w-10 rounded-full bg-muted-foreground/40 sm:hidden" />
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-[11px] font-extrabold uppercase tracking-wider text-primary">Detalhes</p>
            <h2 id={idDoTitulo} className="mt-1 text-xl font-extrabold tracking-tight">Tempo registrado</h2>
          </div>
          <button
            type="button"
            data-foco-inicial
            onClick={aoFechar}
            aria-label="Fechar detalhes"
            className="grid size-10 shrink-0 place-items-center rounded-xl border border-border bg-secondary text-foreground hover:bg-secondary/70 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
          >
            <X className="size-4" aria-hidden />
          </button>
        </div>

        <p className="text-sm leading-relaxed text-muted-foreground">
          {periodo && <>{periodo} </>}
          O tempo registrado é o que o aparelho mediu entre o início e o fim. Não é a duração do sono.
        </p>

        <dl className="grid grid-cols-2 gap-2">
          {dados.map(([rotulo, valor]) => (
            <div key={rotulo} className="min-w-0 rounded-xl bg-secondary p-3">
              <dt className="text-xs text-muted-foreground">{rotulo}</dt>
              <dd className="mt-0.5 text-xl font-extrabold tracking-tight">{valor}</dd>
            </div>
          ))}
        </dl>

        {verTudo && (
          <p className="text-xs leading-relaxed text-muted-foreground">
            O período de cada sessão vai do primeiro ao último registro; o tempo entre uma sessão e outra não entra.
          </p>
        )}
      </div>
    </dialog>
  );
}
