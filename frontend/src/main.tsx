import { createRoot } from "react-dom/client";

import App from "./App.tsx";
import { AuthProvider } from "./contexts/AuthContext.tsx";
import "./styles/index.css";
import { registrarServiceWorker } from "./lib/instalacao";

createRoot(document.getElementById("root")!).render(
  <AuthProvider>
    <App />
  </AuthProvider>,
);

// PWA instalavel (APP-07). Falha em silencio; ver lib/instalacao.ts.
registrarServiceWorker();
