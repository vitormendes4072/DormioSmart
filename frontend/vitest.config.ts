import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    // Node basta: os testes cobrem funções puras e o cliente de API com fetch
    // mockado. Testes de componente (jsdom) entram quando houver componente
    // com lógica própria para testar.
    environment: 'node',
    include: ['src/**/*.test.ts'],
  },
})
