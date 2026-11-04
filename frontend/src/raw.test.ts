/**
 * Todo arquivo importado com `?raw` está liberado no servidor de desenvolvimento? (UI-21)
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
 * silencioso: um segundo documento importado com `?raw` passaria nos testes
 * (pasta liberada) e no build (que não aplica a lista), e só quebraria no
 * `npm run dev`, com um 403. Este teste fecha isso: cada `?raw` de um módulo
 * da aplicação tem de estar coberto pela lista do `vite.config.ts`.
 *
 * ── O QUE PROVA, E O QUE NÃO ────────────────────────────────────────────
 *
 * Prova: o caminho de cada `?raw` está, ou está dentro de, uma entrada do
 * `server.fs.allow` do servidor de desenvolvimento — a mesma regra do vite
 * (arquivo igual, ou pasta que o contém). **Não** prova que o servidor serve
 * a página: isso foi conferido à mão em 03/11, no navegador. Arquivos de teste
 * ficam de fora, porque rodam só no vitest.
 */
import { readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import configuracao from "../vite.config";

const SRC = resolve(dirname(fileURLToPath(import.meta.url)));
const IMPORT_RAW = /from\s+["']([^"']+)\?raw["']/g;

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

function importsRaw(): { modulo: string; arquivo: string }[] {
  return modulosDaAplicacao(SRC).flatMap((modulo) =>
    [...readFileSync(modulo, "utf-8").matchAll(IMPORT_RAW)].map((m) => ({
      modulo: relative(SRC, modulo),
      arquivo: resolve(dirname(modulo), m[1]),
    })),
  );
}

// A regra do vite (`isUriInFilePath`): o mesmo arquivo, ou uma pasta que o contém.
function liberado(arquivo: string, lista: string[]): boolean {
  return lista.some((entrada) => arquivo === entrada || arquivo.startsWith(entrada + sep));
}

describe("?raw x server.fs.allow do servidor de desenvolvimento (UI-21)", () => {
  const lista = (configuracao.server?.fs?.allow ?? []).map((e) => resolve(e));
  const achados = importsRaw();

  it("acha os imports ?raw (catraca: a busca não pode ficar cega)", () => {
    console.info(
      "?raw nos módulos da aplicação:\n" +
        achados.map((a) => `  ${a.modulo} -> ${relative(resolve(SRC, ".."), a.arquivo)}`).join("\n"),
    );
    expect(achados.length).toBeGreaterThan(0);
  });

  it("todo arquivo importado com ?raw está liberado no vite.config.ts", () => {
    const fora = achados
      .filter((a) => !liberado(a.arquivo, lista))
      .map((a) => `${a.modulo} importa ${a.arquivo}, fora do server.fs.allow`);
    expect(fora).toEqual([]);
  });
});
