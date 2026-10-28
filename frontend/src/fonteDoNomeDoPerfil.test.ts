/**
 * O nome do perfil tem um leitor só? (PERFIL-01, Regra 1)
 *
 * ── O DEFEITO QUE ISTO IMPEDE ────────────────────────────────────────────
 *
 * `public.profiles` virou a fonte de verdade do nome e da idade. O nome
 * também existe em `auth.users.raw_user_meta_data`, onde o cadastro o escreve
 * para o gatilho `handle_new_user` o semear — e, depois disso, **nada no
 * aplicativo deve lê-lo**.
 *
 * Essa é a regra que resolve a duplicidade, e ela resolve porque divergência
 * entre duas cópias só é ambiguidade quando **as duas são lidas**. Com um
 * leitor só, a outra cópia não é um segundo valor em disputa: é resíduo, e
 * resíduo tem outro tratamento (ver `lib/perfil.ts`).
 *
 * O jeito de a regra ser quebrada não é alguém discordar dela. É alguém
 * precisar do nome numa tela nova, ter `usuario` do `useAuth()` à mão, e
 * escrever `usuario.user_metadata.nome` — que funciona, compila, e mostra o
 * nome certo até a primeira correção. Era literalmente o que a `Sidebar` fazia
 * até 17/10, e é uma linha.
 *
 * ── O QUE ESTA VERIFICAÇÃO PROVA, E O QUE NÃO PROVA ──────────────────────
 *
 * Prova: `user_metadata` não aparece em **linha de código** de `src/`.
 *
 * **Não** prova que o nome exibido vem de `profiles` — prova que não vem
 * daquele metadado. Um terceiro lugar inventado amanhã passaria aqui. Também é
 * varredura **textual**, não análise sintática: o equivalente em `ast` existe
 * no backend (`tests/test_privilegio_minimo.py`) e aqui não há parser de TS à
 * mão sem dependência nova. Uma leitura escrita como
 * `usuario["user" + "_metadata"]` escaparia — e quem escreve isso num
 * formulário de perfil está fazendo outra coisa, não resolvendo um problema.
 *
 * É **catraca**, não cobertura: nasce com a árvore limpa e pega a próxima
 * leitura.
 */
import { readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const SRC = resolve(dirname(fileURLToPath(import.meta.url)));

/** O que se procura. Ver o cabeçalho para o alcance real. */
const PROIBIDO = "user_metadata";

/**
 * Isenções, impressas a cada execução.
 *
 * Isenção silenciosa é como uma verificação deixa de verificar sem ninguém
 * notar (§1 das lições). **Hoje a lista está vazia**, e isso é informação: a
 * semeadura do metadado no cadastro (`lib/autenticacao.ts`) passa `nome` em
 * `options: { data: { nome } }` e **não** menciona `user_metadata`, então nem
 * ela precisa de isenção.
 */
const ISENTOS: string[] = [];

function arquivosDeFonte(dir: string, achados: string[] = []): string[] {
  for (const nome of readdirSync(dir)) {
    const caminho = join(dir, nome);
    if (statSync(caminho).isDirectory()) {
      arquivosDeFonte(caminho, achados);
      continue;
    }
    if (!/\.tsx?$/.test(nome)) continue;
    // Arquivos de teste ficam fora, como em `alcance.test.ts`: o que a regra
    // protege é o que vai ao navegador. Um dublê que monte
    // `{ user_metadata: ... }` como dado de entrada não lê nada em produção —
    // e `lib/perfil.test.ts` precisa poder montar um `User` do Supabase.
    if (/\.test\.tsx?$/.test(nome)) continue;
    achados.push(caminho);
  }
  return achados;
}

/**
 * Tira comentários de bloco e de linha.
 *
 * Os cabeçalhos deste projeto EXPLICAM `user_metadata` em prosa, e muito —
 * sem isto, a verificação acusaria a documentação da própria regra, que é o
 * oposto do que ela existe para fazer.
 *
 * É aproximação, não parser: uma sequência de abertura de comentário dentro de
 * um literal de string confundiria. Está no alcance declarado do cabeçalho, e
 * não há nenhuma hoje — a guarda abaixo exercita o removedor a cada execução.
 */
function semComentarios(fonte: string): string {
  return fonte
    .replace(/\/\*[\s\S]*?\*\//g, " ")
    .replace(/\/\/[^\n]*/g, " ");
}

/** Linhas de código (1-based) em que o termo aparece. */
function linhasComOTermo(fonte: string, termo: string): number[] {
  const limpo = semComentarios(fonte).split("\n");
  const achadas: number[] = [];
  limpo.forEach((linha, indice) => {
    if (linha.includes(termo)) achadas.push(indice + 1);
  });
  return achadas;
}

describe("a fonte do nome do perfil (PERFIL-01, Regra 1)", () => {
  const arquivos = arquivosDeFonte(SRC);
  const relativos = arquivos.map((caminho) => relative(SRC, caminho).replace(/\\/g, "/"));

  it("imprime o alcance e as isencoes", () => {
    console.log(
      `[fonteDoNomeDoPerfil] ${arquivos.length} arquivos de src/ varridos por ` +
        `"${PROIBIDO}" em linha de codigo.`,
    );
    console.log(
      ISENTOS.length === 0
        ? "[fonteDoNomeDoPerfil] isencoes: NENHUMA — a regra vale para src/ inteiro."
        : `[fonteDoNomeDoPerfil] isencoes: ${ISENTOS.join(", ")}`,
    );
    expect(true).toBe(true);
  });

  // --- a guarda do proprio instrumento -------------------------------------
  //
  // "Um sabotador morto se le como ponto cego" (§4 das licoes). Se a varredura
  // deixasse de achar arquivos, ou o removedor de comentarios comesse o codigo
  // junto, a verificacao passaria sem verificar nada — e passaria para sempre.

  it("a varredura de fato enxerga a arvore", () => {
    expect(arquivos.length).toBeGreaterThan(40);
    expect(relativos).toContain("components/Sidebar.tsx");
    expect(relativos).toContain("lib/perfil.ts");
  });

  it("o removedor de comentarios nao come o codigo", () => {
    const fonte = [
      "// user_metadata num comentario de linha",
      "/* user_metadata num bloco */",
      "const x = usuario.user_metadata.nome;",
    ].join("\n");
    expect(linhasComOTermo(fonte, PROIBIDO)).toEqual([3]);
  });

  it("acharia a leitura se ela existisse", () => {
    // O controle positivo, embutido: o instrumento é exercitado contra uma
    // fonte que TEM o defeito, a cada execução. Sem isto, "nenhuma ocorrência"
    // e "a varredura não funciona" produzem o mesmo verde.
    const fonte = 'const nome = (usuario?.user_metadata?.nome as string) ?? "";';
    expect(linhasComOTermo(fonte, PROIBIDO)).toEqual([1]);
  });

  // --- a regra -------------------------------------------------------------

  it("nenhum arquivo de src/ le user_metadata em codigo", () => {
    const ofensores: string[] = [];

    arquivos.forEach((caminho, indice) => {
      const relativo = relativos[indice];
      if (ISENTOS.includes(relativo)) return;
      const linhas = linhasComOTermo(readFileSync(caminho, "utf8"), PROIBIDO);
      if (linhas.length > 0) ofensores.push(`${relativo}:${linhas.join(",")}`);
    });

    expect(
      ofensores,
      "o nome do perfil tem fonte de verdade unica em public.profiles " +
        "(PERFIL-01). Estes arquivos leem o metadado do Auth, que e apenas o " +
        "insumo de criacao:\n  " +
        ofensores.join("\n  ") +
        "\nLeia de usePerfil()/nomeDoPerfil(). Ver docs/DECISAO-FONTE-DO-PERFIL.md.",
    ).toEqual([]);
  });
});
