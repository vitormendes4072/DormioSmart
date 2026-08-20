import { Eye, EyeOff, Loader2 } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router";

import { AuthLayout } from "../components/AuthLayout";
import { entrar, recuperarSenha } from "../lib/autenticacao";
import { BOTAO_PRIMARIO_CLS, INPUT_CLS, LABEL_CLS } from "../lib/ui";

export function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [mostrarSenha, setMostrarSenha] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  async function aoEnviar(evento: React.FormEvent) {
    evento.preventDefault();
    if (enviando) return;

    setErro(null);
    setAviso(null);
    setEnviando(true);

    const resultado = await entrar(email, senha);
    setEnviando(false);

    if (resultado.ok) {
      navigate("/dashboard");
      return;
    }
    setErro(resultado.mensagem);
  }

  async function aoRecuperarSenha() {
    if (!email.trim()) {
      setErro("Informe seu e-mail para receber o link de recuperação.");
      return;
    }
    setErro(null);
    const resultado = await recuperarSenha(email);
    // Resposta identica com ou sem conta: dizer "e-mail nao encontrado"
    // permitiria descobrir quem tem cadastro.
    setAviso(
      resultado.ok
        ? "Se houver uma conta com este e-mail, o link de recuperação foi enviado."
        : resultado.mensagem,
    );
  }

  return (
    <AuthLayout subtitulo="Seu guia para um sono de qualidade">
      <div>
        <h2 className="text-lg font-semibold text-foreground">Bem-vindo de volta</h2>
        <p className="text-sm text-muted-foreground mt-0.5">Entre na sua conta</p>
      </div>

      <form className="space-y-4" onSubmit={aoEnviar} noValidate>
        <div>
          <label className={LABEL_CLS} htmlFor="email">E-mail</label>
          <input
            id="email"
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
          <label className={LABEL_CLS} htmlFor="senha">Senha</label>
          <div className="relative">
            <input
              id="senha"
              type={mostrarSenha ? "text" : "password"}
              autoComplete="current-password"
              required
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
              placeholder="••••••••"
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
          <button
            type="button"
            onClick={aoRecuperarSenha}
            className="text-xs text-primary hover:text-accent transition mt-1.5 block ml-auto"
          >
            Esqueci minha senha
          </button>
        </div>

        {erro ? (
          <p role="alert" className="text-sm text-destructive">
            {erro}
          </p>
        ) : null}
        {aviso ? <p className="text-sm text-muted-foreground">{aviso}</p> : null}

        <button type="submit" disabled={enviando} className={BOTAO_PRIMARIO_CLS + " disabled:opacity-70"}>
          {enviando ? (
            <span className="inline-flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              Entrando...
            </span>
          ) : (
            "Entrar"
          )}
        </button>
      </form>

      <p className="text-center text-sm text-muted-foreground">
        Não tem uma conta?{" "}
        <Link to="/cadastro" className="text-primary hover:text-accent transition font-semibold">
          Cadastre-se
        </Link>
      </p>
    </AuthLayout>
  );
}
