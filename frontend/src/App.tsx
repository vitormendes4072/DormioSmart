import { BrowserRouter, Navigate, Route, Routes } from "react-router";

import { RotaDeVisitante, RotaProtegida } from "./components/Guardas";

import { Layout } from "./components/Layout";
import { Dashboard } from "./pages/Dashboard";
import { Login } from "./pages/Login";
import { NovaSenha } from "./pages/NovaSenha";
import { Register } from "./pages/Register";
import { Settings } from "./pages/Settings";

/**
 * Rotas do app. Substitui o `useState<Screen>` do prototipo: com URL de
 * verdade, recarregar a pagina, voltar no navegador e compartilhar link
 * passam a funcionar.
 *
 * Guardas (AUTH-04): `RotaProtegida` exige sessao; `RotaDeVisitante` tira de
 * login/cadastro quem ja entrou. Ambas esperam a sessao terminar de carregar
 * antes de decidir — sem isso, recarregar a pagina deslogaria o usuario.
 *
 * `/nova-senha` fica fora das duas: chega-se nela pelo link do e-mail, com
 * uma sessao temporaria de recuperacao.
 */
export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<RotaDeVisitante />}>
          <Route path="/login" element={<Login />} />
          <Route path="/cadastro" element={<Register />} />
        </Route>

        <Route path="/nova-senha" element={<NovaSenha />} />

        <Route element={<RotaProtegida />}>
          <Route element={<Layout />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/configuracoes" element={<Settings />} />
          </Route>
        </Route>

        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
