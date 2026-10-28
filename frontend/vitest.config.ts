import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    // `node` é o padrão porque é o que 26 dos 27 arquivos precisam: funções
    // puras e o cliente de API com fetch mockado.
    //
    // ✏️ 19/10 (UI-17): o comentário anterior dizia que testes de componente
    // em jsdom "entram quando houver componente com lógica própria para
    // testar". Eles entraram, por outro motivo — não para testar lógica de
    // componente, e sim para provar que os componentes estão MONTADOS. O
    // `src/montagem.test.ts` pede jsdom por diretiva no próprio arquivo
    // (`// @vitest-environment jsdom`), e não aqui, de propósito: trocar o
    // ambiente global faria 26 arquivos passarem a rodar em jsdom sem que
    // nenhum deles precise, pagando o custo e mudando o que eles exercitam.
    environment: 'node',
    // `.tsx` entrou no padrão em 19/10, e **não** porque algum arquivo precise
    // dele hoje: o `montagem.test.ts` não tem JSX próprio, porque quem monta a
    // árvore é o `main.tsx`. Entrou porque o padrão anterior (`*.test.ts`)
    // **não coletaria** um `*.test.tsx` — e um arquivo de teste que não é
    // coletado é indistinguível de um arquivo de teste que passa. Agora que há
    // jsdom no projeto, escrever o primeiro `.test.tsx` é plausível, e o modo
    // de falha dele seria silencioso. É a ocorrência 4 do §1 das lições
    // (alcance de verificação escrito à mão deixa de acompanhar a pasta),
    // corrigida antes de acontecer em vez de depois.
    include: ['src/**/*.test.{ts,tsx}'],
  },
})
