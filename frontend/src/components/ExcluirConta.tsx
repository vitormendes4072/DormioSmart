/**
 * Exclusão de conta (UI-10 / SEC-07 / LGPD art. 18, V).
 *
 * A rota `DELETE /api/me` existe desde o SEC-07, e só. Sem caminho pela
 * interface, o titular dependia de alguém chamar a API por ele — o que não é
 * exercer um direito, é pedir um favor.
 *
 * ── TRÊS DECISÕES DE DESENHO, E O QUE CADA UMA EVITA ────────────────────
 *
 * **1. Dois passos, e o segundo exige digitar.** O botão não apaga: abre. O que
 * apaga fica atrás de um campo onde a frase exata tem de ser escrita à mão. Não
 * é cerimônia — é que nenhum dos modos reais de disparo acidental (clique
 * duplo, retry automático, `fetch` repetido por hot reload, botão tocado no
 * bolso) digita uma frase. Mesma barreira que o backend exige; aqui ela existe
 * para ser VISTA, não só conferida.
 *
 * **2. A lista do que sai vem ANTES do campo.** Quem lê a tela na ordem em que
 * ela é apresentada encontra a consequência antes do gatilho. A alternativa —
 * botão primeiro, aviso depois — é a que produz arrependimento.
 *
 * **3. O desfecho parcial tem tela própria.** É a decisão que o item existe
 * para acertar. A rota pode responder **200 com remoção incompleta**: os dados
 * de sono saem, o cadastro de acesso (e-mail) fica, porque o privilégio de
 * `DELETE` em `auth.users` pertence ao Supabase. Mostrar "conta excluída" nesse
 * caso seria mentir para alguém que acabou de exercer um direito, sobre dado
 * pessoal que ainda existe. Então há três desfechos na tela, não dois.
 *
 * ── O QUE DELIBERADAMENTE NÃO TEM ───────────────────────────────────────
 *
 * Não há contagem regressiva, nem "tem certeza?" em cima de "tem certeza?".
 * Fricção empilhada treina a pessoa a clicar em tudo sem ler, que é o oposto do
 * objetivo. Uma barreira que exige atenção real vale mais que três que não.
 */
import { AlertTriangle, CheckCircle2, Loader2, Trash2 } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router";

import { useAuth } from "../contexts/AuthContext";
import { ErroApi } from "../lib/api";
import {
  FRASE_DE_CONFIRMACAO,
  type ResultadoDeExclusao,
  confirmacaoValida,
  descreverRecibo,
  excluirMinhaConta,
} from "../lib/conta";

type Estado = "fechado" | "confirmando" | "apagando" | "concluido";

export function ExcluirConta() {
  const [estado, setEstado] = useState<Estado>("fechado");
  const [texto, setTexto] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [resultado, setResultado] = useState<ResultadoDeExclusao | null>(null);

  async function confirmar() {
    setErro(null);
    setEstado("apagando");
    try {
      setResultado(await excluirMinhaConta(texto));
      setEstado("concluido");
    } catch (e) {
      // 401 já leva ao login sozinho (o callback de sessão expirada em
      // `api.ts`). Os demais viram texto na tela: o que não pode acontecer é a
      // pessoa achar que apagou quando não apagou.
      setErro(
        e instanceof ErroApi
          ? e.message
          : "Não foi possível concluir a exclusão. Nada foi apagado.",
      );
      setEstado("confirmando");
    }
  }

  if (estado === "concluido" && resultado) {
    return <Desfecho resultado={resultado} />;
  }

  if (estado === "fechado") {
    return (
      <div>
        <button
          onClick={() => {
            setEstado("confirmando");
            setTexto("");
            setErro(null);
          }}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl border border-destructive/30 text-sm font-medium text-destructive hover:bg-destructive/5 transition"
        >
          <Trash2 className="w-4 h-4" />
          Excluir minha conta
        </button>
        <p className="text-xs text-muted-foreground mt-3">
          Remove permanentemente seus dados deste serviço. Você poderá revisar o
          que será apagado antes de confirmar.
        </p>
      </div>
    );
  }

  const podeConfirmar = confirmacaoValida(texto) && estado !== "apagando";

  return (
    <div className="rounded-xl border border-destructive/30 bg-destructive/5 p-4 space-y-4">
      <div className="flex items-start gap-2.5">
        <AlertTriangle className="w-4 h-4 text-destructive shrink-0 mt-0.5" />
        <div className="space-y-2">
          <p className="text-sm font-semibold text-foreground">
            Isto é irreversível. Não há como desfazer.
          </p>
          <p className="text-xs text-muted-foreground">Serão apagados definitivamente:</p>
          <ul className="text-xs text-muted-foreground space-y-1 list-disc pl-4">
            <li>
              <strong className="text-foreground">Todas as suas leituras</strong> — cada
              época de movimento já captada, de todas as noites.
            </li>
            <li>
              <strong className="text-foreground">Todos os seus dispositivos</strong> — o
              pareamento é perdido; um aparelho em campo deixa de conseguir enviar.
            </li>
            <li>
              <strong className="text-foreground">Seu perfil</strong> — nome e
              preferências.
            </li>
          </ul>
          <p className="text-xs text-muted-foreground">
            Se quiser guardar seu histórico, <strong>exporte o CSV antes</strong> — depois
            de confirmar, não existe mais cópia deste lado.
          </p>
        </div>
      </div>

      <div>
        <label htmlFor="confirmacao-exclusao" className="block text-xs text-muted-foreground mb-1.5">
          Para confirmar, digite{" "}
          <code className="text-foreground font-semibold">{FRASE_DE_CONFIRMACAO}</code>
        </label>
        <input
          id="confirmacao-exclusao"
          type="text"
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          disabled={estado === "apagando"}
          autoComplete="off"
          // `off` de propósito: um gerenciador de senhas preenchendo a frase
          // transformaria a barreira num clique, que é exatamente o que ela
          // existe para impedir.
          spellCheck={false}
          placeholder={FRASE_DE_CONFIRMACAO}
          className="w-full px-3 py-2 rounded-lg bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:border-destructive/50 disabled:opacity-60"
        />
      </div>

      {erro ? <p className="text-xs text-destructive">{erro}</p> : null}

      <div className="flex gap-2">
        <button
          onClick={() => {
            setEstado("fechado");
            setTexto("");
            setErro(null);
          }}
          disabled={estado === "apagando"}
          className="flex-1 px-4 py-2.5 rounded-lg border border-border text-sm font-medium text-foreground hover:bg-secondary transition disabled:opacity-60"
        >
          Cancelar
        </button>
        <button
          onClick={confirmar}
          disabled={!podeConfirmar}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-destructive text-sm font-medium text-white hover:opacity-90 transition disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {estado === "apagando" ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
          {estado === "apagando" ? "Apagando..." : "Excluir definitivamente"}
        </button>
      </div>
    </div>
  );
}

/**
 * O que a pessoa vê depois. Dois desfechos possíveis, e eles NÃO se parecem.
 *
 * O parcial não é uma variação do sucesso com um asterisco: é um estado em que
 * dado pessoal do titular continua existindo, e a tela precisa dizer isso com
 * as mesmas letras com que diria qualquer outra coisa importante.
 */
function Desfecho({ resultado }: { resultado: ResultadoDeExclusao }) {
  const navigate = useNavigate();
  const { sair } = useAuth();
  const [saindo, setSaindo] = useState(false);
  const completa = resultado.tipo === "completa";

  async function encerrar() {
    setSaindo(true);
    // A sessão precisa cair de qualquer jeito: o JWT continua válido até
    // expirar, e deixar a pessoa navegando num app cujas linhas não existem
    // mais produziria telas vazias sem explicação.
    await sair();
    navigate("/login");
  }

  return (
    <div
      className={`rounded-xl border p-4 space-y-3 ${
        completa ? "border-border bg-secondary/40" : "border-destructive/40 bg-destructive/5"
      }`}
    >
      <div className="flex items-start gap-2.5">
        {completa ? (
          <CheckCircle2 className="w-4 h-4 text-primary shrink-0 mt-0.5" />
        ) : (
          <AlertTriangle className="w-4 h-4 text-destructive shrink-0 mt-0.5" />
        )}
        <div className="space-y-2">
          <p className="text-sm font-semibold text-foreground">
            {completa ? "Conta excluída." : "Exclusão concluída apenas em parte."}
          </p>
          <p className="text-xs text-muted-foreground">
            Foram apagados {descreverRecibo(resultado.recibo)}.
          </p>
          {resultado.tipo === "parcial" ? (
            <>
              <p className="text-xs text-foreground font-medium">{resultado.aviso}</p>
              <p className="text-xs text-muted-foreground">
                Isso acontece quando o serviço de autenticação não permite que a
                própria aplicação remova o cadastro — é uma limitação de
                privilégio do projeto, não uma falha da sua solicitação. Para
                completar a remoção do seu e-mail, procure o responsável pelo
                sistema.
              </p>
            </>
          ) : null}
        </div>
      </div>

      <button
        onClick={encerrar}
        disabled={saindo}
        className="w-full px-4 py-2.5 rounded-lg border border-border text-sm font-medium text-foreground hover:bg-secondary transition disabled:opacity-60"
      >
        {saindo ? "Saindo..." : "Encerrar sessão"}
      </button>
    </div>
  );
}
