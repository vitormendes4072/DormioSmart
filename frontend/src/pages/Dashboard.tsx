import { Activity, Clock, Moon, Waves } from "lucide-react";
import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { CardMetrica } from "../components/CardMetrica";
import { Carregando, FalhaAoCarregar, SemLeituras } from "../components/EstadoDaTela";
import { NotaDeEscopo } from "../components/NotaDeEscopo";
import { useHistorico } from "../hooks/useHistorico";
import {
  calcularMetricas,
  formatarDuracao,
  formatarHora,
  prepararSerie,
  type PontoDaSerie,
} from "../lib/metricas";
import { ehMovimento, intensidade } from "../types/sleep";

/**
 * Cores da serie via token, nao hex cru (BRAND-01).
 *
 * Precisam mudar junto com o tema — um ambar calibrado para fundo escuro
 * perde contraste sobre branco. Os valores por tema estao em theme.css, com o
 * contraste verificado ao lado de cada um.
 *
 * A cor nunca e o unico sinal: o tooltip e a coluna "Estado" da tabela dizem
 * "Movimento"/"Repouso" por escrito, o que resolve tanto daltonismo quanto
 * impressao em preto e branco.
 */
const COR_MOVIMENTO = "var(--chart-movimento)";
const COR_REPOUSO = "var(--chart-repouso)";

function TooltipDoGrafico({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ payload: PontoDaSerie }>;
  label?: string;
}) {
  const ponto = payload?.[0]?.payload;
  if (!active || !ponto) return null;

  return (
    <div className="bg-card border border-border rounded-xl px-3 py-2 text-sm shadow-2xl">
      <p className="text-muted-foreground text-xs mb-0.5">{label}</p>
      <p className="text-foreground font-semibold">
        {ponto.intensidade == null ? "sem leitura" : `${ponto.intensidade.toFixed(2)} m/s²`}
      </p>
      <p className="text-xs mt-0.5" style={{ color: ponto.movimento ? COR_MOVIMENTO : COR_REPOUSO }}>
        {ponto.movimento ? "Movimento" : "Repouso"}
      </p>
    </div>
  );
}

export function Dashboard() {
  const { leituras, carregando, erro, recarregar } = useHistorico();

  if (carregando) {
    return (
      <div className="space-y-6">
        <Cabecalho />
        <Carregando />
      </div>
    );
  }

  if (erro) {
    return (
      <div className="space-y-6">
        <Cabecalho />
        <FalhaAoCarregar mensagem={erro} aoTentarNovamente={recarregar} />
      </div>
    );
  }

  if (leituras.length === 0) {
    return (
      <div className="space-y-6">
        <Cabecalho />
        <NotaDeEscopo />
        <SemLeituras />
      </div>
    );
  }

  const m = calcularMetricas(leituras);
  const serie = prepararSerie(leituras);
  const emRepouso = m.totalLeituras - m.eventosDeMovimento;
  const pctMovimento = m.totalLeituras > 0 ? (m.eventosDeMovimento / m.totalLeituras) * 100 : 0;

  return (
    <div className="space-y-6">
      <Cabecalho
        periodo={
          m.janela
            ? `${formatarHora(m.janela.inicio)} — ${formatarHora(m.janela.fim)}`
            : undefined
        }
      />

      <NotaDeEscopo />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <CardMetrica
          rotulo="Eventos"
          valor={m.eventosDeMovimento}
          detalhe={`em ${m.totalLeituras} ${m.totalLeituras === 1 ? "leitura" : "leituras"}`}
          icone={Activity}
          corDoIcone="text-amber-400"
        />
        <CardMetrica
          rotulo="Captação"
          valor={formatarDuracao(m.duracaoDaJanelaMs)}
          detalhe="janela registrada"
          icone={Clock}
          corDoIcone="text-blue-400"
        />
        <CardMetrica
          rotulo="Sem movimento"
          valor={formatarDuracao(m.maiorPeriodoSemMovimentoMs)}
          detalhe="maior intervalo contínuo"
          icone={Moon}
          corDoIcone="text-indigo-400"
        />
        <CardMetrica
          rotulo="Intensidade"
          valor={m.intensidadeMedia == null ? null : m.intensidadeMedia.toFixed(2)}
          unidade="m/s²"
          detalhe="média do desvio do repouso"
          icone={Waves}
          corDoIcone="text-primary"
        />
      </div>

      <div className="bg-card border border-border rounded-2xl p-4 sm:p-6">
        <div className="flex items-start justify-between gap-4 mb-5 flex-wrap">
          <div>
            <h3 className="text-sm font-semibold text-foreground">Intensidade do movimento</h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Desvio do repouso ao longo da captação · |magnitude − 9,81 m/s²|
            </p>
          </div>
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-sm inline-block" style={{ background: COR_REPOUSO }} />
              Repouso
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-sm inline-block" style={{ background: COR_MOVIMENTO }} />
              Movimento
            </span>
          </div>
        </div>
        <div className="h-44 sm:h-56">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={serie} margin={{ top: 4, right: 4, left: -12, bottom: 0 }}>
              <XAxis
                dataKey="hora"
                axisLine={false}
                tickLine={false}
                tick={{ fill: "var(--muted-foreground)", fontSize: 11, fontFamily: "Outfit" }}
                minTickGap={24}
              />
              <YAxis
                axisLine={false}
                tickLine={false}
                tick={{ fill: "var(--muted-foreground)", fontSize: 11, fontFamily: "Outfit" }}
                tickFormatter={(v: number) => v.toFixed(1)}
              />
              <Tooltip
                content={<TooltipDoGrafico />}
                cursor={{ fill: "var(--secondary)", fillOpacity: 0.5 }}
              />
              {/* Animacao desligada de proposito: o dashboard recarrega os
                  dados periodicamente, e reanimar as barras a cada atualizacao
                  vira ruido visual. Tambem torna a captura de tela confiavel —
                  com animacao, um print pode pegar as barras no meio do
                  crescimento e mostrar valores que nao existem. */}
              <Bar dataKey="intensidade" radius={[3, 3, 0, 0]} isAnimationActive={false}>
                {serie.map((ponto, i) => (
                  <Cell key={i} fill={ponto.movimento ? COR_MOVIMENTO : COR_REPOUSO} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        <div className="lg:col-span-2 bg-card border border-border rounded-2xl p-4 sm:p-6">
          <h3 className="text-sm font-semibold text-foreground">Repouso × Movimento</h3>
          <p className="text-xs text-muted-foreground mt-0.5 mb-5">
            Dois estados — é o que o sensor distingue
          </p>

          <div className="space-y-4">
            <Barra
              rotulo="Repouso"
              quantidade={emRepouso}
              porcentagem={100 - pctMovimento}
              cor={COR_REPOUSO}
            />
            <Barra
              rotulo="Movimento"
              quantidade={m.eventosDeMovimento}
              porcentagem={pctMovimento}
              cor={COR_MOVIMENTO}
            />
          </div>

          {m.janela ? (
            <div className="mt-5 pt-5 border-t border-border grid grid-cols-2 gap-3">
              <div className="text-center">
                <p className="text-lg font-bold text-foreground">
                  {formatarHora(m.janela.inicio)}
                </p>
                <p className="text-xs text-muted-foreground mt-0.5">Primeira leitura</p>
              </div>
              <div className="text-center">
                <p className="text-lg font-bold text-foreground">{formatarHora(m.janela.fim)}</p>
                <p className="text-xs text-muted-foreground mt-0.5">Última leitura</p>
              </div>
            </div>
          ) : null}
        </div>

        <div className="lg:col-span-3 bg-card border border-border rounded-2xl p-4 sm:p-6">
          <div className="mb-5">
            <h3 className="text-sm font-semibold text-foreground">Leituras recentes</h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Amostras individuais, da mais recente para a mais antiga
            </p>
          </div>

          <div className="overflow-x-auto -mx-4 sm:mx-0 px-4 sm:px-0">
            <table className="w-full text-sm min-w-[22rem]">
              <thead>
                <tr className="text-xs text-muted-foreground uppercase tracking-wider">
                  <th className="text-left font-medium pb-2">Hora</th>
                  <th className="text-right font-medium pb-2">Intensidade</th>
                  <th className="text-right font-medium pb-2">Temp. chip</th>
                  <th className="text-right font-medium pb-2">Estado</th>
                </tr>
              </thead>
              <tbody>
                {leituras.slice(0, 8).map((leitura, i) => {
                  const valor = intensidade(leitura);
                  const movimento = ehMovimento(leitura.status);
                  const instante = new Date(leitura.created_at);
                  return (
                    <tr key={i} className="border-t border-border">
                      <td className="py-2.5 text-foreground">
                        {Number.isNaN(instante.getTime()) ? "--" : formatarHora(instante)}
                      </td>
                      <td className="py-2.5 text-right font-mono text-muted-foreground">
                        {valor == null ? "--" : valor.toFixed(2)}
                      </td>
                      <td className="py-2.5 text-right text-muted-foreground">
                        {leitura.temp == null ? "--" : `${leitura.temp.toFixed(1)}°C`}
                      </td>
                      <td
                        className="py-2.5 text-right text-xs font-medium"
                        style={{ color: movimento ? COR_MOVIMENTO : COR_REPOUSO }}
                      >
                        {movimento ? "Movimento" : "Repouso"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <p className="text-xs text-muted-foreground mt-4">
            O agrupamento por sessão de noite depende do modelo de amostragem (DATA-02), ainda
            em aberto — por isso a lista mostra amostras, não sessões.
          </p>
        </div>
      </div>
    </div>
  );
}

function Cabecalho({ periodo }: { periodo?: string }) {
  return (
    <div className="min-w-0">
      <p className="text-xs text-muted-foreground uppercase tracking-wider">
        {periodo ?? "Monitoramento"}
      </p>
      <h1 className="text-xl sm:text-2xl font-semibold text-foreground mt-1">
        Movimento durante o repouso
      </h1>
    </div>
  );
}

function Barra({
  rotulo,
  quantidade,
  porcentagem,
  cor,
}: {
  rotulo: string;
  quantidade: number;
  porcentagem: number;
  cor: string;
}) {
  return (
    <div>
      <div className="flex justify-between text-xs mb-1.5">
        <span className="text-muted-foreground">{rotulo}</span>
        <span className="text-foreground font-semibold">
          {quantidade} · {porcentagem.toFixed(0)}%
        </span>
      </div>
      <div className="h-1.5 bg-secondary rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${porcentagem}%`, backgroundColor: cor }}
        />
      </div>
    </div>
  );
}
