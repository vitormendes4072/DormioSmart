import { CheckCircle2, Eye, EyeOff, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router";

import { AuthLayout } from "../components/AuthLayout";
import { MINIMO_DA_SENHA, traduzirErroDeAuth } from "../lib/autenticacao";
import { ehRetornoDeRecuperacao } from "../lib/rotas";
import { obterSupabase } from "../lib/supabase";
import { BOTAO_PRIMARIO_CLS, INPUT_CLS, LABEL_CLS } from "../lib/ui";

/**
 * Definir nova senha (AUTH-04).
 *
 * Destino do link enviado por "esqueci minha senha". O supabase-js consome os
 * tokens da URL ao carregar (`detectSessionInUrl`) e cria uma sessao temporaria
 * de recuperacao; e ela que autoriza o `updateUser`.
 *
 * A pagina fica fora dos guardas de rota: quem chega aqui pode nao ter sessao
 * ainda no instante do primeiro render, e ser redirecionado para o login faria
 * o link do e-mail parecer quebrado.
 */
export function NovaSenha() {
  const navigate = useNavigate();
  const [senha, setSenha] = useState("");
  const [mostrarSenha, setMostrarSenha] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [pronto, setPronto] = useState(false);
  const [linkValido, setLinkValido] = useState<boolean | null>(null);

  useEffect(() => {
    const supabase = obterSupabase();
    if (!supabase) {
      setLinkValido(false);
      return;
    }

    const veioDeEmail = ehRetornoDeRecuperacao(window.location);

    // A sessao de recuperacao pode chegar depois do primeiro render — o
    // supabase-js ainda esta processando a URL. Por isso escutamos o evento
    // em vez de decidir na hora.
    const { data: assinatura } = supabase.auth.onAuthStateChange((_evento, sessao) => {
      if (sessao) setLinkValido(true);
    });

    void supabase.auth.getSession().then(({ data }) => {
      setLinkValido(data.session !== null || veioDeEmail);
    });

    return () => assinatura.subscription.unsubscribe();
  }, []);

  async function aoEnviar(evento: React.FormEvent) {
    evento.preventDefault();
    if (enviando) return;

    if (senha.length < MINIMO_DA_SENHA) {
      setErro(`A senha precisa ter pelo menos ${MINIMO_DA_SENHA} caracteres.`);
      return;
    }

    setErro(null);
    setEnviando(true);

    const supabase = obterSupabase();
    const { error } = supabase
      ? await supabase.auth.updateUser({ password: senha })
      : { error: null };

    setEnviando(false);

    if (error) {
      setErro(traduzirErroDeAuth(error));
      return;
    }
    setPronto(true);
  }

  if (pronto) {
    return (
      <AuthLayout subtitulo="Tudo certo">
        <div className="text-center space-y-3">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-primary/15">
            <CheckCircle2 className="w-6 h-6 text-primary" />
          </div>
          <h2 className="text-lg font-semibold text-foreground">Senha alterada</h2>
          <p className="text-sm text-muted-foreground">
            Você já pode usar a nova senha para entrar.
          </p>
        </div>
        <button onClick={() => navigate("/dashboard")} className={BOTAO_PRIMARIO_CLS}>
          Ir para o início
        </button>
      </AuthLayout>
    );
  }

  if (linkValido === false) {
    return (
      <AuthLayout subtitulo="Link inválido">
        <div className="text-center space-y-2">
          <h2 className="text-lg font-semibold text-foreground">
            Este link não é mais válido
          </h2>
          <p className="text-sm text-muted-foreground">
            Links de recuperação expiram e só podem ser usados uma vez. Peça um novo na
            tela de login.
          </p>
        </div>
        <Link to="/login" className={BOTAO_PRIMARIO_CLS + " block text-center"}>
          Voltar para o login
        </Link>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout subtitulo="Defina uma nova senha">
      <div>
        <h2 className="text-lg font-semibold text-foreground">Nova senha</h2>
        <p className="text-sm text-muted-foreground mt-0.5">
          Escolha uma senha com pelo menos {MINIMO_DA_SENHA} caracteres.
        </p>
      </div>

      <form className="space-y-4" onSubmit={aoEnviar} noValidate>
        <div>
          <label className={LABEL_CLS} htmlFor="nova-senha">Nova senha</label>
          <div className="relative">
            <input
              id="nova-senha"
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
              Salvando...
            </span>
          ) : (
            "Salvar nova senha"
          )}
        </button>
      </form>
    </AuthLayout>
  );
}
