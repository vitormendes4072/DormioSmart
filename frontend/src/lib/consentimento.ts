import { requisitarJson } from "./api";
import type { PerfilDoServidor } from "./perfil";

/**
 * O consentimento específico e destacado para dado de saúde (LGPD-12).
 *
 * A política trata a série de movimento e a estimativa de sono como dado de
 * saúde (art. 11, I): antes da primeira noite e da primeira coleta, a pessoa vê
 * esta tela e consente — ou não, e nada é medido. A garantia é do banco
 * (migração 017): sem o consentimento na versão vigente, a gravação e o
 * pareamento recusam.
 *
 * `VERSAO_DO_CONSENTIMENTO` é a mesma de `public.versao_do_consentimento()` e de
 * `web-app/consentimento.py`; `web-app/tests/test_consentimento.py` confere as
 * três. **Mudar o texto da tela é mudar a versão nos três lugares**: quem
 * aceitou o texto anterior vê a tela de novo.
 */
export const VERSAO_DO_CONSENTIMENTO = "2026-11-10";

/** O que a pessoa consente, item por item. É o texto da tela. */
export const TEXTO_DO_CONSENTIMENTO: readonly string[] = [
  "O Dormio mede o movimento do aparelho enquanto você dorme e guarda essas medições na sua conta.",
  "A partir delas, o sistema estima, a cada 30 segundos, se você estava dormindo ou acordado.",
  "Essas medições e essa estimativa são tratadas como dado de saúde, com o cuidado que a lei exige.",
  "A estimativa não é diagnóstico e não deve orientar nenhuma decisão de saúde.",
  "Você pode apagar tudo a qualquer momento, excluindo a conta em Configurações.",
];

export function consentimentoVigente(perfil: PerfilDoServidor | null): boolean {
  return perfil?.consentimento_saude_versao === VERSAO_DO_CONSENTIMENTO;
}

/** Registra o consentimento na versão desta tela. A data é a do banco. */
export async function registrarConsentimento(): Promise<void> {
  await requisitarJson("/api/me/consentimento", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ versao: VERSAO_DO_CONSENTIMENTO }),
  });
}
