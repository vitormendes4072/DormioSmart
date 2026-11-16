import { Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router";

import { RotaDeVisitante, RotaProtegida } from "./components/Guardas";

import { Layout } from "./components/Layout";
import { noiteNativaDisponivel } from "./lib/noiteNativa";

import { rotaSobDemanda } from "./components/RotaSobDemanda";

const Coletar = rotaSobDemanda("Coletar", () => import("./pages/Coletar").then((m) => ({ default: m.Coletar })));
const Dispositivos = rotaSobDemanda("Dispositivos", () => import("./pages/Dispositivos").then((m) => ({ default: m.Dispositivos })));
const Dashboard = rotaSobDemanda("Dashboard", () => import("./pages/Dashboard").then((m) => ({ default: m.Dashboard })));
const Historico = rotaSobDemanda("Historico", () => import("./pages/Historico").then((m) => ({ default: m.Historico })));
const Landing = rotaSobDemanda("Landing", () => import("./pages/Landing").then((m) => ({ default: m.Landing })));
const Login = rotaSobDemanda("Login", () => import("./pages/Login").then((m) => ({ default: m.Login })));
const NovaSenha = rotaSobDemanda("NovaSenha", () => import("./pages/NovaSenha").then((m) => ({ default: m.NovaSenha })));
const Noite = rotaSobDemanda("Noite", () => import("./pages/Noite").then((m) => ({ default: m.Noite })));
const Register = rotaSobDemanda("Register", () => import("./pages/Register").then((m) => ({ default: m.Register })));
const Settings = rotaSobDemanda("Settings", () => import("./pages/Settings").then((m) => ({ default: m.Settings })));
const Privacidade = rotaSobDemanda("Privacidade", () => import("./pages/Privacidade"));

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
        {/* Pagina publica: quem chega pelo link precisa entender o projeto
            antes de ver um formulario. Fica fora dos guardas — visitante e
            usuario logado veem a mesma pagina, com o botao mudando de destino. */}
        {/* APP-02, etapa 4: no app Android, o comeco e a noite (ou o login, pelo
            guarda). A pagina de apresentacao e para quem chega pelo site. */}
        <Route path="/" element={noiteNativaDisponivel() ? <Navigate to="/noite" replace /> : <Suspense fallback={null}><Landing /></Suspense>} />

        <Route element={<RotaDeVisitante />}>
          <Route path="/login" element={<Suspense fallback={null}><Login /></Suspense>} />
          <Route path="/cadastro" element={<Suspense fallback={null}><Register /></Suspense>} />
        </Route>

        <Route path="/nova-senha" element={<Suspense fallback={null}><NovaSenha /></Suspense>} />

        {/* Pública, fora dos guardas: precisa ser lida ANTES do cadastro
            (LGPD-01 (b), LGPD art. 9º). */}
        <Route
          path="/privacidade"
          element={
            <Suspense fallback={<p className="p-6 text-sm text-muted-foreground">Carregando a política…</p>}>
              <Privacidade />
            </Suspense>
          }
        />

        <Route element={<RotaProtegida />}>
          <Route element={<Layout />}>
            <Route path="/dashboard" element={<Suspense fallback={null}><Dashboard /></Suspense>} />
            <Route path="/coletar" element={<Suspense fallback={null}><Coletar /></Suspense>} />
            <Route path="/historico" element={<Suspense fallback={null}><Historico /></Suspense>} />
            <Route path="/dispositivos" element={<Suspense fallback={null}><Dispositivos /></Suspense>} />
            <Route path="/noite" element={<Suspense fallback={null}><Noite /></Suspense>} />
            <Route path="/configuracoes" element={<Suspense fallback={null}><Settings /></Suspense>} />
          </Route>
        </Route>

        {/* Rota desconhecida cai na pagina publica, nao no login:
            quem digitou errado tem contexto em vez de um formulario. */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
