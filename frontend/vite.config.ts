import path from 'path'

import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// O bundle original do Figma trazia um `figmaAssetResolver`, que resolvia
// imports `figma:asset/...` para src/assets. Nenhum arquivo usa esses imports
// e a pasta assets não veio no bundle — removido na importação (UI-01).
// APP-02: o build do app Android (`npm run build:app`, modo `app`) roda em
// `https://localhost` dentro do aparelho, então as chamadas à API precisam do
// endereço completo do backend. O site não usa este modo e segue relativo.
const BACKEND_DO_APP = 'https://dormio-smart.vercel.app'

export default defineConfig(({ mode }) => ({
  define:
    mode === 'app'
      ? {
          'import.meta.env.VITE_API_BASE': JSON.stringify(
            process.env.VITE_API_BASE ?? BACKEND_DO_APP,
          ),
        }
      : {},
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: {
    port: 5173,
    // LGPD-01 (b): a página /privacidade importa o documento versionado, que
    // fica fora de frontend/. Libera esse arquivo, e só ele.
    fs: {
      allow: [
        path.resolve(__dirname),
        path.resolve(__dirname, '../docs/POLITICA-DE-PRIVACIDADE.md'),
      ],
    },
    // Durante o desenvolvimento, /api/* vai para o Flask local.
    // Em produção quem faz esse roteamento é o vercel.json (UI-08).
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
    },
  },
}))
