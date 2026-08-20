/**
 * DADOS FICTÍCIOS — TEMPORÁRIOS.
 *
 * Vieram do protótipo do Figma e existem só para as telas renderizarem
 * enquanto a API não está ligada. São substituídos por dados reais no UI-03
 * (camada de API) e no UI-04/05 (dashboard de movimento).
 *
 * ⚠️ Estes números descrevem estágios de sono e "pontuação", que o dispositivo
 * NÃO mede — ver Escopo no ROADMAP.md. A troca por métricas de movimento é o
 * UI-04/UI-06. Nada aqui pode chegar à defesa como se fosse medição.
 */

export const DADOS_SEMANAIS = [
  { day: "Seg", hours: 6.5 },
  { day: "Ter", hours: 7.8 },
  { day: "Qua", hours: 5.9 },
  { day: "Qui", hours: 8.2 },
  { day: "Sex", hours: 7.1 },
  { day: "Sáb", hours: 9.0 },
  { day: "Dom", hours: 7.4 },
];

export const ESTAGIOS = [
  { name: "Profundo", pct: 22, color: "#8b7ff8" },
  { name: "REM", pct: 21, color: "#a78bfa" },
  { name: "Leve", pct: 47, color: "#243260" },
  { name: "Acordado", pct: 10, color: "#1a2448" },
];

export const HISTORICO = [
  { date: "Hoje, 19 Ago", bed: "23:15", wake: "07:30", dur: "8h 15m", score: 91 },
  { date: "18 Ago", bed: "00:02", wake: "07:45", dur: "7h 43m", score: 78 },
  { date: "17 Ago", bed: "23:45", wake: "07:00", dur: "7h 15m", score: 82 },
  { date: "16 Ago", bed: "22:30", wake: "06:45", dur: "8h 15m", score: 94 },
];

export function corDaPontuacao(s: number) {
  if (s >= 85) return "#8b7ff8";
  if (s >= 70) return "#60a5fa";
  return "#fb923c";
}
