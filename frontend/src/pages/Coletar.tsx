import { AlertTriangle, Check, Loader2, Play, Smartphone, Square, X } from "lucide-react";
import { useEffect, useState } from "react";

import { Moldura } from "../components/Blueprint";
import { NotaDeEscopo } from "../components/NotaDeEscopo";
import { EPOCAS_DISPONIVEIS_S, EPOCA_PADRAO_S, desvio } from "../lib/acelerometro";
import { prepararDispositivoDoCelular } from "../lib/coleta";
import { ErroApi } from "../lib/api";
import { useColeta, type Registro } from "../hooks/useColeta";
import { GRAVIDADE, LIMIAR_DE_MOVIMENTO } from "../types/sleep";

/**
 * Coleta pelo acelerômetro do celular (APP-01).
 *
 * ── PARA QUE ISTO EXISTE ────────────────────────────────────────────────
 *
 * Não é um substituto do dispositivo — é um **instrumento de referência**.
 * Gravar celular e travesseiro ao mesmo tempo, no mesmo evento, dá validade
 * concorrente à medição do protótipo (VIA-02). Sem isso, o VIA-01 é uma
 * afirmação sobre um único instrumento, sem comparador.
 *
 * ── O QUE ELE NÃO FAZ, E A TELA DIZ ─────────────────────────────────────
 *
 * Não monitora a noite inteira. `devicemotion` para quando a tela bloqueia ou
 * a aba vai para o fundo; o Wake Lock segura a tela acesa ao custo de bateria
 * e calor. Um coletor que promete a noite e entrega quatro minutos é pior do
 * que nenhum, então o aviso é fixo e não dispensável — a mesma regra da faixa
 * de demonstração e da legenda do traçado da landing.
 */

/**
 * O estado do envio de uma época (APP-10).
 *
 * Três estados, três desenhos. A versão anterior mostrava **X vermelho
 * enquanto ainda estava enviando** — o registro entra na lista antes de a
 * requisição terminar, e a tela lia `enviada ? check : X`. A época piscava
 * em vermelho e virava certa um segundo depois, o que parece perda de dado.
 *
 * O motivo da falha fica na própria linha, e não num `title`: `title` é
 * tooltip de passagem de mouse, e esta tela existe para ser usada no celular,
 * onde não há mouse. O texto ficava inalcançável justamente em quem mais
 * precisa dele.
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

export function Coletar() {
  const [epoca, setEpoca] = useState<number>(EPOCA_PADRAO_S);
  // Pareamento automático (APP-08): a sessão já identifica o dono, então o
  // aparelho prepara o próprio dispositivo sem o usuário ver credencial.
  const [dispositivo, setDispositivo] = useState<string | null>(null);
  const [nomeDoDispositivo, setNomeDoDispositivo] = useState<string | null>(null);
  const [erroDePreparo, setErroDePreparo] = useState<string | null>(null);

  const { estado, erro, registros, amostrasNaEpoca, comecar, parar } = useColeta(
    epoca,
    dispositivo,
  );

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

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs text-muted-foreground uppercase tracking-wider">
          Instrumento de referência
        </p>
        <h1 className="text-xl sm:text-2xl font-semibold text-foreground mt-1">
          Coletar pelo celular
        </h1>
      </div>

      {/* Fixo e não dispensável. Ver a nota no topo do arquivo. */}
      <div className="flex gap-3 rounded-xl border border-amber-500/40 bg-amber-500/5 p-4">
        <AlertTriangle className="w-5 h-5 flex-shrink-0 text-amber-500" aria-hidden />
        <div className="text-sm text-muted-foreground space-y-1.5">
          <p className="font-semibold text-foreground">Não serve para a noite inteira.</p>
          <p>
            O navegador interrompe o sensor quando a tela bloqueia ou a aba sai de foco. Mesmo
            com a tela travada acesa, o aparelho esquenta e a bateria cai. Use para sessões de
            minutos — teste de bancada e comparação com o dispositivo.
          </p>
        </div>
      </div>

      <NotaDeEscopo />

      <Moldura>
        <h2 className="text-sm font-semibold text-foreground">Configuração</h2>

        {/* Nenhum campo de credencial, de propósito. Ver a nota em lib/coleta.ts. */}
        <div className="mt-4 text-sm">
          {erroDePreparo ? (
            <p className="text-destructive" role="alert">
              {erroDePreparo}
            </p>
          ) : pronto ? (
            <p className="text-muted-foreground">
              Enviando como{" "}
              <strong className="font-semibold text-foreground">{nomeDoDispositivo}</strong>.
              Este aparelho aparece no painel como um dispositivo seu.
            </p>
          ) : (
            <p className="inline-flex items-center gap-2 text-muted-foreground">
              <Loader2 className="w-4 h-4 animate-spin" aria-hidden />
              Preparando este aparelho...
            </p>
          )}
        </div>

        <label className="block mt-4">
          <span className="text-xs uppercase tracking-wider text-muted-foreground">
            Época de agregação
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
            Uma leitura por época, com o pico de magnitude da janela. Amostrar a 50 Hz e enviar
            tudo daria 180 mil linhas por hora.
          </span>
        </label>

        <div className="mt-5 flex flex-wrap items-center gap-3">
          {coletando ? (
            <button
              onClick={parar}
              className="inline-flex items-center gap-2 rounded-xl bg-destructive px-5 py-2.5 font-semibold text-destructive-foreground transition-all duration-200 hover:-translate-y-0.5 active:translate-y-0"
            >
              <Square className="w-4 h-4" />
              Parar
            </button>
          ) : (
            <button
              onClick={() => void comecar()}
              disabled={!pronto}
              className="inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-2.5 font-semibold text-primary-foreground transition-all duration-200 hover:-translate-y-0.5 active:translate-y-0 disabled:opacity-50 disabled:hover:translate-y-0"
            >
              <Play className="w-4 h-4" />
              Começar a coletar
            </button>
          )}

          {coletando && (
            <span className="inline-flex items-center gap-2 text-sm text-muted-foreground">
              <Smartphone className="w-4 h-4 animate-pulse text-primary" aria-hidden />
              {amostrasNaEpoca} amostras nesta época
            </span>
          )}
        </div>

        {erro && (
          <p className="mt-4 text-sm text-destructive" role="alert">
            {erro}
          </p>
        )}
      </Moldura>

      {registros.length > 0 && (
        <Moldura>
          <h2 className="text-sm font-semibold text-foreground">
            Épocas registradas ({registros.length})
          </h2>
          <ul className="mt-4 space-y-2">
            {registros.slice(0, 12).map((r) => {
              const intensidade = desvio(r.agregado);
              const movimento = intensidade > LIMIAR_DE_MOVIMENTO;
              return (
                <li
                  key={r.agregado.fimEmMs}
                  className="border-b border-border/50 pb-2 text-sm last:border-0"
                >
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-mono text-xs text-muted-foreground">
                      {new Date(r.agregado.fimEmMs).toLocaleTimeString("pt-BR")}
                    </span>
                    <span className="font-mono text-xs text-muted-foreground">
                      {r.agregado.amostras} am.
                    </span>
                    <span className="font-mono text-xs tabular-nums text-foreground">
                      {intensidade.toFixed(2)} m/s²
                    </span>
                    <span
                      className={`text-xs font-semibold ${movimento ? "text-chart-movimento" : "text-chart-repouso"}`}
                    >
                      {movimento ? "Movimento" : "Repouso"}
                    </span>
                    <MarcaDeEnvio registro={r} />
                  </div>
                  {/* O motivo fica na própria linha. `title` é tooltip de
                      mouse, e esta tela é para celular. */}
                  {r.envio === "falhou" && r.falha && (
                    <p className="mt-1 text-xs text-destructive" role="alert">
                      {r.falha}
                    </p>
                  )}
                </li>
              );
            })}
          </ul>
          <p className="mt-4 text-xs text-muted-foreground">
            Repouso é a magnitude perto de {GRAVIDADE} m/s². A coluna do meio é o desvio; acima
            de {LIMIAR_DE_MOVIMENTO} m/s² o próprio aparelho rotula como movimento — o mesmo
            critério do firmware.
          </p>
        </Moldura>
      )}
    </div>
  );
}
