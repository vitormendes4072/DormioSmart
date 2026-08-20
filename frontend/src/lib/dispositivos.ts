/**
 * Dispositivos do usuário (AUTH-05).
 *
 * Um usuário tem muitos dispositivos; cada dispositivo tem um dono. O backend
 * resolve a posse pelo JWT, então nenhuma chamada daqui envia `user_id`.
 */
import { requisitarJson } from "./api";

export type Dispositivo = {
  id: string;
  nome: string;
  created_at: string;
  last_seen_at: string | null;
  revoked_at: string | null;
};

/** Resposta do pareamento. `token` só existe aqui, nesta única resposta. */
export type Pareamento = {
  device: Dispositivo;
  token: string;
};

export const NOME_MAXIMO = 60;

export function listarDispositivos(): Promise<Dispositivo[]> {
  return requisitarJson<Dispositivo[]>("/api/devices");
}

export function parearDispositivo(nome: string): Promise<Pareamento> {
  return requisitarJson<Pareamento>("/api/devices", {
    method: "POST",
    body: JSON.stringify({ nome }),
  });
}

export function renomearDispositivo(id: string, nome: string): Promise<Dispositivo> {
  return requisitarJson<Dispositivo>(`/api/devices/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ nome }),
  });
}

export function revogarDispositivo(id: string): Promise<Dispositivo> {
  return requisitarJson<Dispositivo>(`/api/devices/${id}/revogar`, { method: "POST" });
}

export function estaAtivo(dispositivo: Dispositivo): boolean {
  return dispositivo.revoked_at === null;
}

/**
 * "nunca" quando o dispositivo ainda não enviou nada.
 *
 * Distinguir "nunca enviou" de "enviou faz tempo" é o que responde a pergunta
 * real do usuário: o pareamento funcionou?
 */
export function descreverUltimoContato(dispositivo: Dispositivo): string {
  if (!dispositivo.last_seen_at) return "nunca enviou dados";

  const quando = new Date(dispositivo.last_seen_at);
  if (Number.isNaN(quando.getTime())) return "data desconhecida";

  const minutos = Math.floor((Date.now() - quando.getTime()) / 60_000);
  if (minutos < 1) return "agora mesmo";
  if (minutos < 60) return `há ${minutos} min`;

  const horas = Math.floor(minutos / 60);
  if (horas < 24) return `há ${horas}h`;

  const dias = Math.floor(horas / 24);
  return dias === 1 ? "ontem" : `há ${dias} dias`;
}
