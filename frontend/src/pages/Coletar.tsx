import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Check,
  Loader2,
  Play,
  Square,
  X,
} from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router";

import { BarraDoWorkspace } from "../components/BarraDoWorkspace";
import { TelaDeConsentimento } from "../components/TelaDeConsentimento";
import { usePerfil } from "../contexts/PerfilContext";
import { usePortaoDoConsentimento } from "../hooks/usePortaoDoConsentimento";
import { consentimentoVigente, registrarConsentimento } from "../lib/consentimento";
import { noiteNativaDisponivel } from "../lib/noiteNativa";
import { EPOCAS_DISPONIVEIS_S, EPOCA_PADRAO_S, desvio } from "../lib/acelerometro";
import { ErroApi } from "../lib/api";
import { estaEmModoDemo } from "../lib/demo";
import { prepararDispositivoDoCelular } from "../lib/coleta";
import { formatarDuracao } from "../lib/metricas";
import { contarFalhas, resumoDaSessao } from "../lib/sessaoDeColeta";
import { useColeta, type Registro } from "../hooks/useColeta";
import { GRAVIDADE, LIMIAR_DE_MOVIMENTO } from "../types/sleep";

/**
 * Coleta pelo acelerômetro do celular.
 *
 * ── DUAS PLATEIAS, E ELAS QUEREM COISAS DIFERENTES (APP-12) ─────────────
 *
 * Esta tela nasceu como **instrumento de bancada** (APP-01), para gravar em
 * paralelo com o dispositivo e comparar as duas medições (VIA-02). Por isso
 * ela expunha as engrenagens: seletor de época, contagem de amostras, tabela
 * de m/s² por registro.
 *
 * Depois o objetivo mudou — o celular passou a ser a alternativa para quem
 * não comprou o sensor — e a tela não acompanhou. "Época de agregação" é
 * vocabulário de quem escreveu o código, não de quem vai dormir. Quem usa
 * quer apertar um botão e, no fim, ver um gráfico.
 *
 * A divisão é essa: o caminho principal tem **um botão, um estado e uma
 * saída** (o painel). As engrenagens continuam existindo, recolhidas em
 * "detalhes técnicos", porque a bancada ainda precisa delas.
 *
 * ── O QUE NÃO PODE SE ESCONDER ──────────────────────────────────────────
 *
 * Simplificar não pode virar esconder problema. Duas coisas ficam sempre no
 * caminho principal:
 *
 * 1. **O aviso de que isto não cobre a noite.** O navegador corta o sensor
 *    quando a tela bloqueia — é limite do sistema operacional, não do código.
 *    Uma tela bonita que deixa a pessoa achar que pode dormir com ela seria
 *    uma promessa falsa, e ela acordaria com o gráfico vazio.
 * 2. **Falhas de envio.** Se um registro não gravou, isso aparece na frente,
 *    e não dentro de um bloco recolhido.
 */

export function Coletar() {
  return estaEmModoDemo() ? <ColetaDemonstrativa /> : <ColetaReal />;
}

const CLASSE_INICIAR = "inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground hover:opacity-90";
const CLASSE_ENCERRAR = "inline-flex items-center gap-2 rounded-xl bg-destructive px-5 py-2.5 text-sm font-semibold text-destructive-foreground hover:opacity-90";

function TelaDaColeta({ children }: { children: ReactNode }) {
  return (
    <div className="mx-auto max-w-[1540px] space-y-3.5">
      <header>
        <BarraDoWorkspace secao="Nova coleta" />
        <h1 className="text-2xl font-extrabold tracking-tight text-foreground sm:text-[27px]">Nova coleta</h1>
        <p className="mt-0.5 text-xs text-muted-foreground">Inicie uma sessão de registro de movimento.</p>
      </header>
      <div className="flex items-start gap-2 rounded-xl border border-amber-500/30 border-l-4 bg-amber-500/10 px-3 py-3 text-sm text-foreground">
        <AlertTriangle className="size-4 shrink-0 text-amber-700 dark:text-amber-300" aria-hidden />
        <p><strong>Importante.</strong> Mantenha a tela ligada e esta página aberta. A coleta pelo navegador é indicada para sessões curtas e não cobre uma noite de sono.</p>
      </div>
      {children}
    </div>
  );
}

function CartaoDaColeta({
  decorridoMs,
  titulo,
  estado,
  descricao,
  children,
}: {
  decorridoMs: number;
  titulo: string;
  estado: string;
  descricao: string;
  children: ReactNode;
}) {
  const segundos = Math.floor(decorridoMs / 1000);
  const horario = [Math.floor(segundos / 3600), Math.floor(segundos / 60) % 60, segundos % 60]
    .map((parte) => String(parte).padStart(2, "0")).join(":");
  return (
    <section aria-labelledby="titulo-cartao-coleta" className="flex min-h-[390px] flex-col items-center justify-center rounded-[14px] border border-border bg-card px-4 py-6 text-center shadow-sm">
      <span className="grid size-20 place-items-center rounded-full bg-primary/10 text-primary sm:size-24">
        <Activity className="size-7" aria-hidden />
      </span>
      <h2 id="titulo-cartao-coleta" className="mt-3 text-lg font-extrabold text-foreground">{titulo}</h2>
      <p className="mt-2 max-w-md text-sm text-muted-foreground">{descricao}</p>
      <p aria-label="Tempo decorrido" className="mt-5 text-4xl font-extrabold tabular-nums tracking-tight text-foreground">{horario}</p>
      <p role="status" className="mb-4 mt-3 rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
        {estado}
      </p>
      {children}
    </section>
  );
}

function Orientacoes({ demo = false }: { demo?: boolean }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <section className="rounded-[14px] border border-border bg-card p-4 shadow-sm">
        <h2 className="text-sm font-bold text-foreground">Como se preparar</h2>
        <ol className="mt-2 list-decimal space-y-1 pl-4 text-xs text-muted-foreground">
          <li>Apoie o celular em uma superfície estável.</li>
          <li>Mantenha esta página aberta e a tela ligada.</li>
          <li>Inicie o registro e permaneça próximo ao aparelho.</li>
        </ol>
      </section>
      <section className="rounded-[14px] border border-border bg-card p-4 shadow-sm">
        <h2 className="text-sm font-bold text-foreground">O que será registrado</h2>
        <p className="mt-2 text-xs text-muted-foreground">
          {demo ? "Esta demonstração exibe somente o cronômetro da sessão."
            : "O acelerômetro mede movimentos. Os registros enviados podem ser consultados no painel."}
        </p>
      </section>
    </div>
  );
}

function ColetaDemonstrativa() {
  const [inicio, setInicio] = useState<number | null>(null);
  const [decorridoMs, setDecorridoMs] = useState(0);
  const [encerrada, setEncerrada] = useState(false);
  useEffect(() => {
    if (inicio === null) return;
    const timer = window.setInterval(() => setDecorridoMs(Date.now() - inicio), 250);
    return () => window.clearInterval(timer);
  }, [inicio]);

  const coletando = inicio !== null;
  return (
    <TelaDaColeta>
      <CartaoDaColeta
        decorridoMs={decorridoMs}
        titulo={coletando ? "Coleta em andamento" : encerrada ? "Sessão encerrada" : "Pronto para começar?"}
        estado={coletando ? "Simulação em andamento" : encerrada ? "Simulação encerrada" : "Aguardando início"}
        descricao="Modo de demonstração. O cronômetro simula uma sessão sem usar sensores nem gravar dados."
      >
        {coletando ? (
          <button type="button" className={CLASSE_ENCERRAR} onClick={() => {
            setDecorridoMs(Date.now() - inicio);
            setInicio(null);
            setEncerrada(true);
          }}>Encerrar simulação</button>
        ) : (
          <button type="button" className={CLASSE_INICIAR} onClick={() => {
            setDecorridoMs(0);
            setEncerrada(false);
            setInicio(Date.now());
          }}>Iniciar simulação</button>
        )}
      </CartaoDaColeta>
      <Orientacoes demo />
    </TelaDaColeta>
  );
}

function ColetaReal() {
  const [epoca, setEpoca] = useState<number>(EPOCA_PADRAO_S);
  // Pareamento automático (APP-08): a sessão já identifica o dono, então o
  // aparelho prepara o próprio dispositivo sem o usuário ver credencial.
  const [dispositivo, setDispositivo] = useState<string | null>(null);
  const [nomeDoDispositivo, setNomeDoDispositivo] = useState<string | null>(null);
  const [erroDePreparo, setErroDePreparo] = useState<string | null>(null);

  const { estado, erro, registros, amostrasNaEpoca, decorridoMs, comecar, parar } =
    useColeta(epoca, dispositivo);

  // LGPD-12: sem o consentimento vigente, o servidor recusa preparar o
  // dispositivo (403). O preparo espera por ele, e "Começar" abre a tela antes.
  const { perfil, recarregar } = usePerfil();
  const vigente = consentimentoVigente(perfil);
  const portao = usePortaoDoConsentimento({
    vigente,
    registrar: async () => {
      await registrarConsentimento();
      await recarregar();
    },
  });

  useEffect(() => {
    if (!vigente) return;
    let vivo = true;
    prepararDispositivoDoCelular()
      .then((d) => {
        if (!vivo) return;
        setDispositivo(d.id);
        setNomeDoDispositivo(d.nome);
      })
      .catch((e) => {
        if (!vivo) return;
        setErroDePreparo(
          e instanceof ErroApi ? e.message : "Não foi possível preparar este aparelho.",
        );
      });
    return () => {
      vivo = false;
    };
  }, [vigente]);

  const coletando = estado === "coletando";
  const pronto = dispositivo !== null;
  const falhas = contarFalhas(registros);
  const resumo = resumoDaSessao(registros);

  const iniciouSessao = decorridoMs > 0 || resumo.total > 0;
  const situacao = erroDePreparo || erro ? "Atenção necessária"
    : coletando ? "Registrando"
    : vigente && !pronto ? "Preparando aparelho"
    : iniciouSessao ? "Sessão encerrada" : "Aguardando início";

  return (
    <TelaDaColeta>
      {portao.telaAberta && (
        <TelaDeConsentimento aoConcordar={portao.concordar} aoRecusar={portao.recusar} erro={portao.erro} />
      )}
      {noiteNativaDisponivel() && (
        <Link
          to="/noite"
          className="flex items-center justify-between gap-3 rounded-xl border border-primary/40 bg-primary/5 p-4 text-sm"
        >
          <span>
            <span className="font-semibold text-foreground">Registrar a noite inteira</span>
            <span className="block text-muted-foreground">
              No app, o registro continua com a tela apagada.
            </span>
          </span>
          <ArrowRight className="w-4 h-4 flex-shrink-0" aria-hidden />
        </Link>
      )}

      <CartaoDaColeta
        decorridoMs={decorridoMs}
        titulo={coletando ? "Coleta em andamento" : iniciouSessao ? "Resumo da sessão" : "Pronto para começar?"}
        estado={situacao}
        descricao={coletando
          ? `${resumo.total} ${resumo.total === 1 ? "registro" : "registros"} nesta sessão`
          : "Use o acelerômetro deste celular para registrar movimentos durante uma sessão curta."}
      >
        {!vigente ? (
          // LGPD-12: antes do consentimento não há preparo (o servidor recusaria);
          // o botão abre a tela, e depois dela o aparelho se prepara.
          <button
            onClick={() => portao.pedir(() => undefined)}
            className="inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-2.5 font-semibold text-primary-foreground transition-all duration-200 hover:-translate-y-0.5 active:translate-y-0"
          >
            <Play className="w-4 h-4" />
            Iniciar coleta
          </button>
        ) : erroDePreparo ? (
          <p className="text-sm text-destructive" role="alert">
            {erroDePreparo}
          </p>
        ) : !pronto ? (
          <p className="inline-flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="w-4 h-4 animate-spin" aria-hidden />
            Preparando este aparelho...
          </p>
        ) : coletando ? (
          <div className="space-y-4">
            <button
              onClick={parar}
              className="inline-flex items-center gap-2 rounded-xl bg-destructive px-5 py-2.5 font-semibold text-destructive-foreground transition-all duration-200 hover:-translate-y-0.5 active:translate-y-0"
            >
              <Square className="w-4 h-4" />
              Encerrar sessão
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            <button
              onClick={() => portao.pedir(() => comecar())}
              className="inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-2.5 font-semibold text-primary-foreground transition-all duration-200 hover:-translate-y-0.5 active:translate-y-0"
            >
              <Play className="w-4 h-4" />
              Iniciar coleta
            </button>

            {/* A saída. Sem isto a pessoa coleta e a tela não a leva a lugar
                nenhum — e o gráfico é o ponto inteiro. */}
            {resumo.total > 0 && (
              <div className="text-sm text-muted-foreground">
                <p>
                  {resumo.total} {resumo.total === 1 ? "registro" : "registros"} nesta
                  sessão, {formatarDuracao(decorridoMs)} de captação.
                </p>
                <Link
                  to="/dashboard"
                  className="mt-2 inline-flex items-center gap-1.5 font-semibold text-primary hover:underline"
                >
                  Ver no painel
                  <ArrowRight className="w-4 h-4" />
                </Link>
              </div>
            )}
          </div>
        )}

        {/* Falha nunca fica dentro dos detalhes recolhidos. */}
        {falhas > 0 && (
          <p className="mt-4 text-sm text-destructive" role="alert">
            {falhas} {falhas === 1 ? "registro não foi gravado" : "registros não foram gravados"}.
            Abra os detalhes técnicos para ver o motivo.
          </p>
        )}

        {erro && (
          <p className="mt-4 text-sm text-destructive" role="alert">
            {erro}
          </p>
        )}
      </CartaoDaColeta>
      <Orientacoes />

      {/* --- as engrenagens, recolhidas --- */}
      <details className="rounded-xl border border-border/70 bg-card">
        <summary className="cursor-pointer px-5 py-3 text-sm font-semibold text-foreground">
          Detalhes técnicos
        </summary>

        <div className="border-t border-border/70 px-5 py-4 space-y-5">
          <p className="text-xs text-muted-foreground">
            Enviando como{" "}
            <strong className="font-semibold text-foreground">{nomeDoDispositivo}</strong>.
            Este aparelho aparece no painel como um dispositivo seu.
          </p>

          <label className="block">
            <span className="text-xs uppercase tracking-wider text-muted-foreground">
              Janela de agregação
            </span>
            <select
              value={epoca}
              onChange={(e) => setEpoca(Number(e.target.value))}
              disabled={coletando}
              className="mt-1.5 block rounded-lg border border-border bg-input-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-60"
            >
              {EPOCAS_DISPONIVEIS_S.map((s) => (
                <option key={s} value={s}>
                  {s} segundos
                </option>
              ))}
            </select>
            <span className="mt-1.5 block text-xs text-muted-foreground">
              Um registro por janela, com o pico de magnitude do período.
            </span>
          </label>

          {coletando && (
            <p className="text-xs text-muted-foreground">
              {amostrasNaEpoca} amostras na janela atual.
            </p>
          )}

          {registros.length > 0 && (
            <div>
              <h3 className="text-xs font-semibold text-foreground">
                Registros ({registros.length})
              </h3>
              <ul className="mt-3 space-y-2">
                {registros.slice(0, 12).map((r) => (
                  <LinhaDeRegistro key={r.agregado.fimEmMs} registro={r} />
                ))}
              </ul>
              <p className="mt-4 text-xs text-muted-foreground">
                Repouso é a magnitude perto de {GRAVIDADE} m/s². A coluna do meio é o desvio;
                acima de {LIMIAR_DE_MOVIMENTO} m/s² o próprio aparelho rotula como movimento
                — o mesmo critério do firmware.
              </p>
            </div>
          )}
        </div>
      </details>
    </TelaDaColeta>
  );
}

function LinhaDeRegistro({ registro }: { registro: Registro }) {
  const intensidade = desvio(registro.agregado);
  const movimento = intensidade > LIMIAR_DE_MOVIMENTO;

  return (
    <li className="border-b border-border/50 pb-2 text-sm last:border-0">
      <div className="flex items-center justify-between gap-3">
        <span className="font-mono text-xs text-muted-foreground">
          {new Date(registro.agregado.fimEmMs).toLocaleTimeString("pt-BR")}
        </span>
        <span className="font-mono text-xs text-muted-foreground">
          {registro.agregado.amostras} am.
        </span>
        <span className="font-mono text-xs tabular-nums text-foreground">
          {intensidade.toFixed(2)} m/s²
        </span>
        <span
          className={`text-xs font-semibold ${movimento ? "text-chart-movimento" : "text-chart-repouso"}`}
        >
          {movimento ? "Movimento" : "Repouso"}
        </span>
        <MarcaDeEnvio registro={registro} />
      </div>
      {/* O motivo fica na própria linha. `title` é tooltip de mouse, e esta
          tela é para celular. */}
      {registro.envio === "falhou" && registro.falha && (
        <p className="mt-1 text-xs text-destructive" role="alert">
          {registro.falha}
        </p>
      )}
    </li>
  );
}

/**
 * O estado do envio de uma época (APP-10).
 *
 * Três estados, três desenhos. A versão anterior mostrava X vermelho enquanto
 * ainda estava enviando — o registro entra na lista antes de a requisição
 * terminar, e a tela lia `enviada ? check : X`. Parecia perda de dado.
 */
function MarcaDeEnvio({ registro }: { registro: Registro }) {
  if (registro.envio === "enviando") {
    return (
      <Loader2
        className="w-4 h-4 flex-shrink-0 animate-spin text-muted-foreground"
        aria-label="enviando"
      />
    );
  }
  if (registro.envio === "gravada") {
    return <Check className="w-4 h-4 flex-shrink-0 text-primary" aria-label="gravada" />;
  }
  return <X className="w-4 h-4 flex-shrink-0 text-destructive" aria-label="falhou" />;
}
