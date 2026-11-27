import type { serieDaSemana } from "./calendarioDoSono";

const MINUTO = 60_000;
const MAXIMO = 960;

export function minutosDaMeta(valor: unknown): number | null {
  return typeof valor === "number" && Number.isInteger(valor) && valor >= 60 && valor <= MAXIMO ? valor : null;
}

export function lerMetaDiaria(texto: string) {
  if (!texto.trim()) return { ok: true as const, valor: null };
  const partes = /^(\d{1,2}):([0-5]\d)$/.exec(texto.trim());
  const total = partes && minutosDaMeta(Number(partes[1]) * 60 + Number(partes[2]));
  return total && total % 15 === 0
    ? { ok: true as const, valor: total }
    : { ok: false as const, motivo: "Informe de 1:00 a 16:00, em passos de 15 minutos." };
}

export function preencherMeta(valor: unknown) {
  const minutos = minutosDaMeta(valor);
  return minutos === null ? "" : `${Math.floor(minutos / 60)}:${String(minutos % 60).padStart(2, "0")}`;
}

export function tempoDaMeta(minutos: number) {
  const inteiro = Math.round(minutos);
  const horas = Math.floor(inteiro / 60);
  const resto = inteiro % 60;
  return horas === 0 ? `${resto} min` : resto === 0 ? `${horas} h` : `${horas} h ${String(resto).padStart(2, "0")}`;
}

export function projetarMeta(
  serie: Pick<ReturnType<typeof serieDaSemana>, "media" | "dias" | "comRegistro">,
  meta: number,
  hoje: Date,
  parcial: boolean,
) {
  if (parcial || serie.media === null) return null;
  const media = serie.media / MINUTO;
  if (media >= meta) return { tipo: "atingida" } as const;
  const inicioDeHoje = new Date(hoje.getFullYear(), hoje.getMonth(), hoje.getDate()).getTime();
  const restantes = serie.dias.filter(({ estado, data }) =>
    (estado === "futuro" || estado === "sem-registro") && data.getTime() >= inicioDeHoje).length;
  if (restantes === 0) return { tipo: "fora-do-alcance" } as const;
  const total = serie.comRegistro.length;
  const porDia = (meta * (total + restantes) - media * total) / restantes;
  return porDia > MAXIMO ? { tipo: "fora-do-alcance" } as const
    : { tipo: "possivel", restantes, porDia } as const;
}
