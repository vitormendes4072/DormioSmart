/**
 * O dia e o aparelho do Início no endereço (UI-54): `/dashboard?dia=2026-11-26&aparelho=<id>`.
 *
 * É como o Histórico abre uma sessão no Início: o dia é o do começo da sessão (a mesma
 * regra do calendário, `calendarioDoSono.ts`), e o aparelho evita misturar o celular e o
 * travesseiro no mesmo dia. Endereço malformado é ignorado, sem erro: o Início abre como
 * sempre abriu.
 */
import { PARAMETRO_DEMO } from "./demo";

const DIA = /^(\d{4})-(\d{2})-(\d{2})$/;
const APARELHO = /^[A-Za-z0-9_-]{1,64}$/;

function doisDigitos(n: number) {
  return String(n).padStart(2, "0");
}

export function destinoDoDia(inicio: number, aparelho: string | null | undefined, busca: string) {
  const data = new Date(inicio);
  const parametros = new URLSearchParams();
  parametros.set("dia", `${data.getFullYear()}-${doisDigitos(data.getMonth() + 1)}-${doisDigitos(data.getDate())}`);
  if (aparelho && APARELHO.test(aparelho)) parametros.set("aparelho", aparelho);
  if (new URLSearchParams(busca).get(PARAMETRO_DEMO) === "1") parametros.set(PARAMETRO_DEMO, "1");
  return `/dashboard?${parametros.toString()}`;
}

export function lerDiaDoEndereco(busca: string): { dia: Date | null; aparelho: string | null } {
  const parametros = new URLSearchParams(busca);
  const texto = parametros.get("dia") ?? "";
  const partes = DIA.exec(texto);
  let dia: Date | null = null;
  if (partes) {
    const [ano, mes, data] = partes.slice(1).map(Number);
    // Ao meio-dia, como cada dia do calendário (`somarDias`): é por igualdade que ele marca o escolhido.
    const candidato = new Date(ano, mes - 1, data, 12);
    // 2026-02-31 vira 3 de março no Date: só vale se nada transbordou.
    if (candidato.getFullYear() === ano && candidato.getMonth() === mes - 1 && candidato.getDate() === data) dia = candidato;
  }
  const aparelho = parametros.get("aparelho");
  return { dia, aparelho: dia && aparelho && APARELHO.test(aparelho) ? aparelho : null };
}

/** O endereço sem o dia e o aparelho, para quando a pessoa escolhe outro no próprio Início. */
export function semDiaNoEndereco(busca: string) {
  const parametros = new URLSearchParams(busca);
  if (!parametros.has("dia") && !parametros.has("aparelho")) return null;
  parametros.delete("dia");
  parametros.delete("aparelho");
  const resto = parametros.toString();
  return resto ? `?${resto}` : "";
}
