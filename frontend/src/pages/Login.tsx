import { Eye, EyeOff } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router";

import { AuthLayout } from "../components/AuthLayout";
import { BOTAO_PRIMARIO_CLS, INPUT_CLS, LABEL_CLS } from "../lib/ui";

export function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [mostrarSenha, setMostrarSenha] = useState(false);

  // Autenticação real (Supabase Auth) é o AUTH-02. Hoje só navega.
  function entrar() {
    navigate("/dashboard");
  }

  return (
    <AuthLayout subtitulo="Seu guia para um sono de qualidade">
      <div>
        <h2 className="text-lg font-semibold text-foreground">Bem-vindo de volta</h2>
        <p className="text-sm text-muted-foreground mt-0.5">Entre na sua conta</p>
      </div>

      <div className="space-y-4">
        <div>
          <label className={LABEL_CLS} htmlFor="email">E-mail</label>
          <input
            id="email"
            type="email"
            autoComplete="email"
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
          <button className="text-xs text-primary hover:text-accent transition mt-1.5 block ml-auto">
            Esqueci minha senha
          </button>
        </div>
      </div>

      <button onClick={entrar} className={BOTAO_PRIMARIO_CLS}>
        Entrar
      </button>

      <p className="text-center text-sm text-muted-foreground">
        Não tem uma conta?{" "}
        <Link to="/cadastro" className="text-primary hover:text-accent transition font-semibold">
          Cadastre-se
        </Link>
      </p>
    </AuthLayout>
  );
}
