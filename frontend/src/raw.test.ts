/**
 * Todo arquivo importado com `?raw`/`?url`/`?inline` é servido pelo servidor de desenvolvimento? (UI-21, UI-22)
 *
 * ── POR QUE EXISTE ──────────────────────────────────────────────────────
 *
 * A página /privacidade importa `docs/POLITICA-DE-PRIVACIDADE.md?raw`, que
 * fica fora de `frontend/`. O `vite.config.ts` libera esse arquivo, e só ele
 * (`server.fs.allow`). Desde o vite 6.4 o carregador dos testes confere o
 * caminho com a query, e uma liberação de arquivo nunca casa com `…md?raw`;
 * por isso o `vitest.config.ts` libera a pasta `docs/` inteira (SEC-17).
 *
 * As duas listas divergem de propósito, e a divergência tem um modo de falha
 * silencioso: um segundo documento importado assim passaria nos testes (pasta
 * liberada) e no build (que não aplica a lista), e só quebraria no
 * `npm run dev`, com um 403. Este teste fecha isso.
 *
 * ── COMO ────────────────────────────────────────────────────────────────
 *
 * 1. Acha, nos módulos da aplicação, todo texto entre aspas ou crases que
 *    termine em `?raw`, `?url` ou `?inline` — as queries que o vite confere
 *    contra a lista. Pega `import x from`, `import()` dinâmico e template
 *    string. `import.meta.glob` não deixa o caminho escrito: reprova o uso,
 *    para que quem o introduzir decida como conferir.
 * 2. Sobe o servidor de desenvolvimento DE VERDADE, com o `vite.config.ts`,
 *    numa porta livre, e pede cada arquivo como o navegador pede
 *    (`/@fs/…?import&raw`). Exige `200`. Quem decide é o vite, não uma cópia
 *    da regra escrita aqui (UI-22: a versão do UI-21 reimplementava a regra).
 *
 * ── O QUE NÃO PROVA ─────────────────────────────────────────────────────
 *
 * A concatenação simples (`import(base + "?raw")`) reprova por teste próprio;
 * um caminho montado de forma mais elaborada (a query guardada numa variável,
 * por exemplo) não é achado — isso já é contornar de propósito, não descuido.
 * Arquivos de teste ficam de fora: rodam só no vitest. E prova que
 * o servidor SERVE o arquivo, não que a página o renderiza — isso é do
 * `Privacidade.test.tsx` e do `montagem.test.ts`.
 */
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import type { AddressInfo } from "node:net";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { createServer, type ViteDevServer } from "vite";
import { afterAll, beforeAll, describe, expect, it } from "vitest";

const SRC = resolve(dirname(fileURLToPath(import.meta.url)));
const FRONTEND = resolve(SRC, "..");
const IMPORT_COM_QUERY = /["'`]([^"'`\n]+)\?(raw|url|inline)["'`]/g;

function modulosDaAplicacao(dir: string, achados: string[] = []): string[] {
  for (const nome of readdirSync(dir)) {
    const caminho = join(dir, nome);
    if (statSync(caminho).isDirectory()) {
      modulosDaAplicacao(caminho, achados);
    } else if (/\.tsx?$/.test(nome) && !/\.test\.tsx?$/.test(nome)) {
      achados.push(caminho);
    }
  }
  return achados;
}

const MODULOS = modulosDaAplicacao(SRC);

const ACHADOS = MODULOS.flatMap((modulo) =>
  [...readFileSync(modulo, "utf-8").matchAll(IMPORT_COM_QUERY)].map((m) => ({
    modulo: relative(SRC, modulo),
    arquivo: resolve(dirname(modulo), m[1]),
    query: m[2],
  })),
);

describe("?raw/?url/?inline x servidor de desenvolvimento (UI-21, UI-22)", () => {
  let servidor: ViteDevServer;
  let base: string;

  beforeAll(async () => {
    servidor = await createServer({
      configFile: join(FRONTEND, "vite.config.ts"),
      root: FRONTEND,
      logLevel: "silent",
      server: { port: 0, strictPort: false, hmr: false },
      optimizeDeps: { noDiscovery: true, include: [] },
    });
    await servidor.listen();
    base = `http://localhost:${(servidor.httpServer!.address() as AddressInfo).port}`;
  }, 30_000);

  afterAll(async () => {
    await servidor?.close();
  });

  it("acha os imports com query (catraca: a busca não pode ficar cega)", () => {
    console.info(
      "imports com query nos módulos da aplicação:\n" +
        ACHADOS.map((a) => `  ${a.modulo} -> ${relative(FRONTEND, a.arquivo)}?${a.query}`).join("\n"),
    );
    expect(ACHADOS.length).toBeGreaterThan(0);
  });

  // `import(base + "?raw")`: a busca acima não vê caminho nenhum, o build passa
  // sem aviso (com `@vite-ignore`), o documento NÃO entra no pacote e o
  // navegador pede o caminho em tempo de execução — quebra no site publicado,
  // e os testes de página não pegam, porque o vitest resolve (medido em 03/11).
  // Texto que COMEÇA com a query só faz sentido colado a outro: é a assinatura.
  it("nenhum módulo monta o caminho colando a query (import(x + \"?raw\"))", () => {
    const colados = MODULOS.filter((m) => /["'`]\?(raw|url|inline)["'`]/.test(readFileSync(m, "utf-8")));
    expect(colados.map((m) => relative(SRC, m))).toEqual([]);
  });

  it("nenhum módulo usa import.meta.glob, que esconde o caminho da busca", () => {
    const comGlob = MODULOS.filter((m) => readFileSync(m, "utf-8").includes("import.meta.glob"));
    expect(comGlob.map((m) => relative(SRC, m))).toEqual([]);
  });

  // `200` sozinho não basta: para um caminho que não existe, o vite responde
  // `200` com o `index.html` da aplicação (medido em 03/11). Por isso o corpo
  // tem de ser o arquivo — e o arquivo tem de existir.
  it("o servidor de desenvolvimento serve cada arquivo achado, com o conteúdo dele", async () => {
    const falhas = await Promise.all(
      ACHADOS.map(async (a) => {
        const nome = `${a.modulo} -> ${relative(FRONTEND, a.arquivo)}?${a.query}`;
        if (!existsSync(a.arquivo)) return `${nome}: arquivo não existe`;
        const caminho = a.arquivo.replace(/\\/g, "/").replace(/^\/?/, "/");
        const resposta = await fetch(`${base}/@fs${caminho}?import&${a.query}`);
        if (resposta.status !== 200) return `${nome}: ${resposta.status}`;
        const corpo = await resposta.text();
        return corpo === readFileSync(a.arquivo, "utf-8") ? null : `${nome}: 200, mas o corpo não é o arquivo`;
      }),
    );
    expect(falhas.filter(Boolean)).toEqual([]);
  }, 30_000);
});
