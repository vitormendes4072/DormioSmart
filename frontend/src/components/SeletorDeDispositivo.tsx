import { Layers } from "lucide-react";

import {
  TODOS_OS_DISPOSITIVOS,
  type Dispositivo,
  precisaEscolherDispositivo,
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
        {dispositivos.map((d) => (
          <option key={d.id} value={d.id}>
            {d.nome}
            {d.revoked_at ? " (revogado)" : ""}
          </option>
        ))}
      </select>
    </label>
  );
}

/**
 * Aviso de que a serie empilha instrumentos diferentes.
 *
 * Travesseiro e celular medem o mesmo fenomeno por acoplamentos mecanicos
 * diferentes. Somar os dois numa linha sem dizer seria o mesmo defeito de
 * honestidade que o tracado sintetico da landing evita com a legenda fixa.
 */
export function AvisoDeMistura() {
  return (
    <p className="text-xs text-muted-foreground">
      A série reúne <strong className="font-semibold">todos os dispositivos</strong>. Instrumentos
      em posições diferentes medem o mesmo movimento de formas diferentes — escolha um dispositivo
      acima para comparar séries separadas.
    </p>
  );
}
