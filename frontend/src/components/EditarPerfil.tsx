/**
 * Edição de perfil (UI-11 / LGPD art. 18, III).
 *
 * A lógica inteira está em `lib/perfil.ts`, com teste. Aqui ficam só o estado
 * do formulário e o texto — pela mesma razão pela qual o `UI-10` ficou assim:
 * neste projeto não há teste de componente (o `vitest` roda em ambiente `node`
 * e não há testing-library, ver `UI-17`), então tudo que puder ser decidido
 * fora do JSX é decidido fora do JSX.
 *
 * ── A ASSIMETRIA QUE A TELA TEM DE MOSTRAR ──────────────────────────────
 *
 * Nome e e-mail estão no mesmo formulário e **não** têm o mesmo desfecho: o
 * nome vale ao salvar, o e-mail depende de confirmação por link e o endereço
 * de acesso continua sendo o antigo até alguém clicar. A tela diz isso em
 * texto, e o campo de e-mail avisa **antes** de a pessoa salvar — avisar
 * depois faria o aviso parecer notícia ruim em vez de informação.
 */
import { Check, Loader2, Mail, Pencil } from "lucide-react";
import { useState } from "react";

import { useAuth } from "../contexts/AuthContext";
import {
  NOME_MAXIMO_DO_PERFIL,
  type ResultadoDePerfil,
  atualizarPerfil,
  calcularAlteracao,
  descreverResultado,
  emailDaSessao,
  nadaAFazer,
  nomeDaSessao,
} from "../lib/perfil";

const CAMPO_CLS =
  "w-full rounded-lg border border-border bg-input-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring";

export function EditarPerfil() {
  const { usuario } = useAuth();
  const atual = { nome: nomeDaSessao(usuario), email: emailDaSessao(usuario) };

  const [aberto, setAberto] = useState(false);
  const [nome, setNome] = useState(atual.nome);
  const [email, setEmail] = useState(atual.email);
  const [salvando, setSalvando] = useState(false);
  const [resultado, setResultado] = useState<ResultadoDePerfil | null>(null);

  function abrir() {
    // Recarrega da sessão ao abrir: entre dois usos a sessão pode ter mudado
    // (confirmação de e-mail concluída noutra aba, por exemplo), e o
    // formulário não pode partir de um valor velho — partiria oferecendo
    // "corrigir" de volta para o que a pessoa já trocou.
    setNome(atual.nome);
    setEmail(atual.email);
    setResultado(null);
    setAberto(true);
  }

  async function salvar() {
    setSalvando(true);
    try {
      setResultado(await atualizarPerfil(atual, { nome, email }));
    } finally {
      setSalvando(false);
    }
  }

  const alteracao = calcularAlteracao(atual, { nome, email });
  const semMudanca = nadaAFazer(alteracao);
  const trocandoEmail = alteracao.email !== undefined;

  if (!aberto) {
    return (
      <div>
        <dl className="space-y-3 text-sm">
          <div className="flex justify-between gap-4">
            <dt className="text-muted-foreground">Nome</dt>
            <dd className="text-foreground font-medium truncate">{atual.nome || "—"}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-muted-foreground">E-mail</dt>
            <dd className="text-foreground font-medium truncate">{atual.email || "—"}</dd>
          </div>
        </dl>
        {resultado && resultado.tipo !== "nada-a-fazer" ? (
          <p className="text-xs text-muted-foreground mt-3">
            {descreverResultado(resultado, atual.email)}
          </p>
        ) : null}
        <button
          onClick={abrir}
          className="mt-4 w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border border-border text-sm font-medium text-foreground hover:bg-muted/40 transition"
        >
          <Pencil className="w-4 h-4" />
          Editar dados
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="space-y-1.5">
        <label className="text-xs text-muted-foreground" htmlFor="perfil-nome">
          Nome
        </label>
        <input
          id="perfil-nome"
          type="text"
          value={nome}
          maxLength={NOME_MAXIMO_DO_PERFIL}
          onChange={(e) => setNome(e.target.value)}
          className={CAMPO_CLS}
          placeholder="Seu nome"
        />
      </div>

      <div className="space-y-1.5">
        <label className="text-xs text-muted-foreground" htmlFor="perfil-email">
          E-mail
        </label>
        <input
          id="perfil-email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className={CAMPO_CLS}
          placeholder="voce@exemplo.com"
        />
        {/* Antes de salvar, e não depois: o e-mail é credencial de acesso, e
            quem está digitando precisa saber que a troca não é imediata. */}
        {trocandoEmail ? (
          <p className="text-xs text-muted-foreground flex items-start gap-1.5">
            <Mail className="w-3.5 h-3.5 shrink-0 mt-0.5" />
            <span>
              Trocar o e-mail exige confirmação por link. Até você confirmar, seu acesso
              continua sendo <strong className="text-foreground">{atual.email}</strong>.
            </span>
          </p>
        ) : null}
      </div>

      {resultado ? (
        <p
          className={
            resultado.tipo === "invalido" || resultado.tipo === "erro"
              ? "text-xs text-destructive"
              : "text-xs text-muted-foreground"
          }
        >
          {descreverResultado(resultado, atual.email)}
        </p>
      ) : null}

      <div className="flex gap-2">
        <button
          onClick={salvar}
          disabled={salvando || semMudanca}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-primary text-sm font-medium text-primary-foreground hover:opacity-90 transition disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {salvando ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Check className="w-4 h-4" />
          )}
          Salvar
        </button>
        <button
          onClick={() => setAberto(false)}
          disabled={salvando}
          className="px-4 py-2.5 rounded-xl border border-border text-sm font-medium text-foreground hover:bg-muted/40 transition disabled:opacity-40"
        >
          Cancelar
        </button>
      </div>

      {/* O botão fica inerte sem mudança em vez de escondido: escondê-lo
          deixaria a pessoa procurando por que não há como salvar. */}
      {semMudanca ? (
        <p className="text-xs text-muted-foreground">Altere algum campo para poder salvar.</p>
      ) : null}
    </div>
  );
}
