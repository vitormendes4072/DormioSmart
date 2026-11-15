import { readFileSync } from "node:fs";
import ts from "typescript";
import { expect, it } from "vitest";

it("App carrega cada página somente por rotaSobDemanda", () => {
  const fonte = ts.createSourceFile(
    "App.tsx",
    readFileSync(new URL("./App.tsx", import.meta.url), "utf8"),
    ts.ScriptTarget.Latest,
    true,
    ts.ScriptKind.TSX,
  );
  const caminhos: string[] = [];
  const problemas: string[] = [];
  const pagina = (no: ts.Node | undefined): no is ts.StringLiteralLike =>
    !!no && ts.isStringLiteralLike(no) && no.text.startsWith("./pages/");

  function visitar(no: ts.Node) {
    if ((ts.isImportDeclaration(no) || ts.isExportDeclaration(no)) && pagina(no.moduleSpecifier)) {
      problemas.push(`Import estático: ${no.moduleSpecifier.text}`);
    }
    if (ts.isCallExpression(no) && no.expression.kind === ts.SyntaxKind.ImportKeyword && pagina(no.arguments[0])) {
      const caminho = no.arguments[0].text;
      caminhos.push(caminho);
      let ancestral: ts.Node = no;
      while (ancestral.parent && !ts.isArrowFunction(ancestral) && !ts.isFunctionExpression(ancestral)) {
        ancestral = ancestral.parent;
      }
      const chamada = ancestral.parent;
      if (!chamada || !ts.isCallExpression(chamada) || !ts.isIdentifier(chamada.expression)
        || chamada.expression.text !== "rotaSobDemanda" || chamada.arguments[1] !== ancestral) {
        problemas.push(`Import dinâmico sem rotaSobDemanda: ${caminho}`);
      }
    }
    ts.forEachChild(no, visitar);
  }

  visitar(fonte);
  expect(problemas).toEqual([]);
  expect(caminhos).not.toHaveLength(0);
});
