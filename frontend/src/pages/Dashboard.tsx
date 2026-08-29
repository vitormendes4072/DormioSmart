import { Activity, Clock, Pause, Waves } from "lucide-react";
import { useState, type ReactNode } from "react";
import {
  Bar,
  BarChart,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { CardMetrica } from "../components/CardMetrica";
import { Carregando, FalhaAoCarregar, SemLeituras } from "../components/EstadoDaTela";
import { NotaDeEscopo } from "../components/NotaDeEscopo";
import { AvisoDeMistura, SeletorDeDispositivo } from "../components/SeletorDeDispositivo";
import { useDispositivos } from "../hooks/useDispositivos";
import { useHistorico } from "../hooks/useHistorico";
import { nomeDoDispositivo, serieMisturaInstrumentos } from "../lib/dispositivos";
import { agruparEmSessoes } from "../lib/cobertura";
import {
  calcularMetricas,
  formatarDuracao,
  formatarHora,
  prepararSerie,
  type PontoDaSerie,
} from "../lib/metricas";
import { LIMIAR_DE_MOVIMENTO, ehMovimento, intensidade } from "../types/sleep";
import { AvisoDeLacuna, NotaDeInferencia } from "../components/AvisoDeLacuna";
import { SeletorDeSessao } from "../components/SeletorDeSessao";

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

  // Lacuna nao e leitura: dizer "Repouso" aqui seria o mesmo defeito que o
  // DASH-09 corrigiu nas metricas, so que no tooltip.
  if (ponto.lacuna) {
    return (
      <div className="bg-card border border-border rounded-xl px-3 py-2 text-sm shadow-2xl">
        <p className="text-foreground font-semibold">Sem medição</p>
        <p className="text-xs text-muted-foreground mt-0.5">
          {ponto.duracaoDaLacunaMs == null
            ? "trecho sem leitura"
            : `${formatarDuracao(ponto.duracaoDaLacunaMs)} sem leitura`}
        </p>
      </div>
    );
  }

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
  // `null` = todos os dispositivos. O recorte por instrumento (DASH-05) e
  // opcional: sem ele o painel se comporta como antes.
  const [dispositivo, setDispositivo] = useState<string | null>(null);
  const [verTudo, setVerTudo] = useState(false);
  const dispositivos = useDispositivos();
  const { leituras, carregando, erro, recarregar } = useHistorico({ dispositivo });

  const seletor = (
    <SeletorDeDispositivo
      dispositivos={dispositivos}
      selecionado={dispositivo}
      aoSelecionar={setDispositivo}
    />
  );

  // O seletor aparece tambem nos tres estados iniciais: se o dispositivo
  // escolhido nao tem leitura, e preciso poder trocar sem sair da tela.
  if (carregando) {
    return (
      <div className="space-y-6">
        <Cabecalho acao={seletor} />
        <Carregando />
      </div>
    );
  }

  if (erro) {
    return (
      <div className="space-y-6">
        <Cabecalho acao={seletor} />
        <FalhaAoCarregar mensagem={erro} aoTentarNovamente={recarregar} />
      </div>
    );
  }

  if (leituras.length === 0) {
    return (
      <div className="space-y-6">
        <Cabecalho acao={seletor} />
        <NotaDeEscopo />
        <SemLeituras />
      </div>
    );
  }

  // ── O RECORTE (DASH-10) ────────────────────────────────────────────
  // O painel mostrava tudo o que chegou como uma janela contínua — "das 14h
  // às 16h" — mesmo quando as leituras eram dois punhados separados por duas
  // horas de silêncio. Isso não é uma captação, são duas.
  //
  // Por padrão mostra a ÚLTIMA sessão, que é a resposta para "e agora?".
  // Quem quiser o histórico inteiro troca no seletor.
  const sessoes = agruparEmSessoes(leituras);
  const ultima = sessoes.length > 0 ? sessoes[sessoes.length - 1] : null;
  const leiturasVisiveis = verTudo || ultima === null ? leituras : ultima.leituras;

  const m = calcularMetricas(leiturasVisiveis);
  const serie = prepararSerie(leiturasVisiveis, m.cobertura);
  const temLacuna = serie.some((p) => p.lacuna);
  // A coluna cinza precisa de altura para existir; usa o topo da série, ou o
  // limiar quando tudo ficou abaixo dele.
  const topo = Math.max(
    LIMIAR_DE_MOVIMENTO,
    ...serie.map((p) => p.intensidade ?? 0),
  );
  const serieComLacuna = serie.map((p) => ({
    ...p,
    alturaDaLacuna: p.lacuna ? topo : undefined,
  }));
  // Por TEMPO MEDIDO, e não por contagem de amostra (DASH-09). Com
  // amostragem irregular, "9 eventos em 20 leituras = 45%" não significava
  // nada: as 20 leituras podiam cobrir três minutos de uma janela de duas
  // horas.
  const pctMovimento = m.fracaoEmMovimento == null ? null : m.fracaoEmMovimento * 100;
  const cob = m.cobertura;
  const pctCoberto =
    cob.janelaMs > 0 ? (cob.tempoCobertoMs / cob.janelaMs) * 100 : null;
  // Coluna inteira de "--" é ruído. O celular não reporta temperatura de chip
  // (contrato v2.0.0 tornou o campo opcional), então numa captação só de
  // celular a coluna nunca tem nada.
  const temMedidaDeTemperatura = leiturasVisiveis.some((l) => l.temp != null);
  // A tabela promete "da mais recente para a mais antiga". A API devolve
  // assim, mas `agruparEmSessoes` reordena crescente para poder recortar — no
  // modo padrão a tabela mostrava as MAIS ANTIGAS sob o rótulo contrário, e a
  // ordem virava sozinha ao clicar "Ver todas" (DASH-11). Ordenar aqui deixa a
  // promessa valer nos dois modos.
  const instanteDe = (l: { created_at: string }) =>
    typeof l.created_at === "string" && l.created_at !== ""
      ? new Date(l.created_at).getTime()
      : NaN;
  const maisRecentes = [...leiturasVisiveis]
    .filter((l) => !Number.isNaN(instanteDe(l)))
    .sort((a, b) => instanteDe(b) - instanteDe(a))
    .slice(0, 8);

  return (
    <div className="space-y-6">
      <Cabecalho
        // A MESMA janela do card "Medido": do início da cobertura ao fim dela.
        // Usar a primeira/última leitura aqui fazia o cabeçalho discordar do
        // card ao lado — "22:00 — 22:19" contra "100% de 20 min" (DASH-11).
        // O painel "Primeira/Última leitura", mais abaixo, continua com os
        // instantes das leituras, porque é isso que os rótulos dele prometem.
        periodo={
          cob.trechos.length > 0
            ? `${formatarHora(new Date(cob.trechos[0].inicio))} — ${formatarHora(
                new Date(cob.trechos[cob.trechos.length - 1].fim),
              )}`
            : undefined
        }
        instrumento={
          dispositivos.length > 1 ? nomeDoDispositivo(dispositivos, dispositivo) : undefined
        }
        acao={seletor}
      />

      {serieMisturaInstrumentos(dispositivos, dispositivo) && <AvisoDeMistura />}

      {/* A coleta teve buracos? Isso precisa aparecer ANTES dos números, e
          não depois — porque é o que decide se eles significam algo. */}
      <AvisoDeLacuna cobertura={cob} />

      {/* O recorte, e como sair dele. */}
      {sessoes.length > 1 && (
        <SeletorDeSessao
          total={sessoes.length}
          verTudo={verTudo}
          leiturasFora={leituras.length - leiturasVisiveis.length}
          aoAlternar={() => setVerTudo((v) => !v)}
        />
      )}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <CardMetrica
          rotulo="Eventos"
          valor={m.eventosDeMovimento}
          detalhe={`em ${m.totalLeituras} ${m.totalLeituras === 1 ? "leitura" : "leituras"}`}
          icone={Activity}
          corDoIcone="text-amber-400"
        />
        <CardMetrica
          rotulo="Medido"
          valor={formatarDuracao(cob.tempoCobertoMs)}
          detalhe={
            pctCoberto == null
              ? "tempo com leitura"
              // A janela é a de COBERTURA (`cob.janelaMs`), a mesma que gerou
              // o percentual. `m.duracaoDaJanelaMs` mede da primeira à última
              // leitura e é menor: usá-la aqui produzia frases aritmeticamente
              // impossíveis, do tipo "4m 0s · 100% de 3m 0s" (DASH-11).
              : `${pctCoberto.toFixed(0)}% de ${formatarDuracao(cob.janelaMs)}`
          }
          icone={Clock}
          corDoIcone="text-blue-400"
        />
        <CardMetrica
          rotulo="Maior pausa"
          valor={formatarDuracao(m.maiorPeriodoSemMovimentoMs)}
          // "registrado", e não "houve": a afirmação é sobre o registro do
          // aparelho, não sobre o mundo. Dentro de uma captação o aparelho
          // esteve operando e não registrou movimento; a pausa nunca
          // atravessa uma interrupção, que é o defeito do DASH-09.
          detalhe="sem movimento registrado, na captação"
          icone={Pause}
          corDoIcone="text-indigo-400"
        />
        <CardMetrica
          rotulo="Intensidade"
          valor={m.intensidadeMedia == null ? null : m.intensidadeMedia.toFixed(2)}
          unidade="m/s²"
          detalhe={`média do repouso · limiar ${LIMIAR_DE_MOVIMENTO.toFixed(1).replace(".", ",")}`}
          icone={Waves}
          corDoIcone="text-primary"
        />
      </div>

      {/* Fora do aviso de lacuna de propósito: numa captação de ESP32 com
          cobertura perfeita — justamente onde TUDO é inferido — não há aviso
          de lacuna, e a inferência não aparecia em lugar nenhum da tela. */}
      <NotaDeInferencia cobertura={cob} />

      {/* Depois dos números, e não antes. A revisão apontou que quem abre o
          painel lia dois parágrafos de ressalva antes de ver qualquer dado —
          continua na tela, e em qualquer captura dela, mas não na frente. */}
      <NotaDeEscopo />

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
            <span className="flex items-center gap-1.5">
              {/* Tracejada, como a linha do grafico. */}
              <span
                className="w-3 inline-block border-t-2 border-dashed"
                style={{ borderColor: COR_MOVIMENTO }}
              />
              Limiar {LIMIAR_DE_MOVIMENTO.toFixed(1).replace(".", ",")}
            </span>
            {temLacuna && (
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-sm inline-block bg-muted-foreground/25" />
                Sem dados
              </span>
            )}
          </div>
        </div>
        <div className="h-44 sm:h-56">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={serieComLacuna} margin={{ top: 4, right: 4, left: -12, bottom: 0 }}>
              <XAxis
                dataKey="hora"
                axisLine={false}
                tickLine={false}
                tick={{ fill: "var(--muted-foreground)", fontSize: 11, fontFamily: "Outfit" }}
                minTickGap={24}
              />
              {/* `width` explícito porque o padrão do recharts é 60px, que num
                  gráfico de ~310px no celular consome um quinto da área útil.
                  Mas 32px era estreito demais: com um evento de 20 m/s², os
                  rótulos viravam "l.0" e ".0" — cortados ao meio. 40px cabe
                  dois dígitos, e o formato larga a casa decimal acima de 10,
                  onde ela não informa nada. */}
              <YAxis
                width={40}
                tickCount={4}
                axisLine={false}
                tickLine={false}
                tick={{ fill: "var(--muted-foreground)", fontSize: 11, fontFamily: "Outfit" }}
                tickFormatter={(v: number) => (v >= 10 ? v.toFixed(0) : v.toFixed(1))}
              />
              <Tooltip
                content={<TooltipDoGrafico />}
                cursor={{ fill: "var(--secondary)", fillOpacity: 0.5 }}
              />
              {/* A fronteira da decisao, desenhada (DASH-07).
                  Sem ela o grafico engana: numa captacao so de repouso o eixo
                  se ajusta ao maior valor, as barras enchem a altura toda e
                  parece muito movimento — quando na verdade nada chegou perto
                  do limiar. Foi exatamente o que aconteceu na primeira coleta
                  com hardware real, em 2026-08-24.
                  O tracado da landing ja mostrava a faixa de limiar; aqui,
                  onde o dado e real, ela importa mais.
                  `ifOverflow="extendDomain"` garante que a linha apareca
                  mesmo quando todos os pontos ficam abaixo dela. */}
              <ReferenceLine
                y={LIMIAR_DE_MOVIMENTO}
                ifOverflow="extendDomain"
                stroke={COR_MOVIMENTO}
                strokeDasharray="5 4"
                strokeWidth={1.5}
              />
              {/* A lacuna vira uma coluna cinza de altura cheia. O eixo é
                  categórico — cada leitura ocupa a mesma largura — então um
                  buraco de duas horas ficava visualmente idêntico a dez
                  segundos. Sem esta coluna, a tela não mostrava que a coleta
                  tinha caído (DASH-09). */}
              {temLacuna && (
                <Bar
                  dataKey="alturaDaLacuna"
                  radius={[3, 3, 0, 0]}
                  isAnimationActive={false}
                  fill="var(--muted-foreground)"
                  fillOpacity={0.18}
                />
              )}
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
            Proporção do <strong className="font-semibold">tempo medido</strong> — não da
            contagem de leituras
          </p>

          {pctMovimento == null ? (
            <p className="text-sm text-muted-foreground">
              Sem medição suficiente para calcular proporção.
            </p>
          ) : (
            <div className="space-y-4">
              <Barra
                rotulo="Repouso"
                detalhe={formatarDuracao(cob.tempoCobertoMs * (1 - m.fracaoEmMovimento!))}
                porcentagem={100 - pctMovimento}
                cor={COR_REPOUSO}
              />
              <Barra
                rotulo="Movimento"
                detalhe={formatarDuracao(cob.tempoCobertoMs * m.fracaoEmMovimento!)}
                porcentagem={pctMovimento}
                cor={COR_MOVIMENTO}
              />
            </div>
          )}

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
                  {temMedidaDeTemperatura && (
                    <th className="text-right font-medium pb-2">Temp. chip</th>
                  )}
                  <th className="text-right font-medium pb-2">Estado</th>
                </tr>
              </thead>
              <tbody>
                {maisRecentes.map((leitura, i) => {
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
                      {temMedidaDeTemperatura && (
                        <td className="py-2.5 text-right text-muted-foreground">
                          {leitura.temp == null ? "--" : `${leitura.temp.toFixed(1)}°C`}
                        </td>
                      )}
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
            Cada linha é uma leitura, na ordem em que chegou.
          </p>
        </div>
      </div>
    </div>
  );
}

function Cabecalho({
  periodo,
  instrumento,
  acao,
}: {
  periodo?: string;
  /** Qual dispositivo produziu a serie. So aparece quando ha mais de um —
   *  com um so, dizer o nome nao informa nada. */
  instrumento?: string;
  acao?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0">
        <p className="text-xs text-muted-foreground uppercase tracking-wider">
          {periodo ?? "Monitoramento"}
          {instrumento ? ` · ${instrumento}` : ""}
        </p>
        <h1 className="text-xl sm:text-2xl font-semibold text-foreground mt-1">
          Movimento durante o repouso
        </h1>
      </div>
      {acao}
    </div>
  );
}

/** Uma proporção do tempo medido. `detalhe` traz a duração correspondente —
 *  percentual sozinho não diz se são dez minutos ou seis horas. */
function Barra({
  rotulo,
  detalhe,
  porcentagem,
  cor,
}: {
  rotulo: string;
  detalhe: string;
  porcentagem: number;
  cor: string;
}) {
  return (
    <div>
      <div className="flex justify-between text-xs mb-1.5">
        <span className="text-muted-foreground">{rotulo}</span>
        <span className="text-foreground font-semibold">
          {detalhe} · {porcentagem.toFixed(0)}%
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
