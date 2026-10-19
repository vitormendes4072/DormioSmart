/**
 * Perfil do titular — leitura e correção (UI-11 + PERFIL-01 / LGPD art. 18, III).
 *
 * ── O QUE MUDOU DESDE O `UI-11`, E POR QUÊ ───────────────────────────────
 *
 * O `UI-11` entregou esta tela gravando **tudo** pelo Supabase Auth, e estava
 * certo em fazê-lo: naquele momento `profiles` era escrita uma vez pelo
 * gatilho do signup e **lida por nada**, então gravar nela não mudaria uma
 * letra em tela nenhuma. O cabeçalho anterior deste arquivo documentava isso,
 * e a consequência declarada era: *`profiles.nome` passa a ser cópia que pode
 * divergir; decidir isso é o `PERFIL-01`.*
 *
 * O `PERFIL-01` decidiu: **`public.profiles` é a fonte de verdade** do nome e
 * da idade. Este arquivo é a reconciliação — não a duplicação. O que foi
 * mantido do `UI-11` (e é a maior parte): a normalização, a validação antes da
 * rede, `calcularAlteracao` para não escrever o que não mudou, e todo o
 * tratamento do e-mail, inclusive o estado `email-pendente`.
 *
 * ── ONDE CADA CAMPO É GRAVADO, E POR QUÊ NÃO HÁ DIVERGÊNCIA POSSÍVEL ─────
 *
 *   nome   -> PATCH /api/me/perfil  (profiles)
 *   idade  -> PATCH /api/me/perfil  (profiles)
 *   email  -> supabase.auth.updateUser (é CREDENCIAL, não perfil)
 *
 * **Cada campo tem um destino, e nenhum tem dois.** É isso que impede o modo
 * de falha que o backlog previa para esta saída do `PERFIL-01` — *"gravou no
 * Auth, falhou em `profiles`, e agora os dois divergem e nada diz qual vale"*.
 * Não há tie-break porque não há empate: `nome` não pode divergir de si mesmo
 * quando só existe um lugar que o escreve e um que o lê.
 *
 * Há duas chamadas a dois serviços, como já havia no `UI-11`, e um desfecho
 * parcial continua possível — perfil gravado, e-mail pendente. Esse desfecho
 * tem nome próprio e é relatado campo por campo, exatamente como antes.
 *
 * ── A LIMPEZA DE RESÍDUO, QUE NÃO É UMA SEGUNDA ESCRITA DO MESMO DADO ────
 *
 * `auth.users.raw_user_meta_data.nome` continua existindo: é o **insumo de
 * criação**, lido uma vez pelo gatilho `handle_new_user`. Ninguém mais o lê —
 * e `fonteDoNomeDoPerfil.test.ts` reprova se alguém voltar a ler.
 *
 * Mas, depois de uma correção, ele guardaria o nome **antigo**. Nenhuma tela
 * fica errada por isso (ninguém lê), e ainda assim é problema: o titular
 * exerceu o art. 18, III e o valor inexato continuaria armazenado, sem
 * finalidade — contra o próprio art. 18, III e a minimização do art. 6º, III.
 *
 * Por isso, **depois** de o `PATCH` ter sucedido e só então, limpamos o
 * resíduo. Três propriedades, porque é aqui que um desenho descuidado
 * recriaria o problema que a decisão eliminou:
 *
 *   1. Não é a escrita autoritativa. Se falhar, a correção **aconteceu**, e a
 *      tela diz que aconteceu — porque aconteceu. `residuoLimpo` é campo
 *      próprio do resultado, para que nada minte em nenhuma das direções.
 *   2. É retentável sem estado: toda gravação de perfil bem-sucedida tenta de
 *      novo, e a exclusão de conta remove `auth.users` inteira.
 *   3. **Limpa em vez de sincronizar.** Gravar o nome novo nos dois lados
 *      manteria duas cópias atuais e nada dizendo qual manda, reconstruindo a
 *      ambiguidade. `null` não pode ser confundido com fonte de verdade.
 *
 * Por que no cliente: `updateUser` age sobre a **sessão** de quem chama. O
 * cliente do Flask só autentica o PostgREST; fazer isso no servidor exigiria a
 * API de administração, isto é, papel privilegiado — recusado pelo `SEC-06`.
 *
 * ── PONTO CEGO DECLARADO ─────────────────────────────────────────────────
 *
 * O dublê de `updateUser` exercita a orquestração deste módulo, **não** o
 * comportamento do Supabase: não prova que a troca de e-mail exige
 * confirmação, nem que `data: { nome: null }` apaga a chave. Fecha com um
 * projeto Supabase de teste — registrado no `UI-11`.
 *
 * Raciocínio completo: `docs/DECISAO-FONTE-DO-PERFIL.md`.
 */
import type { User } from "@supabase/supabase-js";

import { requisitarJson } from "./api";
import { traduzirErroDeAuth } from "./autenticacao";
import { obterSupabase } from "./supabase";

/**
 * Teto de caracteres do nome.
 *
 * ⚙️ **Decisão de interface, não limite de banco** (§3 das lições). O banco tem
 * um teto próprio e MAIOR — 200, `profiles_nome_tamanho`, migração `008` —
 * porque ele é o backstop do caminho que não passa por validação nenhuma deste
 * projeto: `authenticated` tem GRANT de UPDATE em `profiles`, e o navegador
 * fala direto com o PostgREST pela chave `anon`, que é pública por design. A
 * assimetria entre 120 e 200 é deliberada: iguais, qualquer afrouxamento deste
 * campo viraria erro de constraint.
 */
export const NOME_MAXIMO_DO_PERFIL = 120;

/** O que a rota `GET /api/me/perfil` devolve. */
export type PerfilDoServidor = {
  nome: string | null;
  idade: number | null;
  updated_at?: string | null;
  /** A rota criou a linha agora, porque faltava. Ver o docstring da rota. */
  perfil_criado_agora?: boolean;
};

/** Estado do formulário. `idade` é texto porque campo de formulário é texto —
 *  guardá-la como número obrigaria a inventar um valor para "vazio". */
export type DadosDoPerfil = { nome: string; idade: string; email: string };

/** O que de fato mudou. `idade: null` é "apague", ausente é "não mexa". */
export type AlteracaoDePerfil = { nome?: string; idade?: number | null; email?: string };

export type ResultadoDePerfil =
  /** O formulário não mudou nada. Não houve ida à rede. */
  | { tipo: "nada-a-fazer" }
  /** Tudo que foi pedido já vale agora. */
  | { tipo: "salvo"; perfilGravado: boolean; residuoLimpo: boolean }
  /** O e-mail depende de confirmação; o endereço de acesso segue o antigo. */
  | { tipo: "email-pendente"; emailPendente: string; perfilGravado: boolean; residuoLimpo: boolean }
  | { tipo: "invalido"; mensagem: string }
  | { tipo: "erro"; mensagem: string; perfilGravado: boolean; residuoLimpo: boolean };

const SEM_CONFIGURACAO = "Autenticação não configurada. Confira o arquivo frontend/.env.";

const CAMINHO = "/api/me/perfil";

// ---------------------------------------------------------------------
// Leitura
// ---------------------------------------------------------------------

/**
 * Perfil do titular, da fonte de verdade.
 *
 * Deixa o erro subir: quem chama (o `PerfilContext`) decide o que mostrar. Um
 * `catch` aqui devolvendo perfil vazio faria "não deu para ler" parecer "não
 * há nome" — e a tela mostraria em branco o nome de quem tem nome, que é
 * degradação silenciosa (§7 das lições).
 */
export async function buscarPerfil(): Promise<PerfilDoServidor> {
  return requisitarJson<PerfilDoServidor>(CAMINHO);
}

/** E-mail de acesso a partir da sessão. O e-mail **não** está em `profiles`:
 *  ele é credencial, e mora no serviço de autenticação. */
export function emailDaSessao(usuario: User | null): string {
  return typeof usuario?.email === "string" ? usuario.email : "";
}

/** Nome exibível, a partir do que a rota devolveu. */
export function nomeDoPerfil(perfil: PerfilDoServidor | null): string {
  const bruto = perfil?.nome;
  return typeof bruto === "string" ? bruto.trim() : "";
}

/** Idade, ou `null`. Qualquer coisa que não seja inteiro conta como ausente —
 *  ler número de um corpo JSON alheio e confiar é como `0` vira idade. */
export function idadeDoPerfil(perfil: PerfilDoServidor | null): number | null {
  const bruto = perfil?.idade;
  return typeof bruto === "number" && Number.isInteger(bruto) ? bruto : null;
}

/** O formulário, preenchido a partir do que vale hoje. */
export function formularioDoPerfil(
  perfil: PerfilDoServidor | null,
  usuario: User | null,
): DadosDoPerfil {
  const idade = idadeDoPerfil(perfil);
  return {
    nome: nomeDoPerfil(perfil),
    idade: idade === null ? "" : String(idade),
    email: emailDaSessao(usuario),
  };
}

// ---------------------------------------------------------------------
// Normalização e validação
// ---------------------------------------------------------------------

/**
 * Normaliza o nome: tira as pontas e colapsa espaço interno.
 *
 * Tem de ser a MESMA normalização de `normalizar_nome` em `web-app/perfil.py`.
 * Se divergissem, o cliente concluiria que nada mudou e o servidor gravaria
 * outra coisa — ou o contrário.
 */
export function normalizarNome(texto: string): string {
  return texto.trim().replace(/\s+/g, " ");
}

/** Normaliza o e-mail: tira as pontas e baixa a caixa. O Supabase guarda e
 *  compara em minúsculas; sem isto, "Ana@x.com" sobre "ana@x.com" pareceria
 *  alteração e dispararia confirmação que não troca nada. */
export function normalizarEmail(texto: string): string {
  return texto.trim().toLowerCase();
}

export function validarNome(texto: string): { ok: true } | { ok: false; motivo: string } {
  const nome = normalizarNome(texto);
  if (nome === "") return { ok: false, motivo: "O nome não pode ficar vazio." };
  if (nome.length > NOME_MAXIMO_DO_PERFIL) {
    return {
      ok: false,
      motivo: `O nome precisa ter no máximo ${NOME_MAXIMO_DO_PERFIL} caracteres.`,
    };
  }
  return { ok: true };
}

/**
 * Lê a idade digitada. **Vazio é válido e significa `null`.**
 *
 * A idade é opcional (art. 6º, III: campo obrigatório para alimentar um aviso
 * seria coleta desproporcional), e apagar o campo é como o titular a retira —
 * o art. 18, IV ao alcance de um clique. Por isso "" não é erro de validação:
 * é uma instrução.
 *
 * A faixa espelha a constraint da migração `001` (`idade >= 0 and idade < 150`)
 * e a validação de `web-app/perfil.py`. Divergir daqui trocaria uma mensagem
 * útil por um erro de constraint do Postgres.
 */
export const IDADE_MINIMA_DO_PERFIL = 0;
export const IDADE_MAXIMA_DO_PERFIL = 149;

export function lerIdade(
  texto: string,
): { ok: true; valor: number | null } | { ok: false; motivo: string } {
  const bruto = texto.trim();
  if (bruto === "") return { ok: true, valor: null };

  // `Number()` aceitaria "1e2", " 12 " e "0x1f"; a comparação explícita com
  // dígitos recusa tudo que não é um inteiro escrito como inteiro. Aceitar
  // "1e2" gravaria 100 sem que ninguém tivesse digitado 100.
  if (!/^\d{1,3}$/.test(bruto)) {
    return { ok: false, motivo: "A idade precisa ser um número inteiro de anos." };
  }

  const valor = Number(bruto);
  if (valor < IDADE_MINIMA_DO_PERFIL || valor > IDADE_MAXIMA_DO_PERFIL) {
    return {
      ok: false,
      motivo: `A idade precisa estar entre ${IDADE_MINIMA_DO_PERFIL} e ${IDADE_MAXIMA_DO_PERFIL}.`,
    };
  }
  return { ok: true, valor };
}

/** Confere o e-mail ANTES de ir à rede.
 *
 *  Deliberadamente frouxo: não é tentativa de validar e-mail de verdade — isso
 *  não se faz com regex, e quem manda é o servidor. O objetivo é que um erro
 *  de digitação óbvio apareça como erro de digitação, e não como um fluxo de
 *  confirmação disparado para um endereço que não existe. */
export function validarEmail(texto: string): { ok: true } | { ok: false; motivo: string } {
  const email = normalizarEmail(texto);
  if (email === "") return { ok: false, motivo: "O e-mail não pode ficar vazio." };
  if (/\s/.test(email)) return { ok: false, motivo: "O e-mail não pode conter espaços." };
  const partes = email.split("@");
  if (partes.length !== 2 || partes[0] === "" || !partes[1].includes(".")) {
    return { ok: false, motivo: "E-mail inválido." };
  }
  if (partes[1].startsWith(".") || partes[1].endsWith(".")) {
    return { ok: false, motivo: "E-mail inválido." };
  }
  return { ok: true };
}

/**
 * O que mudou entre o que vale e o formulário.
 *
 * Existe para que "salvar" sem ter mexido em nada **não** escreva nada. Num
 * formulário de perfil isso não é otimização: mandar o e-mail atual como se
 * fosse novo dispararia um pedido de confirmação para trocar um endereço pelo
 * mesmo endereço, e a pessoa receberia um e-mail dizendo que sua credencial
 * está mudando.
 *
 * Idade inválida **não** entra na alteração — quem reclama é `atualizarPerfil`,
 * que valida antes de ir à rede. Aqui ela só não conta como mudança, para que
 * o botão não prometa salvar o que não vai ser salvo.
 */
export function calcularAlteracao(
  atual: DadosDoPerfil,
  formulario: DadosDoPerfil,
): AlteracaoDePerfil {
  const alteracao: AlteracaoDePerfil = {};

  const nome = normalizarNome(formulario.nome);
  if (nome !== normalizarNome(atual.nome)) alteracao.nome = nome;

  const email = normalizarEmail(formulario.email);
  if (email !== normalizarEmail(atual.email)) alteracao.email = email;

  const lida = lerIdade(formulario.idade);
  const atualLida = lerIdade(atual.idade);
  if (lida.ok && atualLida.ok && lida.valor !== atualLida.valor) {
    alteracao.idade = lida.valor;
  }
  if (!lida.ok && formulario.idade.trim() !== atual.idade.trim()) {
    // Texto inválido digitado: conta como "mexeu", para o botão habilitar e a
    // mensagem de erro aparecer. Sem isto, a pessoa digitaria "abc", o botão
    // ficaria inerte e nada explicaria por quê.
    alteracao.idade = null;
  }

  return alteracao;
}

export function nadaAFazer(alteracao: AlteracaoDePerfil): boolean {
  return (
    alteracao.nome === undefined &&
    alteracao.email === undefined &&
    alteracao.idade === undefined
  );
}

/**
 * O e-mail já vale, pela resposta do servidor?
 *
 * **Pessimista por omissão, de propósito.** Só devolve `true` quando o usuário
 * devolvido traz, ele mesmo, o endereço novo. Resposta sem usuário, usuário sem
 * `email`, ou `email` ainda no antigo — todos contam como pendente. É a mesma
 * regra do `interpretarRecibo` do `UI-10`: na dúvida, o desfecho pior é o
 * verdadeiro.
 */
export function emailJaVale(usuario: User | null | undefined, emailNovo: string): boolean {
  const atual = typeof usuario?.email === "string" ? normalizarEmail(usuario.email) : "";
  return atual !== "" && atual === normalizarEmail(emailNovo);
}

// ---------------------------------------------------------------------
// Escrita
// ---------------------------------------------------------------------

/** Limpa o resíduo do metadado. Nunca levanta: o chamador não pode ter o
 *  desfecho da correção afetado por isto. Ver o cabeçalho. */
async function limparResiduoDoMetadado(): Promise<boolean> {
  try {
    const supabase = obterSupabase();
    if (!supabase) return false;
    const { error } = await supabase.auth.updateUser({ data: { nome: null } });
    return !error;
  } catch {
    return false;
  }
}

/**
 * Aplica a correção.
 *
 * Ordem: **perfil primeiro, e-mail depois.** O perfil é a operação sem
 * desfecho parcial — fazê-la antes garante que, se o e-mail falhar, o que já
 * valeu é o que o resultado informa, e não o contrário. Era assim no `UI-11`
 * com o nome, e continua sendo, só que agora o primeiro passo é a rota.
 */
export async function atualizarPerfil(
  atual: DadosDoPerfil,
  formulario: DadosDoPerfil,
): Promise<ResultadoDePerfil> {
  const alteracao = calcularAlteracao(atual, formulario);
  if (nadaAFazer(alteracao)) return { tipo: "nada-a-fazer" };

  // Valida TUDO antes de escrever QUALQUER coisa. Metade de um formulário de
  // perfil aplicada é pior que nenhuma: a pessoa não saberia o estado.
  if (alteracao.nome !== undefined) {
    const valido = validarNome(alteracao.nome);
    if (!valido.ok) return { tipo: "invalido", mensagem: valido.motivo };
  }
  if (formulario.idade.trim() !== atual.idade.trim()) {
    const lida = lerIdade(formulario.idade);
    if (!lida.ok) return { tipo: "invalido", mensagem: lida.motivo };
  }
  if (alteracao.email !== undefined) {
    const valido = validarEmail(alteracao.email);
    if (!valido.ok) return { tipo: "invalido", mensagem: valido.motivo };
  }

  let perfilGravado = false;
  let residuoLimpo = false;

  const campos: { nome?: string; idade?: number | null } = {};
  if (alteracao.nome !== undefined) campos.nome = alteracao.nome;
  if (alteracao.idade !== undefined) campos.idade = alteracao.idade;

  if (Object.keys(campos).length > 0) {
    try {
      await requisitarJson<PerfilDoServidor>(CAMINHO, {
        method: "PATCH",
        body: JSON.stringify(campos),
      });
      perfilGravado = true;
    } catch (erro) {
      // Não tenta o e-mail: o perfil é a parte que o titular pediu primeiro, e
      // disparar confirmação de troca de credencial depois de falhar a
      // correção simples deixaria a pessoa com um e-mail no caminho e nenhum
      // dado corrigido.
      return {
        tipo: "erro",
        mensagem: erro instanceof Error ? erro.message : "Não foi possível salvar o perfil.",
        perfilGravado: false,
        residuoLimpo: false,
      };
    }

    // Só depois de a escrita autoritativa ter sucedido. Falha aqui não é falha
    // da correção — ver o cabeçalho.
    residuoLimpo = await limparResiduoDoMetadado();
  }

  if (alteracao.email === undefined) return { tipo: "salvo", perfilGravado, residuoLimpo };

  const supabase = obterSupabase();
  if (!supabase) {
    return { tipo: "erro", mensagem: SEM_CONFIGURACAO, perfilGravado, residuoLimpo };
  }

  const { data, error } = await supabase.auth.updateUser({ email: alteracao.email });
  if (error) {
    // O perfil pode já ter sido gravado. O resultado diz isso em vez de deixar
    // a tela anunciar que nada foi salvo.
    return {
      tipo: "erro",
      mensagem: traduzirErroDeAuth(error),
      perfilGravado,
      residuoLimpo,
    };
  }

  if (emailJaVale(data?.user, alteracao.email)) {
    return { tipo: "salvo", perfilGravado, residuoLimpo };
  }
  return {
    tipo: "email-pendente",
    emailPendente: alteracao.email,
    perfilGravado,
    residuoLimpo,
  };
}

/**
 * A frase que a tela mostra para cada desfecho.
 *
 * Separada do componente para poder ser testada: a diferença entre "salvo" e
 * "e-mail pendente" é exatamente o que não pode ser dito errado, e texto
 * dentro de JSX é mais caro de prender que função pura. ✏️ **19/10:** a frase
 * aqui dizia *"não tem teste neste projeto"*, e isso caiu com o `UI-17`
 * (`src/montagem.test.ts`). A separação continua certa pelo motivo acima — o
 * que mudou é que agora existe o segundo nível, não que este deixou de valer.
 *
 * **`residuoLimpo` não aparece no texto, e é decisão e não esquecimento.** O
 * titular pediu correção de nome e idade; a correção aconteceu. A limpeza de
 * uma cópia interna que nenhuma tela lê não é informação útil para ele, e
 * anunciá-la como pendência faria uma operação bem-sucedida parecer parcial. O
 * campo existe no resultado para quem depura e para que o código não possa
 * confundir as duas coisas.
 */
export function descreverResultado(resultado: ResultadoDePerfil, emailAtual: string): string {
  switch (resultado.tipo) {
    case "nada-a-fazer":
      return "Nada a salvar — os dados já estão assim.";
    case "salvo":
      return "Dados atualizados.";
    case "email-pendente": {
      const inicio = resultado.perfilGravado ? "Nome e idade atualizados. " : "";
      return (
        `${inicio}Enviamos um link de confirmação para ${resultado.emailPendente}. ` +
        `Seu e-mail de acesso continua sendo ${emailAtual} até a confirmação — e pode ` +
        `ser pedida confirmação também no endereço atual.`
      );
    }
    case "invalido":
      return resultado.mensagem;
    case "erro":
      return resultado.perfilGravado
        ? `Nome e idade foram atualizados, mas o e-mail não: ${resultado.mensagem}`
        : resultado.mensagem;
  }
}
