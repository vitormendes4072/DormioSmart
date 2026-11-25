import { ChevronDown, Layers } from "lucide-react";

import {
  TODOS_OS_DISPOSITIVOS,
  type Dispositivo,
  descreverDispositivo,
  precisaEscolherDispositivo,
  tiposPresentes,
} from "../lib/dispositivos";

/**
 * Escolha do instrumento exibido no painel (DASH-05).
 *
 * Some quando ha um dispositivo so — um controle com uma opcao e ruido, e esse
 * e o caso de praticamente todo mundo hoje. A decisao vive em
 * `precisaEscolherDispositivo`, testada a parte.
 *
 * Dispositivo revogado continua na lista: o dado que ele coletou nao deixou de
 * existir, e esconder a origem de uma serie que ainda aparece no grafico seria
 * pior do que mostrar o rotulo.
 */
export function SeletorDeDispositivo({
  dispositivos,
  selecionado,
  aoSelecionar,
}: {
  dispositivos: Dispositivo[];
  selecionado: string | null;
  aoSelecionar: (id: string | null) => void;
}) {
  if (!precisaEscolherDispositivo(dispositivos)) return null;

  return (
    <label className="flex items-center gap-2 text-sm">
      <span className="sr-only">Dispositivo exibido</span>
      <Layers className="w-4 h-4 text-muted-foreground flex-shrink-0" aria-hidden />
      <select
        value={selecionado ?? TODOS_OS_DISPOSITIVOS}
        onChange={(e) => aoSelecionar(e.target.value || null)}
        className="rounded-lg border border-border bg-input-background px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
      >
        <option value={TODOS_OS_DISPOSITIVOS}>Todos os dispositivos</option>
        {/* Nome E tipo (DASH-08): `nome` e texto livre do usuario — "Quarto",
            "Teste 2" — e nao diz de que instrumento a serie veio. */}
        {dispositivos.map((d) => (
          <option key={d.id} value={d.id}>
            {descreverDispositivo(d)}
            {d.revoked_at ? " (revogado)" : ""}
          </option>
        ))}
      </select>
    </label>
  );
}

/** Informa quais instrumentos compõem o gráfico e oferece contexto sob demanda. */
export function AvisoDeMistura({ dispositivos }: { dispositivos: Dispositivo[] }) {
  const tipos = tiposPresentes(dispositivos);
  const origem = tipos.length > 1 && !tipos.includes("Dispositivo")
    ? tipos.join(" e ")
    : "vários dispositivos";

  return (
    <details className="group text-xs text-muted-foreground">
      <summary className="flex min-h-8 w-fit cursor-pointer list-none flex-wrap items-center gap-x-2 rounded-sm focus-visible:outline-2 focus-visible:outline-ring [&::-webkit-details-marker]:hidden">
        <span>Gráfico combina {origem}</span>
        <span className="inline-flex items-center gap-0.5 font-semibold text-primary">
          Entenda
          <ChevronDown aria-hidden="true" className="size-3 group-open:rotate-180" />
        </span>
      </summary>
      <p className="mt-1 max-w-prose">
        Aparelhos em posições diferentes captam o mesmo movimento de formas diferentes.
        Escolha um dispositivo no filtro para ver seus registros separadamente.
      </p>
    </details>
  );
}
