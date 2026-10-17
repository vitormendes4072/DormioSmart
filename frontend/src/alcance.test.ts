/**
 * Todo módulo de `src/` é alcançável a partir do ponto de entrada? (UI-17)
 *
 * ── O DEFEITO QUE ISTO PEGA, E QUE JÁ ACONTECEU ─────────────────────────
 *
 * `components/ExcluirConta.tsx` foi commitado em 29/09 com 23 testes, e
 * **nenhum arquivo versionado o importava.** A tela de exclusão de conta — o
 * mecanismo do art. 18, VI da LGPD — ficou inalcançável por qualquer rota do
 * aplicativo por dezoito dias, enquanto o backlog, a
 * `docs/POLITICA-DE-PRIVACIDADE.md` e o `docs/LGPD-ELIMINACAO.md` afirmavam
 * que a interface existia. As três linhas que a montavam estavam presas numa
 * árvore de trabalho não commitada.
 *
 * Nada no repositório podia pegar isso. Os 23 testes exercitam
 * `interpretarRecibo` e a frase de confirmação: são testes de `lib/`, e
 * passavam — continuam passando — com o componente desmontado. `tsc` não
 * reclama de módulo não importado, e o `vite build` tampouco: ele poda o que
 * não entra no grafo e segue verde.
 *
 * ── O QUE ESTA VERIFICAÇÃO PROVA, E O QUE NÃO PROVA ─────────────────────
 *
 * Prova: existe um caminho de `import` de `main.tsx` até cada arquivo. É
 * suficiente para o defeito acima, que é o arquivo fora do grafo.
 *
 * **Não** prova que o componente é renderizado, nem que há rota que leve a
 * ele, nem que o botão aparece. Um componente importado e nunca usado no JSX
 * passa aqui. Fechar essa diferença exige teste de componente, que este
 * projeto não tem — o `vitest` roda em ambiente `node` e não há
 * testing-library. Está declarado no `UI-17`, e é de propósito que esta
 * limitação esteja escrita aqui e não só lá: alcance de verificação que não
 * está escrito ao lado da verificação é como o §1 das lições acontece.
 *
 * É **catraca**, não cobertura: nasce com a árvore limpa e pega o próximo
 * órfão.
 */
import { readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const SRC = resolve(dirname(fileURLToPath(import.meta.url)));
const ENTRADA = join(SRC, "main.tsx");

/**
 * Isenções, impressas a cada execução.
 *
 * Isenção silenciosa é como uma verificação deixa de verificar sem ninguém
 * notar (§1 das lições). Hoje a lista tem só o que não é módulo de aplicação.
 */
const ISENTOS = [
  "vite-env.d.ts", // declaração de tipos do Vite, não é módulo importável
];

function arquivosDeFonte(dir: string, achados: string[] = []): string[] {
  for (const nome of readdirSync(dir)) {
    const caminho = join(dir, nome);
    if (statSync(caminho).isDirectory()) {
      arquivosDeFonte(caminho, achados);
      continue;
    }
    if (!/\.tsx?$/.test(nome)) continue;
    if (/\.test\.tsx?$/.test(nome)) continue;
    achados.push(caminho);
  }
  return achados;
}

/** Resolve um especificador relativo para um arquivo em disco, ou null. */
function resolverRelativo(deArquivo: string, especificador: string): string | null {
  const base = resolve(dirname(deArquivo), especificador);
  const tentativas = [
    base,
    `${base}.ts`,
    `${base}.tsx`,
    join(base, "index.ts"),
    join(base, "index.tsx"),
  ];
  for (const t of tentativas) {
    try {
      if (statSync(t).isFile()) return t;
    } catch {
      // não existe; tenta a próxima forma
    }
  }
  return null;
}

/**
 * Especificadores relativos de um arquivo.
 *
 * Casa `import ... from "./x"`, `import "./x"` e `export ... from "./x"`. Não
 * casa `import()` dinâmico — não há nenhum no projeto hoje, e se passar a
 * haver, o efeito é um falso positivo (acusa órfão que não é), que é o lado
 * seguro de errar: alguém vai olhar.
 */
function importesRelativos(fonte: string): string[] {
  const achados: string[] = [];
  const padrao = /(?:from|import)\s*["'](\.[^"']*)["']/g;
  let m: RegExpExecArray | null;
  while ((m = padrao.exec(fonte)) !== null) achados.push(m[1]);
  return achados;
}

function alcancaveis(): Set<string> {
  const vistos = new Set<string>();
  const fila = [ENTRADA];
  while (fila.length > 0) {
    const atual = fila.pop()!;
    if (vistos.has(atual)) continue;
    vistos.add(atual);
    const fonte = readFileSync(atual, "utf8");
    for (const esp of importesRelativos(fonte)) {
      const destino = resolverRelativo(atual, esp);
      if (destino && !vistos.has(destino)) fila.push(destino);
    }
  }
  return vistos;
}

describe("alcançabilidade dos módulos de src/ (UI-17)", () => {
  it("imprime as isenções, para que nenhuma seja silenciosa", () => {
    // Não é decoração: a isenção que ninguém vê é a que faz a verificação
    // parar de verificar.
    console.log(`[alcance] isenções declaradas (${ISENTOS.length}): ${ISENTOS.join(", ")}`);
    expect(ISENTOS).toEqual(["vite-env.d.ts"]);
  });

  it("o ponto de entrada existe", () => {
    // Guarda do próprio instrumento: se `main.tsx` for renomeado, esta suíte
    // passaria a percorrer um grafo vazio e aprovaria tudo.
    expect(() => readFileSync(ENTRADA, "utf8")).not.toThrow();
  });

  it("o grafo não é trivialmente pequeno", () => {
    // Segunda guarda do instrumento, pelo mesmo motivo: um bug no resolvedor
    // devolveria um grafo de um nó e nenhum órfão.
    expect(alcancaveis().size).toBeGreaterThan(20);
  });

  it("nenhum módulo fica fora do grafo de imports", () => {
    const vistos = alcancaveis();
    const orfaos = arquivosDeFonte(SRC)
      .filter((f) => !vistos.has(f))
      .map((f) => relative(SRC, f).replace(/\\/g, "/"))
      .filter((f) => !ISENTOS.includes(f))
      .sort();

    // A mensagem nomeia os arquivos: "há 1 órfão" manda procurar, a lista
    // manda consertar.
    expect(orfaos, `módulos não alcançáveis a partir de main.tsx:\n  ${orfaos.join("\n  ")}`).toEqual(
      [],
    );
  });
});
