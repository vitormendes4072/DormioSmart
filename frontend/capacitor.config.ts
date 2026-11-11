import type { CapacitorConfig } from "@capacitor/cli";

/**
 * Casca do app Android (APP-02).
 *
 * O app é o mesmo frontend, empacotado: `npm run build:app` gera o `dist/` no
 * modo `app` (com o endereço do backend, ver `vite.config.ts`) e o `cap sync`
 * copia para `android/`. Só o registro da noite é nativo, porque o navegador
 * não mantém o acelerômetro com a tela bloqueada (`useColeta.ts`).
 *
 * `CapacitorHttp` faz as chamadas `fetch` pelo HTTP nativo do aparelho: a
 * página roda em `https://localhost`, e o backend não tem CORS para essa
 * origem. Com o HTTP nativo, ele não precisa ter.
 */
const config: CapacitorConfig = {
  appId: "app.dormiosmart.coleta",
  appName: "Dormio",
  webDir: "dist",
  plugins: {
    CapacitorHttp: { enabled: true },
  },
};

export default config;
