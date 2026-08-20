import { Eye, EyeOff } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router";

import { AuthLayout } from "../components/AuthLayout";
import { BOTAO_PRIMARIO_CLS, INPUT_CLS, LABEL_CLS } from "../lib/ui";

export function Register() {
  const navigate = useNavigate();
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [mostrarSenha, setMostrarSenha] = useState(false);

  // Cadastro real + confirmação de e-mail é o AUTH-02. Hoje só navega.
  function criarConta() {
    navigate("/dashboard");
  }

  return (
    <AuthLayout subtitulo="Comece a acompanhar seu repouso">
      <div>
        <h2 className="text-lg font-semibold text-foreground">Criar conta</h2>
        <p className="text-sm text-muted-foreground mt-0.5">Preencha seus dados abaixo</p>
      </div>

      <div className="space-y-4">
        <div>
          <label className={LABEL_CLS} htmlFor="nome">Nome completo</label>
          <input
            id="nome"
            type="text"
            autoComplete="name"
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
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
              placeholder="Mínimo 8 caracteres"
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
      </div>

      <button onClick={criarConta} className={BOTAO_PRIMARIO_CLS}>
        Criar conta
      </button>

      <p className="text-center text-sm text-muted-foreground">
        Já tem uma conta?{" "}
        <Link to="/login" className="text-primary hover:text-accent transition font-semibold">
          Entrar
        </Link>
      </p>
    </AuthLayout>
  );
}
