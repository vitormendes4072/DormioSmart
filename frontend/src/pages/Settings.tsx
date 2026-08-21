import {
  ChevronRight,
  Cpu,
  Download,
  Loader2,
  Lock,
  Palette,
  Shield,
  User,
} from "lucide-react";
import { useState } from "react";

import { MeusDispositivos } from "../components/MeusDispositivos";
import { SeletorDeTema } from "../components/SeletorDeTema";
import { buscarHistorico } from "../lib/api";
import { baixarCsv } from "../lib/exportar";

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
      <SecaoPerfil />
      <SecaoDispositivos />
      <SecaoDados />
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

const AVISO_SESSAO = "Disponível após a autenticação de usuário entrar no ar.";

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

function SecaoPerfil() {
  const rotulo = "text-xs font-medium text-muted-foreground mb-1.5 block uppercase tracking-wider";
  const campo =
    "w-full px-3.5 py-2.5 bg-secondary text-muted-foreground border border-border rounded-xl text-sm " +
    "disabled:opacity-60 disabled:cursor-not-allowed";

  return (
    <Secao titulo="Perfil" icone={User} aviso={AVISO_SESSAO}>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className={rotulo} htmlFor="perfil-nome">Nome</label>
          <input id="perfil-nome" type="text" placeholder="—" className={campo} disabled />
        </div>
        <div>
          <label className={rotulo} htmlFor="perfil-idade">Idade</label>
          <input id="perfil-idade" type="number" placeholder="—" className={campo} disabled />
        </div>
      </div>
      <ItemDeAcao rotulo="Alterar senha" icone={Lock} desabilitado />
    </Secao>
  );
}

function SecaoDispositivos() {
  return (
    <Secao
      titulo="Meus dispositivos"
      icone={Cpu}
      aviso="Cada dispositivo pertence a esta conta e envia leituras com um token próprio. O token aparece uma única vez, no pareamento."
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
      const leituras = await buscarHistorico();
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

      <ItemDeAcao rotulo="Política de privacidade" desabilitado nota="em elaboração" />
      <ItemDeAcao rotulo="Excluir conta" desabilitado destrutivo />
    </Secao>
  );
}

function ItemDeAcao({
  rotulo,
  icone: Icone,
  desabilitado,
  destrutivo,
  nota,
}: {
  rotulo: string;
  icone?: typeof User;
  desabilitado?: boolean;
  destrutivo?: boolean;
  nota?: string;
}) {
  return (
    <button
      disabled={desabilitado}
      className={`w-full flex items-center justify-between gap-3 px-1 py-3.5 mt-1 border-t border-border text-left transition
        ${desabilitado ? "opacity-50 cursor-not-allowed" : "hover:bg-secondary"}`}
    >
      <span
        className={`flex items-center gap-2.5 text-sm ${destrutivo ? "text-destructive" : "text-foreground"}`}
      >
        {Icone ? <Icone className="w-4 h-4" /> : null}
        {rotulo}
        {nota ? <span className="text-xs text-muted-foreground">({nota})</span> : null}
      </span>
      <ChevronRight className="w-4 h-4 text-muted-foreground flex-shrink-0" />
    </button>
  );
}
