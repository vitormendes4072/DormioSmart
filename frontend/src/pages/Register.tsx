import { CheckCircle2, Eye, EyeOff, Loader2, MailCheck } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router";

import { AuthLayout } from "../components/AuthLayout";
import { MINIMO_DA_SENHA, cadastrar, reenviarConfirmacao } from "../lib/autenticacao";
import { BOTAO_PRIMARIO_CLS, INPUT_CLS, LABEL_CLS } from "../lib/ui";

export function Register() {
  const navigate = useNavigate();
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [mostrarSenha, setMostrarSenha] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [aguardandoConfirmacao, setAguardandoConfirmacao] = useState(false);

  async function aoEnviar(evento: React.FormEvent) {
    evento.preventDefault();
    if (enviando) return;

    setErro(null);
    setEnviando(true);
    const resultado = await cadastrar(nome, email, senha);
    setEnviando(false);

    if (!resultado.ok) {
      setErro(resultado.mensagem);
      return;
    }

    if (resultado.precisaConfirmarEmail) {
      setAguardandoConfirmacao(true);
      return;
    }
    // Sem confirmacao de e-mail no projeto, a sessao ja vem no cadastro.
    navigate("/dashboard");
  }

  if (aguardandoConfirmacao) {
    return <ConfiraSeuEmail email={email} />;
  }

  return (
    <AuthLayout subtitulo="Comece a acompanhar seu repouso">
      <div>
        <h2 className="text-lg font-semibold text-foreground">Criar conta</h2>
        <p className="text-sm text-muted-foreground mt-0.5">Preencha seus dados abaixo</p>
      </div>

      <form className="space-y-4" onSubmit={aoEnviar} noValidate>
        <div>
          <label className={LABEL_CLS} htmlFor="nome">Nome completo</label>
          <input
            id="nome"
            type="text"
            autoComplete="name"
            required
            value={nome}
            onChange={(e) => setNome(e.target.value)}
            placeholder="Seu nome"
            className={INPUT_CLS}
          />
        </div>

        <div>
          <label className={LABEL_CLS} htmlFor="email-cadastro">E-mail</label>
          <input
            id="email-cadastro"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="voce@email.com"
            className={INPUT_CLS}
          />
        </div>

        <div>
          <label className={LABEL_CLS} htmlFor="senha-cadastro">Senha</label>
          <div className="relative">
            <input
              id="senha-cadastro"
              type={mostrarSenha ? "text" : "password"}
              autoComplete="new-password"
              required
              minLength={MINIMO_DA_SENHA}
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
              placeholder={`Mínimo ${MINIMO_DA_SENHA} caracteres`}
              className={INPUT_CLS + " pr-10"}
            />
            <button
              type="button"
              aria-label={mostrarSenha ? "Ocultar senha" : "Mostrar senha"}
              onClick={() => setMostrarSenha(!mostrarSenha)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition"
            >
              {mostrarSenha ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {erro ? (
          <p role="alert" className="text-sm text-destructive">
            {erro}
          </p>
        ) : null}

        <button type="submit" disabled={enviando} className={BOTAO_PRIMARIO_CLS + " disabled:opacity-70"}>
          {enviando ? (
            <span className="inline-flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              Criando conta...
            </span>
          ) : (
            "Criar conta"
          )}
        </button>
      </form>

      <p className="text-center text-sm text-muted-foreground">
        Já tem uma conta?{" "}
        <Link to="/login" className="text-primary hover:text-accent transition font-semibold">
          Entrar
        </Link>
      </p>
    </AuthLayout>
  );
}

/**
 * Tela pos-cadastro.
 *
 * Aparece igual para e-mail novo e para e-mail que ja tem conta. Diferenciar
 * os dois casos permitiria descobrir quem esta cadastrado — quem ja tem conta
 * recebe um e-mail avisando disso, que e o caminho seguro.
 */
function ConfiraSeuEmail({ email }: { email: string }) {
  const [reenviando, setReenviando] = useState(false);
  const [reenviado, setReenviado] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function reenviar() {
    setReenviando(true);
    setErro(null);
    const resultado = await reenviarConfirmacao(email);
    setReenviando(false);
    if (resultado.ok) setReenviado(true);
    else setErro(resultado.mensagem);
  }

  return (
    <AuthLayout subtitulo="Falta um passo">
      <div className="text-center space-y-3">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-primary/15">
          <MailCheck className="w-6 h-6 text-primary" />
        </div>
        <div>
          <h2 className="text-lg font-semibold text-foreground">Confirme seu e-mail</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Enviamos um link de confirmação para{" "}
            <strong className="text-foreground break-all">{email}</strong>. Abra o link para
            ativar sua conta.
          </p>
        </div>
        <p className="text-xs text-muted-foreground">
          Não chegou? Verifique a caixa de spam — o e-mail pode levar alguns minutos.
        </p>
      </div>

      {erro ? (
        <p role="alert" className="text-sm text-destructive text-center">
          {erro}
        </p>
      ) : null}

      {reenviado ? (
        <p className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
          <CheckCircle2 className="w-4 h-4 text-primary" />
          Reenviado.
        </p>
      ) : (
        <button
          onClick={reenviar}
          disabled={reenviando}
          className="w-full py-3 rounded-xl text-sm font-semibold bg-secondary text-foreground hover:bg-secondary/70 transition disabled:opacity-70"
        >
          {reenviando ? "Reenviando..." : "Reenviar e-mail de confirmação"}
        </button>
      )}

      <p className="text-center text-sm text-muted-foreground">
        <Link to="/login" className="text-primary hover:text-accent transition font-semibold">
          Voltar para o login
        </Link>
      </p>
    </AuthLayout>
  );
}
