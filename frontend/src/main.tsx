import { createRoot } from "react-dom/client";

import App from "./App.tsx";
import { AuthProvider } from "./contexts/AuthContext.tsx";
import { PerfilProvider } from "./contexts/PerfilContext.tsx";
import "./styles/index.css";
import { registrarServiceWorker } from "./lib/instalacao";

// `PerfilProvider` DENTRO do `AuthProvider`, e não ao lado: ele precisa do JWT
// para buscar o perfil, e precisa saber quando o usuario muda (PERFIL-01).
createRoot(document.getElementById("root")!).render(
  <AuthProvider>
    <PerfilProvider>
      <App />
    </PerfilProvider>
  </AuthProvider>,
);

// PWA instalavel (APP-07). Falha em silencio; ver lib/instalacao.ts.
registrarServiceWorker();
