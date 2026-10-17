/**
 * A finalidade declarada de `profiles.idade` (PERFIL-01 / LGPD-04).
 *
 * ── POR QUE ESTE ARQUIVO EXISTE ──────────────────────────────────────────
 *
 * `idade` era coluna morta: existia no esquema desde a migração `001`,
 * nenhuma tela a preenchia e nenhuma funcionalidade a lia (`LGPD-04`). Ao
 * passar a ser coletada, ela precisa de **finalidade declarada** — e a
 * finalidade tem de ser uma coisa que o código faz, não uma que a política de
 * privacidade promete.
 *
 * A finalidade é esta: **dizer ao titular se a idade dele está dentro ou fora
 * da faixa das coortes em que os métodos citados por este trabalho foram
 * validados.** Aplicar um classificador validado em adultos a uma pessoa de 70
 * anos é extrapolação, e registrar a idade é o que permite *dizer isso* em vez
 * de calar.
 *
 * ── O QUE ESTE MÓDULO NÃO FAZ, E É IMPORTANTE QUE NÃO FAÇA ───────────────
 *
 * Não calcula nada. Não pondera métrica, não estratifica série, não altera
 * limiar, não entra em modelo. Ele escolhe um **texto** a partir de uma faixa.
 *
 * Declarar que a idade "estratifica a análise do sono" soaria melhor e seria
 * finalidade declarada que o código não cumpre — o §6 das lições na forma mais
 * barata de cometê-lo, porque um parágrafo de política de privacidade não tem
 * como ficar vermelho. Se um dia a idade entrar em cálculo, isso é
 * **finalidade nova** e exige declaração nova ANTES (item `ML-07`).
 *
 * ── PROCEDÊNCIA DE CADA NÚMERO (§3 das lições) ───────────────────────────
 *
 * Nenhum limite aqui é clínico, e nenhum foi derivado por este trabalho:
 *
 * | Número | O que é | Fonte |
 * |---|---|---|
 * | 12 | **especificação legal** — fronteira criança/adolescente | Lei 13.709/2018 (LGPD), art. 14, e ECA art. 2º |
 * | 18 | **especificação legal** — maioridade | Código Civil, art. 5º |
 * | 60 | **especificação legal** — pessoa idosa | Lei 10.741/2003, art. 1º |
 *
 * As faixas são legais de propósito. Fronteira clínica de "sono do idoso"
 * existe na literatura e **não** está nas fontes que este repositório cita —
 * usar um número de memória seria o §3 inteiro (*"de onde veio este número?"*).
 *
 * As coortes citadas, com o que o repositório afirma sobre cada uma, estão em
 * `docs/ML-DATASETS-E-PLANO.md` e `docs/LIMITACOES-TCC.md` X.2.
 */

/** Fronteiras etárias. Especificação legal, não medição — ver o cabeçalho. */
export const IDADE_DE_ADOLESCENTE = 12;
export const IDADE_DE_MAIORIDADE = 18;
export const IDADE_DE_PESSOA_IDOSA = 60;

export type FaixaEtaria = "crianca" | "adolescente" | "adulto" | "pessoa-idosa";

/** Quanto do que o trabalho cita cobre a faixa do titular. */
export type Cobertura =
  /** Há coorte citada nessa faixa, e ela é a faixa principal. */
  | "coberta"
  /** Há coorte citada, com ressalva relevante dita junto. */
  | "parcial"
  /** Nenhuma coorte citada cobre a faixa. Aplicar é extrapolar. */
  | "nao-coberta";

export type Aplicabilidade = {
  faixa: FaixaEtaria;
  cobertura: Cobertura;
  /** Frase para a tela. Uma só, e sem promessa de diagnóstico. */
  aviso: string;
  /** Verdadeiro quando o art. 14 da LGPD incide. Ver `LGPD-05`. */
  menorDeIdade: boolean;
};

export function faixaDaIdade(idade: number): FaixaEtaria {
  if (idade < IDADE_DE_ADOLESCENTE) return "crianca";
  if (idade < IDADE_DE_MAIORIDADE) return "adolescente";
  if (idade < IDADE_DE_PESSOA_IDOSA) return "adulto";
  return "pessoa-idosa";
}

/**
 * O aviso de aplicabilidade, ou `null` quando não há idade.
 *
 * **`null` é o caso normal, não o caso de erro.** A idade é opcional — campo
 * obrigatório para alimentar um aviso seria coleta desproporcional à
 * finalidade (art. 6º, III). Sem idade, o aviso simplesmente não existe, e a
 * tela não pede nada.
 */
export function aplicabilidadeDaIdade(idade: number | null | undefined): Aplicabilidade | null {
  if (idade == null || !Number.isInteger(idade) || idade < 0) return null;

  const faixa = faixaDaIdade(idade);
  const menorDeIdade = idade < IDADE_DE_MAIORIDADE;

  switch (faixa) {
    case "crianca":
    case "adolescente":
      return {
        faixa,
        cobertura: "parcial",
        menorDeIdade,
        aviso:
          "A literatura que este trabalho cita para esta faixa de idade é pediátrica " +
          "e de acelerômetro de punho (137 participantes de 8 a 16 anos), não de " +
          "travesseiro. A comparação com os resultados apresentados aqui é indireta.",
      };
    case "adulto":
      return {
        faixa,
        cobertura: "coberta",
        menorDeIdade,
        aviso:
          "As coortes de validação que este trabalho cita são de pessoas adultas — é " +
          "a faixa para a qual os números apresentados foram medidos. As fontes não " +
          "publicam o intervalo exato de idade de todas elas.",
      };
    case "pessoa-idosa":
      return {
        faixa,
        cobertura: "nao-coberta",
        menorDeIdade,
        aviso:
          "Nenhuma das coortes de validação citadas por este trabalho cobre esta faixa " +
          "de idade. Aplicar aqui os números apresentados é extrapolar para fora do " +
          "que foi medido, e o resultado deve ser lido com essa ressalva.",
      };
  }
}
