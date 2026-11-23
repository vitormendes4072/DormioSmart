import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import { mensagemDoServidor } from "./mensagemDoServidor";

// Falhas de entradas que o próprio cliente monta e diagnósticos de formato.
// A frase genérica é acompanhada pelo texto do servidor em Detalhes técnicos.
const genericas = new Set([
  "'ate' antes de 'desde'",
  "'bancada' obrigatorio, true ou false",
  "'desde' e 'ate' devem ambos ter fuso horario ou ambos nao ter",
  "'desde' e 'ate' obrigatorios, em ISO 8601",
  "'desde' e 'ate' precisam de fuso horario",
  "'desde' e posterior a 'ate'",
  "X-Device-Token ausente",
  "bancada_atual deve ser verdadeiro ou falso",
  "campo amostras deve ser inteiro maior que zero",
  "campo cal deve ser 0 ou 1",
  "campo desconhecido: {}",
  "campos desconhecidos: {}",
  "o corpo tem de ser um objeto JSON",
  "campo device_id ausente (obrigatorio na ingestao por sessao)",
  "campo device_id deve ser texto",
  "campo epoca_s deve ser inteiro de segundos",
  "campo epoca_s fora da faixa ([{}, {}]): {}",
  "campo f deve ser lista de {} numeros",
  "campo f exige epoca_s",
  "campo fs deve ser numero em (0, {}]",
  "campo g deve ser lista de 3 numeros",
  "campo g deve ser unitario (|g| = 1 +- {}): |g| = {}",
  "campo leituras ausente",
  "campo leituras deve ser uma lista",
  "campo leituras vazio",
  "campo metodo deve ser um de {}",
  "campo metodo veio sem epoca_s",
  "campo obrigatorio ausente: {}",
  "campo status deve ser um de {}",
  "campo total incoerente com (ax, ay, az): recebido {}, esperado ~{}",
  "campo {} deve ser numero finito",
  "campo {} exige f",
  "campos f, g e fs vem juntos: falta {}",
  "corpo JSON obrigatorio",
  "corpo deve ser um objeto JSON",
  "credencial ausente",
  "cursor invalido",
  "device invalido",
  "envie JSON",
  "epocas_esperadas deve ser um número inteiro entre 1 e 32000",
  "impressao_ids inválida",
  "informe ao menos um campo: {}",
  "janela acima de {} h",
  "lote com {} leituras; o maximo e {}",
  "parametro 'device' nao e um uuid valido",
  "parametro 'limite' deve ser inteiro maior que zero",
  "parametro '{}' nao e um instante ISO 8601 valido",
  "parametros obrigatorios: {}",
  "receber_leituras deve ser booleano",
  "tipo deve ser um de {}"
]);

const fonte = readFileSync(new URL("./mensagemDoServidor.ts", import.meta.url), "utf8");
const tabela = JSON.parse(fonte.slice(fonte.indexOf("= {") + 2, fonte.indexOf("\n};") + 2)) as Record<string, string>;

describe("UI-41: mensagens do servidor", () => {
  it.each(Object.entries(tabela))("apresenta %s", (chave, frase) => {
    expect(mensagemDoServidor(chave.split("{}").join("60"))).toEqual({ mensagem: frase });
  });

  it("preserva o motivo desconhecido para a tela exibir nos detalhes", () => {
    expect(mensagemDoServidor("motivo novo")).toEqual({
      mensagem: "Não foi possível concluir o pedido.", detalhe: "motivo novo",
    });
  });

  it("exige uma decisão explícita para cada mensagem literal do backend", () => {
    const python = process.platform === "win32" ? "python" : "python3";
    const literais = JSON.parse(execFileSync(python, ["-c", `import ast, json
from pathlib import Path
def texto(no):
    if isinstance(no, ast.Constant) and isinstance(no.value, str):
        return no.value
    if isinstance(no, ast.JoinedStr):
        return "".join(texto(p) if isinstance(p, ast.Constant) else "{}" for p in no.values)
    if isinstance(no, ast.BinOp) and isinstance(no.op, ast.Add):
        inicio = texto(no.left)
        if inicio is not None:
            return inicio + (texto(no.right) or "{}")
def mensagens(arvore, nome):
    for no in ast.walk(arvore):
        if isinstance(no, ast.Call) and isinstance(no.func, ast.Name) and no.func.id == "jsonify":
            for arg in no.args:
                if isinstance(arg, ast.Dict):
                    for chave, valor in zip(arg.keys, arg.values):
                        if texto(chave) == "error" and texto(valor):
                            yield texto(valor)
        if isinstance(no, ast.Raise) and isinstance(no.exc, ast.Call):
            if isinstance(no.exc.func, ast.Name) and no.exc.func.id == "PedidoInvalido":
                motivo = texto(no.exc.args[0])
                if motivo:
                    yield motivo
        if isinstance(no, ast.Return):
            v = no.value
            if isinstance(v, ast.Tuple) and len(v.elts) >= 2 and isinstance(v.elts[0], ast.Constant) and v.elts[0].value in (None, False):
                if texto(v.elts[1]):
                    yield texto(v.elts[1])
            if nome == "validacao.py" and texto(v):
                yield texto(v)
raiz = Path("web-app")
nomes = ("routes.py", "auth.py", "consulta.py", "dispositivos.py", "ingestao.py", "lote.py", "lista_de_espera.py", "perfil.py", "trecho.py", "validacao.py")
print(json.dumps(sorted({m for nome in nomes for m in mensagens(ast.parse((raiz / nome).read_text(encoding="utf-8")), nome)})))
`], {
      cwd: fileURLToPath(new URL("../../../", import.meta.url)),
      encoding: "utf8",
    })) as string[];
    expect(literais).toContain("campo ts esta no futuro");
    expect(literais.filter((chave) => !Object.prototype.hasOwnProperty.call(tabela, chave) && !genericas.has(chave))).toEqual([]);
  });
});

