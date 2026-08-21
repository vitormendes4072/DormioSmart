import path from 'path'

import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// O bundle original do Figma trazia um `figmaAssetResolver`, que resolvia
// imports `figma:asset/...` para src/assets. Nenhum arquivo usa esses imports
// e a pasta assets não veio no bundle — removido na importação (UI-01).
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: {
    port: 5173,
    // Durante o desenvolvimento, /api/* vai para o Flask local.
    // Em produção quem faz esse roteamento é o vercel.json (UI-08).
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
    },
  },
})
