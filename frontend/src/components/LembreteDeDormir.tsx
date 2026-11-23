import { useEffect, useState } from "react";

import { Noite, type EstadoDoLembrete } from "../lib/noiteNativa";

type Plugin = Pick<typeof Noite, "lembrete" | "definirLembrete">;

const doisDigitos = (n: number) => String(n).padStart(2, "0");

/** "22:30" a partir da hora e do minuto. */
export function horarioComoTexto(hora: number, minuto: number): string {
  return `${doisDigitos(hora)}:${doisDigitos(minuto)}`;
}

/** Hora e minuto de "HH:MM", ou null se não for um horário. */
export function lerHorario(texto: string): { hora: number; minuto: number } | null {
  const m = /^(\d{2}):(\d{2})$/.exec(texto);
  if (!m) return null;
  const hora = Number(m[1]);
  const minuto = Number(m[2]);
  return hora <= 23 && minuto <= 59 ? { hora, minuto } : null;
}

/**
 * APP-20: o lembrete de dormir, em Configurações (só no app).
 *
 * Começa desligado. Ligar pede a permissão de notificar, se faltar; sem ela, a
 * tela diz como ativar. O horário e o agendamento ficam no próprio celular.
 */
export function LembreteDeDormir({ plugin = Noite }: { plugin?: Plugin }) {
  const [estado, setEstado] = useState<EstadoDoLembrete | null>(null);
  const [falha, setFalha] = useState(false);
  const [salvando, setSalvando] = useState(false);

  useEffect(() => {
    let vivo = true;
    plugin
      .lembrete()
      .then((e) => vivo && setEstado(e))
      .catch(() => vivo && setFalha(true));
    return () => {
      vivo = false;
    };
  }, [plugin]);

  async function definir(ativo: boolean, hora: number, minuto: number) {
    setSalvando(true);
    setFalha(false);
    try {
      setEstado(await plugin.definirLembrete({ ativo, hora, minuto }));
    } catch {
      setFalha(true);
    } finally {
      setSalvando(false);
    }
  }

  if (!estado) {
    return falha ? <p className="text-sm text-destructive">Não foi possível ler o lembrete.</p> : null;
  }
  const horario = horarioComoTexto(estado.hora, estado.minuto);
  return (
    <div className="space-y-3">
      <label className="flex items-center justify-between gap-3">
        <span className="text-sm text-foreground">Lembrar todo dia</span>
        <input
          type="checkbox"
          checked={estado.ativo}
          disabled={salvando}
          onChange={(e) => void definir(e.target.checked, estado.hora, estado.minuto)}
          className="h-5 w-5 accent-[var(--primary)]"
        />
      </label>
      <label className="flex items-center justify-between gap-3">
        <span className="text-sm text-foreground">Horário</span>
        <input
          type="time"
          value={horario}
          disabled={salvando}
          onChange={(e) => {
            const h = lerHorario(e.target.value);
            if (h) void definir(estado.ativo, h.hora, h.minuto);
          }}
          className="rounded-lg border border-border bg-background px-3 py-1.5 text-sm"
        />
      </label>
      {estado.ativo && !estado.notificacoes ? (
        <p role="alert" className="text-xs text-destructive">
          As notificações do app estão desligadas. Para receber o lembrete, ative-as nas configurações do Android.
        </p>
      ) : null}
      {estado.ativo && estado.notificacoes ? (
        <p className="text-xs text-muted-foreground">Você vai receber o lembrete todo dia às {horario}.</p>
      ) : null}
      {falha ? <p className="text-sm text-destructive">Não foi possível salvar o lembrete. Tente de novo.</p> : null}
    </div>
  );
}
