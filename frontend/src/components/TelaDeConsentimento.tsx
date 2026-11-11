import { Loader2, ShieldCheck } from "lucide-react";
import { useId, useState } from "react";
import { Link } from "react-router";

import { TEXTO_DO_CONSENTIMENTO } from "../lib/consentimento";

/**
 * A tela do consentimento específico e destacado (LGPD-12).
 *
 * "Destacado" é literal: uma tela própria, em primeiro plano, que interrompe o
 * início da noite ou da coleta, e não uma linha no cadastro. A caixa de marcar
 * existe para o "Concordo" não ser um clique distraído: sem ela, o botão fica
 * desligado. "Agora não" fecha sem medir nada.
 */
export function TelaDeConsentimento({
  aoConcordar,
  aoRecusar,
  erro,
}: {
  aoConcordar: () => Promise<void>;
  aoRecusar: () => void;
  erro?: string | null;
}) {
  const [marcado, setMarcado] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const titulo = useId();
  const caixa = useId();

  const concordar = async () => {
    setEnviando(true);
    try {
      await aoConcordar();
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titulo}
        className="w-full max-w-md max-h-[90vh] overflow-y-auto rounded-2xl border border-border bg-card p-5 space-y-4"
      >
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-primary" aria-hidden />
          <h2 id={titulo} className="text-base font-semibold text-foreground">
            Antes de começar: seus dados de sono
          </h2>
        </div>
        <ul className="list-disc pl-5 space-y-2 text-sm text-muted-foreground">
          {TEXTO_DO_CONSENTIMENTO.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
        <p className="text-sm text-muted-foreground">
          Os detalhes estão na{" "}
          <Link to="/privacidade" className="text-primary underline">
            política de privacidade
          </Link>
          .
        </p>
        <label htmlFor={caixa} className="flex items-start gap-2 text-sm text-foreground">
          <input
            id={caixa}
            type="checkbox"
            checked={marcado}
            onChange={(e) => setMarcado(e.target.checked)}
            className="mt-1"
          />
          <span>Li e concordo com o tratamento das minhas medições de sono como descrito acima.</span>
        </label>
        {erro && (
          <p className="text-sm text-destructive" role="alert">
            {erro}
          </p>
        )}
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            disabled={!marcado || enviando}
            onClick={() => void concordar()}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {enviando && <Loader2 className="w-4 h-4 animate-spin" aria-hidden />}
            Concordo
          </button>
          <button
            type="button"
            disabled={enviando}
            onClick={aoRecusar}
            className="rounded-lg border border-border px-4 py-2 text-sm font-medium"
          >
            Agora não
          </button>
        </div>
      </div>
    </div>
  );
}
