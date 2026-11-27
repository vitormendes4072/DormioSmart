/**
 * A linguagem das telas depois do login (UI-39, `docs/PADRAO-VISUAL.md`, §10).
 *
 * Reprova jargão no texto que vai à tela. O conjunto de arquivos NÃO é uma
 * lista à mão: sai dos imports das telas, para que um componente novo
 * entre na conferência sozinho. Comentário, classe e nome de variável não
 * contam; o que está num `<details>` de "Detalhes técnicos" também não.
 */
import { existsSync, readFileSync } from "node:fs";
import { dirname, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import ts from "typescript";
import { describe, expect, it } from "vitest";

const RAIZ = dirname(fileURLToPath(import.meta.url));

const TELAS = ["Dashboard", "Noite", "Historico", "Dispositivos", "Coletar", "Settings", "PrimeirosPassos"]
  .map((tela) => resolve(RAIZ, `pages/${tela}.tsx`));

/** Fora da regra, cada um pelo seu motivo. */
const FORA = new Map([
  ["lib/consentimento.ts", "mudar o texto é mudar a versão e pedir aceite de novo (LGPD-15)"],
  ["components/TelaDeConsentimento.tsx", "o mesmo: é o texto do consentimento"],
  ["lib/exportar.ts", "os nomes de coluna do CSV são contrato de dados"],
]);

/** O que o glossário troca. Os acentos separam o texto do nome de código (`epoca`). */
const JARGAO: Array<[string, RegExp]> = [
  ["época", /(?<![\p{L}])épocas?(?![\p{L}])/iu],
  ["epocas, sem acento", /\bas epocas\b/i],
  ["token", /(?<![\p{L}_-])tokens?(?![\p{L}_-])/iu],
  ["leitura", /(?<![\p{L}_-])leituras?(?![\p{L}_-])/iu],
  ["cobertura", /(?<![\p{L}_-])cobertura(?![\p{L}_-])/iu],
  ["lacuna", /(?<![\p{L}_-])lacunas?(?![\p{L}_-])/iu],
  ["captação", /captaç(ão|ões)/iu],
  ["amostra", /(?<![\p{L}_-])amostras?(?![\p{L}_-])/iu],
  ["magnitude", /(?<![\p{L}_-])magnitude(?![\p{L}_-])/iu],
  ["tempo medido", /tempo (que foi )?medido/iu],
  ["sem medição", /sem medição/iu],
  ["desvio", /desvio do repouso/iu],
  ["limiar", /(?<![\p{L}_-])limiar(?![\p{L}_-])/iu],
  ["janela", /(?<![\p{L}_-])janela(?![\p{L}_-])/iu],
  ["credencial", /(?<![\p{L}_-])credencial(?![\p{L}_-])/iu],
  ["criptográfico", /criptográfic/iu],
  ["firmware", /(?<![\p{L}_/-])firmware(?![\p{L}_/-])/iu],
  ["peça", /MPU-?6050|ESP32/i],
  ["taxa do sensor", /taxa do sensor|por taxa/iu],
];

/** Os arquivos do app que as telas alcançam pelos imports. */
function alcancados(): string[] {
  const vistos = new Set<string>();
  const fila = [...TELAS];
  while (fila.length > 0) {
    const arquivo = fila.pop()!;
    if (vistos.has(arquivo) || FORA.has(relativo(arquivo))) continue;
    vistos.add(arquivo);
    for (const { fileName } of ts.preProcessFile(readFileSync(arquivo, "utf8")).importedFiles) {
      if (!fileName.startsWith(".")) continue;
      const achado = [".ts", ".tsx"]
        .map((extensao) => resolve(dirname(arquivo), fileName) + extensao)
        .find((caminho) => existsSync(caminho));
      if (achado) fila.push(achado);
    }
  }
  return [...vistos];
}

function relativo(arquivo: string): string {
  return relative(RAIZ, arquivo).replace(/\\/g, "/");
}

/** Os textos de um arquivo que podem ir à tela, com a linha. */
function textos(nome: string, codigo: string): Array<{ linha: number; texto: string }> {
  const fonte = ts.createSourceFile(nome, codigo, ts.ScriptTarget.Latest, true,
    nome.endsWith("x") ? ts.ScriptKind.TSX : ts.ScriptKind.TS);
  const achados: Array<{ linha: number; texto: string }> = [];

  const ver = (no: ts.Node): void => {
    if (ts.isImportDeclaration(no) || ts.isTypeNode(no)) return;
    // As chaves do tradutor são a entrada da API. Seus valores continuam sob o glossário.
    if (nome === "lib/mensagemDoServidor.ts" && no.parent && ts.isPropertyAssignment(no.parent)
      && no.parent.name === no && ts.isStringLiteral(no)) return;
    if (ts.isJsxAttribute(no)
      && /^(className|id|key|htmlFor|data-testid|aria-labelledby|aria-controls|dataKey)$/.test(no.name.getText())) return;
    // `console.*` é para quem desenvolve.
    if (ts.isCallExpression(no) && no.expression.getText().startsWith("console.")) return;
    if (ts.isJsxElement(no) && no.openingElement.tagName.getText() === "details") {
      const resumo = no.children.find((filho): filho is ts.JsxElement =>
        ts.isJsxElement(filho) && filho.openingElement.tagName.getText() === "summary");
      if (resumo?.getText().includes("Detalhes técnicos")) return;
    }
    if (ts.isJsxText(no) || ts.isStringLiteral(no) || ts.isNoSubstitutionTemplateLiteral(no)
      || ts.isTemplateHead(no) || ts.isTemplateMiddle(no) || ts.isTemplateTail(no)) {
      const texto = no.text.replace(/\s+/g, " ").trim();
      if (texto) achados.push({ linha: fonte.getLineAndCharacterOfPosition(no.getStart()).line + 1, texto });
    }
    ts.forEachChild(no, ver);
  };
  ver(fonte);
  return achados;
}

function jargaoEm(nome: string, codigo: string): string[] {
  return textos(nome, codigo).flatMap(({ linha, texto }) =>
    JARGAO.filter(([, regra]) => regra.test(texto)).map(([termo]) => `${nome}:${linha} [${termo}] ${texto}`));
}

it("UI-61: a meta usa o vocabulário de registro, com uma única frase de ajuda sobre dormir", () => {
  const proibido = /\b(?:dormir|sono|ideal|saudável|deveria|qualidade|noite)\b|\brecomend/iu;
  const ajuda = "O Smart Dormio não recomenda quantas horas dormir.";
  const arquivos = ["components/CampoMetaDiaria.tsx", "components/ComparacaoDaMeta.tsx", "components/GraficoDeTempoPorDia.tsx"];
  const nomeDaJornada = "pages/PrimeirosPassos.tsx";
  const jornada = ts.createSourceFile(nomeDaJornada, readFileSync(resolve(RAIZ, nomeDaJornada), "utf8"), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const formulario = jornada.statements.find((no) => ts.isFunctionDeclaration(no) && no.name?.text === "MetaDaJornada");
  const titulos = jornada.statements
    .flatMap((no) => ts.isVariableStatement(no) ? [...no.declarationList.declarations] : [])
    .find((no) => no.name.getText(jornada) === "titulos")?.initializer;
  const titulo = titulos && ts.isObjectLiteralExpression(titulos) ? titulos.properties.find((no) => no.name?.getText(jornada) === "meta") : undefined;
  expect(formulario).toBeDefined();
  expect(titulo).toBeDefined();
  const ocorrencias = [...arquivos.flatMap((nome) => textos(nome, readFileSync(resolve(RAIZ, nome), "utf8"))),
    ...textos(nomeDaJornada, `const titulos = { ${titulo!.getText(jornada)} };\n${formulario!.getText(jornada)}`)]
    .filter(({ texto }) => proibido.test(texto));
  expect(ocorrencias.map(({ texto }) => texto)).toEqual([`É uma meta sua. ${ajuda}`]);
});

describe("o detector de jargão (controle positivo)", () => {
  const acusa = (codigo: string) => jargaoEm("exemplo.tsx", codigo).length > 0;

  it("acusa no JSX, no atributo, na crase e no ternário", () => {
    expect(acusa("const a = <p>3 épocas aguardando</p>;")).toBe(true);
    expect(acusa('const a = <button aria-label="Copiar token" />;')).toBe(true);
    expect(acusa("const a = `${n} leituras`;")).toBe(true);
    expect(acusa('const a = n === 1 ? "época" : "outra";')).toBe(true);
  });

  it("não acusa comentário, classe, nome de código nem detalhe técnico", () => {
    expect(acusa("// a época tem 30 s\nconst epoca = leitura.token;")).toBe(false);
    expect(acusa('const a = <p className="cobertura">ok</p>;')).toBe(false);
    expect(acusa("const a = <details><summary>Detalhes técnicos</summary>amostras</details>;")).toBe(false);
  });

  it("um details qualquer não é esconderijo", () => {
    expect(acusa("const a = <details><summary>Mais</summary>amostras</details>;")).toBe(true);
  });
});

describe("as telas não falam a língua do desenvolvedor (UI-39)", () => {
  const arquivos = alcancados();

  it("a conferência alcança os componentes e as mensagens das telas", () => {
    const nomes = arquivos.map(relativo);
    for (const esperado of ["pages/PrimeirosPassos.tsx", "components/TokenRecemCriado.tsx", "components/CartaoDaNoite.tsx", "components/MeusDispositivos.tsx",
      "components/AvisoDeLacuna.tsx", "lib/coleta.ts", "lib/envioDaNoite.ts", "lib/dispositivos.ts"]) {
      expect(nomes).toContain(esperado);
    }
  });

  it("nenhum texto usa jargão", () => {
    expect(arquivos.flatMap((arquivo) => jargaoEm(relativo(arquivo), readFileSync(arquivo, "utf8")))).toEqual([]);
  });

  it("o texto de calibração que o Android manda à tela Noite também não", () => {
    const java = readFileSync(resolve(RAIZ,
      "../android/app/src/main/java/app/dormiosmart/coleta/Calibracao.java"), "utf8");
    const frases = [...java.matchAll(/String\.format\(\s*PT_BR,\s*"([^"]+)"/g)].map((achado) => achado[1]);
    expect(frases.length).toBeGreaterThan(0);
    for (const frase of frases) expect(frase).not.toMatch(JARGAO[0][1]);
  });

  it("os botões que a política de privacidade cita guardam o nome", () => {
    const tudo = arquivos.flatMap((arquivo) => textos(relativo(arquivo), readFileSync(arquivo, "utf8")))
      .map(({ texto }) => texto);
    for (const nome of ["Excluir…", "Marcar como bancada", "Desmarcar", "Excluir conta", "Editar dados",
      "Iniciar a noite", "Encerrar a noite", "Meus dispositivos", "Seus dados", "Primeiros passos"]) {
      expect(tudo).toContain(nome);
    }
  });
});
