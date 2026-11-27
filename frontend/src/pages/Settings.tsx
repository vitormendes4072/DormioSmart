import {
  BellRing,
  ChevronRight,
  Cpu,
  Download,
  Loader2,
  LogOut,
  Palette,
  Shield,
  Trash2,
  User,
} from "lucide-react";
import { useId, useState, type ReactNode } from "react";
import { Link, useLocation, useNavigate } from "react-router";

import { EtiquetaDeRegistro, SUPERFICIE_DO_CARTAO_DE_REGISTRO } from "../components/CartoesDeRegistro";
import { EditarPerfil } from "../components/EditarPerfil";
import { LembreteDeDormir } from "../components/LembreteDeDormir";
import { ExcluirConta } from "../components/ExcluirConta";
import { MeusDispositivos } from "../components/MeusDispositivos";
import { SeletorDeTema } from "../components/SeletorDeTema";
import { buscarHistoricoCompleto } from "../lib/api";
import { estaEmModoDemo } from "../lib/demo";
import { baixarCsv } from "../lib/exportar";
import { listarDispositivos } from "../lib/dispositivos";
import { noiteNativaDisponivel } from "../lib/noiteNativa";
import { salvarPreferenciaDoGuia } from "../lib/primeirosPassos";
import { LINHA_DE_CONFIGURACAO } from "../lib/ui";
import { useAuth } from "../contexts/AuthContext";

/**
 * Configuracoes.
 *
 * Regra desta tela: nenhum controle que nao faca nada. O prototipo tinha
 * "Metas de Sono" (pressupoe medir duracao de sono, que o dispositivo nao
 * mede) e quatro interruptores de notificacao sem nada por tras — os dois
 * blocos foram removidos, nao desabilitados. A notificacao que voltou, o
 * lembrete de dormir (APP-20), so aparece no app, onde de fato funciona.
 *
 * Os controles ilustrativos de sensibilidade e avisos da landing ficam fora.
 * Na demonstração, as ações da conta dão lugar ao convite para entrar.
 */
export function Settings() {
  const { search } = useLocation();
  const { sessao } = useAuth();
  return (
    <div className="max-w-2xl space-y-4">
      <header className="mb-5">
        <EtiquetaDeRegistro>Preferências</EtiquetaDeRegistro>
        <h1 className="mt-1 text-2xl font-extrabold tracking-tight text-foreground sm:text-[27px]">Configurações</h1>
        <p className="mt-1 text-xs text-muted-foreground">Conta, dispositivos e seus dados</p>
      </header>

      <SecaoAparencia />
      {estaEmModoDemo(search) ? <SecaoAcessoDemonstrativo /> : (
        <>
          <SecaoConta />
          <Link to="/dashboard#primeiros-passos"
            onClick={() => salvarPreferenciaDoGuia(sessao?.user.id, false)}
            className="inline-flex min-h-11 items-center rounded-lg border border-border bg-card px-3 text-sm font-semibold text-primary hover:bg-secondary focus-visible:outline-2 focus-visible:outline-ring">
            Primeiros passos
          </Link>
          {noiteNativaDisponivel() ? <SecaoLembrete /> : null}
          <SecaoDispositivos />
          <SecaoDados />
          <SecaoSair />
          <SecaoExclusao />
        </>
      )}
    </div>
  );
}

function Secao({
  titulo,
  icone: Icone,
  aviso,
  destrutiva = false,
  children,
}: {
  titulo: string;
  icone: typeof User;
  aviso?: string;
  destrutiva?: boolean;
  children: ReactNode;
}) {
  const id = useId();

  return (
    <section aria-labelledby={id}
      className={`${SUPERFICIE_DO_CARTAO_DE_REGISTRO} px-4 sm:px-5 ${destrutiva ? "ring-1 ring-destructive/20" : ""}`}>
      <header className="pb-3 pt-4">
        <div className="flex items-center gap-2">
          <Icone className={`size-4 shrink-0 ${destrutiva ? "text-destructive" : "text-primary"}`} aria-hidden />
          <h2 id={id} className="text-sm font-semibold text-foreground">{titulo}</h2>
        </div>
        {aviso && <p className="mt-2 text-xs leading-relaxed text-muted-foreground">{aviso}</p>}
      </header>
      <div className="border-t border-border">{children}</div>
    </section>
  );
}

function SecaoAcessoDemonstrativo() {
  const { sessao } = useAuth();

  return (
    <Secao
      titulo="Configurações da conta"
      icone={User}
      aviso="Entre na sua conta para editar o perfil, gerenciar dispositivos, exportar dados ou excluir a conta."
    >
      <Link
        to={sessao ? "/configuracoes" : "/login"}
        state={sessao ? undefined : { de: "/configuracoes" }}
        className={`${LINHA_DE_CONFIGURACAO} text-sm font-semibold text-primary hover:underline`}
      >
        {sessao ? "Abrir configurações da conta" : "Entrar"}
        <ChevronRight className="size-4 shrink-0" aria-hidden />
      </Link>
    </Secao>
  );
}

function SecaoLembrete() {
  return (
    <Secao
      titulo="Lembrete de dormir"
      icone={BellRing}
      aviso="Todo dia, no horário escolhido, o app lembra você de começar a registrar a noite. O horário fica só no celular."
    >
      <LembreteDeDormir />
    </Secao>
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
/**
 * Conta — exibição e correção (UI-11 / LGPD art. 18, III).
 *
 * A seção só exibia nome e e-mail, e a política de privacidade §6.3 teve de
 * declarar que não havia tela para corrigi-los. O `EditarPerfil` entra aqui, e
 * não em seção própria, porque corrigir é a continuação natural de ver — ao
 * contrário de excluir, que ganhou seção separada justamente para não ficar ao
 * alcance de um deslize.
 *
 * A leitura do nome saiu daqui para `lib/perfil.ts`: com a leitura em dois
 * lugares, a tela de exibição e a de edição podiam discordar sobre de onde vem
 * o nome.
 *
 * ✏️ **17/10, `PERFIL-01`:** a fonte passou a ser `public.profiles`, pela rota
 * `/api/me/perfil`, e a idade entrou como campo opcional com finalidade
 * declarada. O e-mail continua no serviço de autenticação, porque é
 * credencial e não perfil — ver `components/EditarPerfil.tsx`.
 */
function SecaoConta() {
  return (
    <Secao
      titulo="Conta"
      icone={User}
      aviso="Nome, idade e e-mail podem ser corrigidos ou retirados a qualquer momento (LGPD, art. 18, III e IV)."
    >
      <EditarPerfil />
    </Secao>
  );
}

function SecaoDispositivos() {
  return (
    <Secao
      titulo="Meus dispositivos"
      icone={Cpu}
      aviso="Cada aparelho que envia registros aparece aqui. Você pode renomear ou remover a qualquer momento."
    >
      <div className="py-3"><MeusDispositivos /></div>
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
      const leituras = await buscarHistoricoCompleto();
      if (leituras.length === 0) {
        // Baixar um CSV so com cabecalho pareceria sucesso e nao seria util.
        setVazio(true);
        return;
      }
      const dispositivos = await listarDispositivos().catch(() => []);
      baixarCsv(leituras, dispositivos);
    } catch {
      setErro("Não foi possível carregar seus registros para exportar.");
    } finally {
      setExportando(false);
    }
  }

  return (
    <Secao
      titulo="Seus dados"
      icone={Shield}
      aviso="Exporta seus registros em CSV — horário, valor do sensor, intensidade do movimento, temperatura, origem da temperatura e estado."
    >
      <button
        type="button"
        onClick={exportar}
        disabled={exportando}
        className={`${LINHA_DE_CONFIGURACAO} w-full text-left text-sm font-medium text-foreground hover:text-primary disabled:cursor-wait disabled:opacity-60`}
      >
        {exportando ? "Preparando arquivo..." : "Exportar meus dados (CSV)"}
        {exportando ? (
          <Loader2 className="size-4 shrink-0 animate-spin text-primary" aria-hidden />
        ) : (
          <Download className="size-4 shrink-0 text-primary" aria-hidden />
        )}
      </button>

      {vazio ? (
        <p className="text-xs text-muted-foreground mt-3">
          Não há registros para exportar — o dispositivo ainda não enviou dados.
        </p>
      ) : null}
      {erro ? <p className="text-xs text-destructive mt-3">{erro}</p> : null}

      {/* LGPD-01 (b), 03/11: o link volta porque agora há a página que o
          serve (`/privacidade`). Antes ele tinha saído daqui por anunciar um
          link que não abria. */}
      <div className={`${LINHA_DE_CONFIGURACAO} border-t border-border text-xs`}>
        <p className="text-muted-foreground">Como seus dados são tratados, e seus direitos:</p>
        <p className="shrink-0 text-right">
          <Link to="/privacidade" className="font-semibold text-primary transition hover:text-accent">
            Política de Privacidade
          </Link>
          .
        </p>
      </div>
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
      destrutiva
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
    <Secao titulo="Sair" icone={LogOut}>
      <button
        type="button"
        onClick={async () => {
          setSaindo(true);
          await sair();
          navigate("/login");
        }}
        disabled={saindo}
        className={`${LINHA_DE_CONFIGURACAO} w-full text-left text-sm font-medium text-foreground transition hover:text-primary disabled:opacity-60`}
      >
        {saindo ? "Saindo..." : "Sair da conta"}
        <LogOut className="size-4 shrink-0 text-muted-foreground" aria-hidden />
      </button>
    </Secao>
  );
}
