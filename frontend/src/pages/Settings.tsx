import {
  Cpu,
  Download,
  Loader2,
  LogOut,
  Palette,
  Shield,
  Trash2,
  User,
} from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router";

import { ExcluirConta } from "../components/ExcluirConta";
import { MeusDispositivos } from "../components/MeusDispositivos";
import { SeletorDeTema } from "../components/SeletorDeTema";
import { LIMITE_DO_PAINEL, buscarHistorico } from "../lib/api";
import { baixarCsv } from "../lib/exportar";
import { useAuth } from "../contexts/AuthContext";

/**
 * Configuracoes.
 *
 * Regra desta tela: nenhum controle que nao faca nada. O prototipo tinha
 * "Metas de Sono" (pressupoe medir duracao de sono, que o dispositivo nao
 * mede) e quatro interruptores de notificacao sem nada por tras — os dois
 * blocos foram removidos, nao desabilitados: nao ha plano de implementa-los.
 *
 * O que depende de sessao aparece DESABILITADO com o motivo dito na tela. Um
 * controle desabilitado e explicado nao engana ninguem; um interruptor que
 * acende e nao faz nada, sim.
 */
export function Settings() {
  return (
    <div className="max-w-2xl space-y-5">
      <div className="mb-8">
        <h1 className="text-xl sm:text-2xl font-semibold text-foreground">Configurações</h1>
        <p className="text-sm text-muted-foreground mt-0.5">Conta, dispositivos e seus dados</p>
      </div>

      <SecaoAparencia />
      <SecaoConta />
      <SecaoDispositivos />
      <SecaoDados />
      <SecaoSair />
      <SecaoExclusao />
    </div>
  );
}

function Secao({
  titulo,
  icone: Icone,
  aviso,
  children,
}: {
  titulo: string;
  icone: typeof User;
  aviso?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="bg-card border border-border rounded-2xl p-4 sm:p-6">
      <div className="flex items-center gap-2 mb-1">
        <Icone className="w-4 h-4 text-primary" />
        <h2 className="text-sm font-semibold text-foreground">{titulo}</h2>
      </div>
      {aviso ? <p className="text-xs text-muted-foreground mb-5 mt-1">{aviso}</p> : <div className="mb-5" />}
      {children}
    </section>
  );
}

function SecaoAparencia() {
  return (
    <Secao
      titulo="Aparência"
      icone={Palette}
      aviso="O tema claro segue a identidade da Dormio Labs; o escuro existe porque o app é consultado de madrugada."
    >
      <SeletorDeTema />
    </Secao>
  );
}

/**
 * A conta em que a pessoa está.
 *
 * Antes esta seção mostrava dois campos vazios, desabilitados, sob o aviso
 * "Disponível após a autenticação de usuário entrar no ar" — texto que ficou
 * obsoleto quando o AUTH-02/03 subiu, e passou a afirmar que uma coisa pronta
 * não existia.
 *
 * Campo vazio desabilitado não é funcionalidade futura visível: é promessa não
 * cumprida ocupando espaço. Ficou o que é verdade — quem está logado.
 */
function SecaoConta() {
  const { usuario } = useAuth();
  const nome = (usuario?.user_metadata?.nome as string | undefined)?.trim();

  return (
    <Secao titulo="Conta" icone={User}>
      <dl className="space-y-3 text-sm">
        {nome && (
          <div className="flex justify-between gap-4">
            <dt className="text-muted-foreground">Nome</dt>
            <dd className="text-foreground font-medium truncate">{nome}</dd>
          </div>
        )}
        <div className="flex justify-between gap-4">
          <dt className="text-muted-foreground">E-mail</dt>
          <dd className="text-foreground font-medium truncate">{usuario?.email ?? "—"}</dd>
        </div>
      </dl>
    </Secao>
  );
}

function SecaoDispositivos() {
  return (
    <Secao
      titulo="Meus dispositivos"
      icone={Cpu}
      aviso="Cada aparelho que envia leituras aparece aqui. Você pode renomear ou remover a qualquer momento."
    >
      <MeusDispositivos />
    </Secao>
  );
}

function SecaoDados() {
  const [exportando, setExportando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [vazio, setVazio] = useState(false);

  async function exportar() {
    setExportando(true);
    setErro(null);
    setVazio(false);
    try {
      // Sem `limite` explicito o backend devolve 20 linhas (DASH-13), e a
      // exportacao que a secao promete como "seus dados" entregava dez
      // minutos de captacao. Numa tela cuja justificativa e o direito de
      // portabilidade da LGPD, isso nao e um recorte: e um arquivo errado.
      const leituras = await buscarHistorico({ limite: LIMITE_DO_PAINEL });
      if (leituras.length === 0) {
        // Baixar um CSV so com cabecalho pareceria sucesso e nao seria util.
        setVazio(true);
        return;
      }
      baixarCsv(leituras);
    } catch {
      setErro("Não foi possível carregar suas leituras para exportar.");
    } finally {
      setExportando(false);
    }
  }

  return (
    <Secao
      titulo="Seus dados"
      icone={Shield}
      aviso="Exporta suas leituras em CSV — instante, magnitude, intensidade, temperatura do chip e estado."
    >
      <button
        onClick={exportar}
        disabled={exportando}
        className="w-full flex items-center justify-between px-4 py-3 rounded-xl bg-secondary hover:bg-secondary/70 transition text-left disabled:opacity-60 disabled:cursor-wait"
      >
        <span className="flex items-center gap-2.5 text-sm text-foreground">
          {exportando ? (
            <Loader2 className="w-4 h-4 animate-spin text-primary" />
          ) : (
            <Download className="w-4 h-4 text-primary" />
          )}
          {exportando ? "Preparando arquivo..." : "Exportar meus dados (CSV)"}
        </span>
      </button>

      {vazio ? (
        <p className="text-xs text-muted-foreground mt-3">
          Não há leituras para exportar — o dispositivo ainda não enviou dados.
        </p>
      ) : null}
      {erro ? <p className="text-xs text-destructive mt-3">{erro}</p> : null}

      {/* "Política de privacidade (em elaboração)" ainda não volta: o rascunho
          existe em docs/POLITICA-DE-PRIVACIDADE.md, mas não há página que o
          sirva (LGPD-01). Anunciar um link que não abre seria repetir o defeito
          que tirou o item daqui. */}
    </Secao>
  );
}

/**
 * Eliminação da conta (UI-10 / SEC-07 / LGPD art. 18, V).
 *
 * Seção própria, e por último, de propósito. Ficar dentro de "Seus dados" a
 * colocaria ao lado da exportação — duas ações de peso oposto no mesmo bloco,
 * com o botão destrutivo a um deslize do botão que a pessoa realmente queria.
 * Separada e no fim, ela é encontrada por quem a procura e não é esbarrada por
 * quem não.
 *
 * O aviso da seção menciona a exportação porque esta é a última tela em que ela
 * ainda é possível.
 */
function SecaoExclusao() {
  return (
    <Secao
      titulo="Excluir conta"
      icone={Trash2}
      aviso="Encerra sua conta e apaga seus dados deste serviço. Se quiser guardar seu histórico, exporte o CSV acima antes."
    >
      <ExcluirConta />
    </Secao>
  );
}

/**
 * Sair da conta.
 *
 * Veio da barra de navegação do celular, onde ocupava um quarto do espaço —
 * um slot permanente para uma ação usada uma vez por sessão, ao lado de três
 * lugares visitados o tempo todo. Barra de navegação ensina que cada item é
 * um destino; um botão destrutivo no meio quebra essa expectativa.
 */
function SecaoSair() {
  const navigate = useNavigate();
  const { sair } = useAuth();
  const [saindo, setSaindo] = useState(false);

  return (
    <button
      onClick={async () => {
        setSaindo(true);
        await sair();
        navigate("/login");
      }}
      disabled={saindo}
      className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl border border-border text-sm font-medium text-muted-foreground hover:text-destructive hover:border-destructive/40 transition disabled:opacity-60"
    >
      <LogOut className="w-4 h-4" />
      {saindo ? "Saindo..." : "Sair da conta"}
    </button>
  );
}

