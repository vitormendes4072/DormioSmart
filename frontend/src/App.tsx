import { BrowserRouter, Navigate, Route, Routes } from "react-router";

import { Layout } from "./components/Layout";
import { Dashboard } from "./pages/Dashboard";
import { Login } from "./pages/Login";
import { Register } from "./pages/Register";
import { Settings } from "./pages/Settings";

/**
 * Rotas do app. Substitui o `useState<Screen>` do prototipo: com URL de
 * verdade, recarregar a pagina, voltar no navegador e compartilhar link
 * passam a funcionar.
 *
 * As rotas de dentro do Layout ainda NAO sao protegidas — qualquer um pode
 * abrir /dashboard direto. Isso e o AUTH-04, que depende da sessao do
 * Supabase Auth (AUTH-01).
 */
export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/cadastro" element={<Register />} />

        <Route element={<Layout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/configuracoes" element={<Settings />} />
        </Route>

        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
