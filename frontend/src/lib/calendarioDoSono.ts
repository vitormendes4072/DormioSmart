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

const meiaNoite = (data: Date) => new Date(data.getFullYear(), data.getMonth(), data.getDate());

export function registrosDoCalendario(leituras: LeituraSono[], inicio: Date, fim: Date) {
  const registros = new Map<number, number>();
  for (const sessao of sessoesDaMarca(leituras, false)) {
    const dia = somarDias(new Date(sessao.inicio), 0).getTime();
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
