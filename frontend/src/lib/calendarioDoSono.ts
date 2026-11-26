import { calcularCobertura } from "./cobertura";
import { sessoesDaMarca } from "./trecho";
import type { LeituraSono } from "../types/sleep";

export function somarDias(data: Date, dias: number): Date {
  return new Date(data.getFullYear(), data.getMonth(), data.getDate() + dias, 12);
}

export function segundaDaSemana(data: Date): Date {
  return somarDias(data, -((data.getDay() + 6) % 7));
}

export function janelaDoCalendario(data: Date) {
  const primeiro = new Date(data.getFullYear(), data.getMonth(), 1, 12);
  const ultimo = new Date(data.getFullYear(), data.getMonth() + 1, 0, 12);
  const inicio = segundaDaSemana(primeiro);
  const fim = somarDias(segundaDaSemana(ultimo), 6);
  return { inicio, fim, diasNoMes: ultimo.getDate(), deslocamento: (primeiro.getDay() + 6) % 7 };
}

function diaDaSessao(inicio: number): number {
  return somarDias(new Date(inicio), 0).getTime();
}

export function sessoesDoDia(leituras: LeituraSono[], dia: Date) {
  const alvo = somarDias(dia, 0).getTime();
  return sessoesDaMarca(leituras, false).filter((sessao) => diaDaSessao(sessao.inicio) === alvo);
}

const meiaNoite = (data: Date) => new Date(data.getFullYear(), data.getMonth(), data.getDate());

export function registrosDoCalendario(leituras: LeituraSono[], inicio: Date, fim: Date) {
  const registros = new Map<number, number>();
  for (const sessao of sessoesDaMarca(leituras, false)) {
    const dia = diaDaSessao(sessao.inicio);
    if (dia < inicio.getTime() || dia > fim.getTime()) continue;
    const tempo = calcularCobertura(sessao.leituras).tempoCobertoMs;
    registros.set(dia, (registros.get(dia) ?? 0) + tempo);
  }
  return registros;
}

export function limitesDaConsulta(inicio: Date, fim: Date) {
  // Busca também as bordas para preservar o início e a duração das sessões
  // que atravessam a meia-noite, inclusive nas viradas de mês.
  return {
    desde: meiaNoite(somarDias(inicio, -1)).toISOString(),
    ate: new Date(meiaNoite(somarDias(fim, 2)).getTime() - 1).toISOString(),
  };
}

export function sequenciasDoCalendario(registros: ReadonlyMap<number, number>): Date[][] {
  const sequencias: Date[][] = [];
  for (const dia of [...registros.keys()].sort((a, b) => a - b)) {
    const ultima = sequencias[sequencias.length - 1];
    const anterior = ultima?.[ultima.length - 1];
    if (anterior && somarDias(anterior, 1).getTime() === dia) {
      ultima.push(new Date(dia));
    } else {
      sequencias.push([new Date(dia)]);
    }
  }
  return sequencias.reverse();
}

export const DIAS_DA_SEMANA = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];

type Dia = { data: Date; rotulo: string };
type DiaRegistrado = Dia & { estado: "registrado"; tempoMs: number };
type DiaSemValor = Dia & { estado: "sem-registro" | "incompleto" | "futuro"; tempoMs: null };

export function serieDaSemana(
  registros: ReadonlyMap<number, number>,
  referencia: Date,
  hoje: Date,
  parcial: boolean,
) {
  const segunda = segundaDaSemana(referencia);
  const hojeMs = somarDias(hoje, 0).getTime();
  const dias = DIAS_DA_SEMANA.map((rotulo, indice): DiaRegistrado | DiaSemValor => {
    const data = somarDias(segunda, indice);
    if (data.getTime() > hojeMs) return { data, rotulo, estado: "futuro", tempoMs: null };
    const tempoMs = registros.get(data.getTime());
    return tempoMs === undefined
      ? { data, rotulo, estado: parcial ? "incompleto" : "sem-registro", tempoMs: null }
      : { data, rotulo, estado: "registrado", tempoMs };
  });

  const comRegistro = dias.filter((dia): dia is DiaRegistrado => dia.estado === "registrado");
  if (comRegistro.length === 0) return { dias, comRegistro, media: null, maiores: [], menores: [] };

  const valores = comRegistro.map(({ tempoMs }) => tempoMs);
  const maximo = Math.max(...valores);
  const minimo = Math.min(...valores);
  return {
    dias,
    comRegistro,
    media: valores.reduce((total, valor) => total + valor, 0) / valores.length,
    maiores: comRegistro.filter(({ tempoMs }) => tempoMs === maximo),
    menores: comRegistro.filter(({ tempoMs }) => tempoMs === minimo),
  };
}
