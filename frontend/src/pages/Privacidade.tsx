import { ShieldCheck } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { Link } from "react-router";
import remarkGfm from "remark-gfm";

// O documento versionado, lido no build — ver `lib/politica.ts`.
import documento from "../../../docs/POLITICA-DE-PRIVACIDADE.md?raw";
import { preencher, textoPublicavel } from "../lib/politica";

const TEXTO = preencher(textoPublicavel(documento), {
  controlador: import.meta.env.VITE_POLITICA_CONTROLADOR,
  contato: import.meta.env.VITE_POLITICA_CONTATO,
});

/**
 * Política de privacidade (LGPD-01 (b), 03/11). Pública: precisa ser lida
 * ANTES do cadastro. `react-markdown` não executa HTML do texto; `remark-gfm`
 * dá as tabelas. Carregada sob demanda (`App.tsx`), para não pesar no pacote
 * principal.
 */
export default function Privacidade() {
  return (
    <main className="min-h-screen bg-background">
      <div className="max-w-3xl mx-auto px-4 py-8 space-y-6">
        <Link to="/" className="text-sm text-primary hover:text-accent transition font-semibold">
          ← Smart Dormio
        </Link>

        <div role="note" className="flex gap-3 rounded-xl border border-border bg-secondary/40 p-4 text-sm">
          <ShieldCheck className="w-5 h-5 text-primary shrink-0 mt-0.5" />
          <p className="text-muted-foreground">
            <strong className="text-foreground">Versão preliminar.</strong> Esta é a política de
            um protótipo acadêmico, ainda em revisão. Ela descreve o que o sistema faz hoje — e
            diz, onde for o caso, o que ele ainda não faz.
          </p>
        </div>

        <article className="politica text-sm leading-relaxed text-foreground space-y-4 [&_h1]:text-2xl [&_h1]:font-bold [&_h2]:text-lg [&_h2]:font-semibold [&_h2]:mt-8 [&_h3]:font-semibold [&_h3]:mt-4 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5 [&_blockquote]:border-l-2 [&_blockquote]:border-border [&_blockquote]:pl-3 [&_blockquote]:text-muted-foreground [&_table]:w-full [&_table]:text-xs [&_th]:text-left [&_th]:p-2 [&_td]:p-2 [&_td]:align-top [&_tr]:border-b [&_tr]:border-border [&_a]:text-primary">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{TEXTO}</ReactMarkdown>
        </article>
      </div>
    </main>
  );
}
