import {
  AlertTriangle,
  ArrowRight,
  Check,
  Loader2,
  Play,
  Smartphone,
  Square,
  X,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router";

import { Moldura } from "../components/Blueprint";
import { EPOCAS_DISPONIVEIS_S, EPOCA_PADRAO_S, desvio } from "../lib/acelerometro";
import { ErroApi } from "../lib/api";
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
  const [epoca, setEpoca] = useState<number>(EPOCA_PADRAO_S);
  // Pareamento automático (APP-08): a sessão já identifica o dono, então o
  // aparelho prepara o próprio dispositivo sem o usuário ver credencial.
  const [dispositivo, setDispositivo] = useState<string | null>(null);
  const [nomeDoDispositivo, setNomeDoDispositivo] = useState<string | null>(null);
  const [erroDePreparo, setErroDePreparo] = useState<string | null>(null);

  const { estado, erro, registros, amostrasNaEpoca, decorridoMs, comecar, parar } =
    useColeta(epoca, dispositivo);

  useEffect(() => {
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
  }, []);

  const coletando = estado === "coletando";
  const pronto = dispositivo !== null;
  const falhas = contarFalhas(registros);
  const resumo = resumoDaSessao(registros);

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs text-muted-foreground uppercase tracking-wider">
          Registrar movimento
        </p>
        <h1 className="text-xl sm:text-2xl font-semibold text-foreground mt-1">
          Usar este celular como sensor
        </h1>
      </div>

      {/* Fixo. Ver a nota no topo do arquivo. Diz primeiro o que FAZER, e
          só depois o porquê — antes começava por "não serve para", que soa
          como defeito em vez de instrução. */}
      <div className="flex gap-3 rounded-xl border border-amber-500/40 bg-amber-500/5 p-4">
        <AlertTriangle className="w-5 h-5 flex-shrink-0 text-amber-500" aria-hidden />
        <div className="text-sm text-muted-foreground space-y-1.5">
          <p className="font-semibold text-foreground">Deixe a tela ligada e o app aberto.</p>
          <p>
            O navegador desliga o sensor quando a tela bloqueia — então isto{" "}
            <strong className="font-semibold">não cobre uma noite de sono</strong>. Serve
            para sessões de alguns minutos, com o aparelho apoiado e você por perto. Para a
            noite inteira é preciso o sensor no travesseiro.
          </p>
        </div>
      </div>

      <Moldura>
        {/* --- o caminho principal: um botão, um estado, uma saída --- */}
        {erroDePreparo ? (
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
            <div className="flex items-baseline gap-2">
              <Smartphone className="w-5 h-5 self-center animate-pulse text-primary" aria-hidden />
              <span className="text-2xl font-semibold tabular-nums text-foreground">
                {formatarDuracao(decorridoMs)}
              </span>
              <span className="text-sm text-muted-foreground">
                · {resumo.total} {resumo.total === 1 ? "registro" : "registros"}
              </span>
            </div>

            <button
              onClick={parar}
              className="inline-flex items-center gap-2 rounded-xl bg-destructive px-5 py-2.5 font-semibold text-destructive-foreground transition-all duration-200 hover:-translate-y-0.5 active:translate-y-0"
            >
              <Square className="w-4 h-4" />
              Parar
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            <button
              onClick={() => void comecar()}
              className="inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-2.5 font-semibold text-primary-foreground transition-all duration-200 hover:-translate-y-0.5 active:translate-y-0"
            >
              <Play className="w-4 h-4" />
              Começar a registrar
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
      </Moldura>


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
    </div>
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
