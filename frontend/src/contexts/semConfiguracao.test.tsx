// @vitest-environment jsdom
/**
 * UI-33: sem configuração do Supabase não há sessão a carregar nem link a
 * validar, e isso se sabe na primeira renderização. Antes, `carregando` e
 * `linkValido` só eram corrigidos dentro de um efeito: a tela passava um quadro
 * no estado de carregamento. `renderToString` não roda efeitos, então mostra
 * exatamente esse primeiro quadro.
 */
import { renderToString } from "react-dom/server";
import { MemoryRouter } from "react-router";
import { expect, it, vi } from "vitest";

vi.mock("../lib/supabase", () => ({
  problemaDeConfiguracao: () => "VITE_SUPABASE_URL nao definida.",
  obterSupabase: () => null,
}));

import { NovaSenha } from "../pages/NovaSenha";
import { AuthProvider, useAuth } from "./AuthContext";

function Sonda() {
  const { carregando, erroDeConfiguracao } = useAuth();
  return <span>{`carregando=${String(carregando)}|${erroDeConfiguracao ?? ""}`}</span>;
}

it("sem configuração, o primeiro quadro do AuthProvider já não está carregando", () => {
  const html = renderToString(<AuthProvider><Sonda /></AuthProvider>);
  expect(html).toContain("carregando=false");
  expect(html).toContain("VITE_SUPABASE_URL nao definida.");
});

it("sem configuração, o primeiro quadro da nova senha já diz que o link é inválido", () => {
  const html = renderToString(<MemoryRouter><NovaSenha /></MemoryRouter>);
  expect(html).toContain("Link inválido");
});
