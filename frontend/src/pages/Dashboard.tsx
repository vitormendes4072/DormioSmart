import { SeletorSegmentado } from "../components/SeletorSegmentado";
import { useEffect, useState, useSyncExternalStore, type ReactNode } from "react";
import { Link, useLocation } from "react-router";

import { BarraDoWorkspace } from "../components/BarraDoWorkspace";
import { CalendarioDoSono } from "../components/CalendarioDoSono";
import { GraficoDeMovimento } from "../components/GraficoDeMovimento";
import { destinoDoWorkspace } from "../components/nav";
import { Carregando, FalhaAoCarregar, SemLeituras } from "../components/EstadoDaTela";
import { NotaDeEscopo } from "../components/NotaDeEscopo";
import { ResumoDeDispositivos } from "../components/ResumoDeDispositivos";
import { ResumoDaSessao } from "../components/ResumoDaSessao";
import { AvisoDeMistura, SeletorDeDispositivo } from "../components/SeletorDeDispositivo";
import { useDispositivos } from "../hooks/useDispositivos";
import { useHistorico } from "../hooks/useHistorico";
import { useHistoricoPaginado } from "../hooks/useHistoricoPaginado";
import { LIMITE_DO_PAINEL } from "../lib/api";
import { origemDaTemperatura, descreverRecorte } from "../lib/dispositivos";
import { calcularCobertura } from "../lib/cobertura";
import { limitesDaConsulta, sessoesDoDia, somarDias } from "../lib/calendarioDoSono";
import { estaEmModoDemo } from "../lib/demo";
import {
  calcularMetricas,
  descreverQuando,
  formatarDuracao,
  formatarPorcentagem,
  formatarHora,
  prepararSerie,
  leituraNaBordaDoLimite,
} from "../lib/metricas";
import {
  GRAVIDADE,
  LIMIAR_DE_MOVIMENTO,
  ehMovimento,
  instanteDaLeitura,
  intensidade,
  type LeituraSono,
} from "../types/sleep";
import { AvisoDeLacuna, NotaDeInferencia } from "../components/AvisoDeLacuna";
import { SeletorDeSessao } from "../components/SeletorDeSessao";
import { semBancada, sessoesDaMarca } from "../lib/trecho";

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
const PERIODOS = [
  { valor: "Sessão toda", rotulo: "Sessão toda" },
  { valor: "1ª metade", rotulo: "1ª metade" },
  { valor: "2ª metade", rotulo: "2ª metade" },
] as const;
type Periodo = typeof PERIODOS[number]["valor"];
const DATA_DO_DIA = new Intl.DateTimeFormat("pt-BR", { weekday: "long", day: "numeric", month: "long" });
const CARTAO = "rounded-2xl border border-border bg-card p-4 shadow-sm sm:p-5";
const LINK_DO_CARTAO = "inline-flex min-h-9 items-center justify-center rounded-lg border border-border px-3 py-2 text-center text-sm font-semibold text-primary hover:bg-secondary focus-visible:outline-2 focus-visible:outline-ring";

// UI-48: a partir desta largura o Início tem duas colunas, e o gráfico de tempo por dia vai para a
// coluna da direita, logo abaixo do calendário. Abaixo dela, fica dentro do cartão do calendário.
const TELA_LARGA = "(min-width: 1050px)";

function observarTelaLarga(atualizar: () => void) {
  const midia = window.matchMedia?.(TELA_LARGA);
  midia?.addEventListener("change", atualizar);
  return () => midia?.removeEventListener("change", atualizar);
}

function ehTelaLarga() {
  return window.matchMedia?.(TELA_LARGA).matches ?? false;
}

export function Dashboard() {
  const { hash, key, search } = useLocation();
  // `null` = todos os dispositivos. O recorte por instrumento (DASH-05) e
  // opcional: sem ele o painel se comporta como antes.
  const [dispositivo, setDispositivo] = useState<string | null>(null);
  const [diaSelecionado, setDiaSelecionado] = useState<Date | null>(null);
  const [ancoraDoCalendario, setAncoraDoCalendario] = useState(() => somarDias(new Date(), 0));
  const telaLarga = useSyncExternalStore(observarTelaLarga, ehTelaLarga, () => false);
  const [vagaDoGrafico, setVagaDoGrafico] = useState<HTMLElement | null>(null);
  const [verTudo, setVerTudo] = useState(false);
  const [periodo, setPeriodo] = useState<Periodo>("Sessão toda");
  const dispositivos = useDispositivos();
  const pausados = dispositivos.filter((d) => !d.revoked_at && d.receber_leituras === false);
  const avisoDePausa = pausados.length > 0 && (
    <p role="status" className="rounded-xl border border-destructive/30 p-3 text-sm text-destructive">
      <strong>Pausado:</strong> {pausados.map((d) => d.nome).join(", ")}. Registros recebidos durante a pausa são descartados.
    </p>
  );
  // `limite` explicito (DASH-13): sem ele o backend devolve 20 linhas — dez
  // minutos de celular —, e todo o recorte por sessao operava sobre isso
  // enquanto a tela dizia descrever a captação inteira.
  const recentes = useHistorico({ dispositivo, limite: LIMITE_DO_PAINEL });
  const demo = import.meta.env.DEV && estaEmModoDemo(search);
  const historicoDoDia = useHistoricoPaginado(
    diaSelecionado && limitesDaConsulta(diaSelecionado, diaSelecionado), dispositivo, demo,
  );
  const { carregando, erro, recarregar } = diaSelecionado ? historicoDoDia : recentes;
  const recebidas = diaSelecionado ? historicoDoDia.dados?.leituras ?? [] : recentes.leituras;
  const sessoesSelecionadas = diaSelecionado ? sessoesDoDia(recebidas, diaSelecionado) : null;
  // DATA-16: as coletas de bancada não entram no painel.
  const leituras = sessoesSelecionadas?.flatMap((sessao) => sessao.leituras) ?? semBancada(recebidas);
  const historicoParcial = diaSelecionado !== null && historicoDoDia.dados?.truncada;
  const tituloDoDia = diaSelecionado ? `Sessões de ${DATA_DO_DIA.format(diaSelecionado)}` : undefined;

  useEffect(() => {
    if (!carregando && hash) {
      document.getElementById(hash.slice(1))?.scrollIntoView();
    }
  }, [carregando, hash, key]);

  const instrumento = dispositivos.length === 1 && dispositivo === null
    ? descreverRecorte(dispositivos, dispositivos[0].id)
    : descreverRecorte(dispositivos, dispositivo);

  function selecionarDispositivo(id: string | null) {
    setDispositivo(id);
    if (diaSelecionado) setVerTudo(false);
    setPeriodo("Sessão toda");
  }

  function selecionarDia(dia: Date | null) {
    setDiaSelecionado(dia);
    setVerTudo(false);
    setPeriodo("Sessão toda");
  }

  const seletor = (
    <SeletorDeDispositivo
      dispositivos={dispositivos}
      selecionado={dispositivo}
      aoSelecionar={selecionarDispositivo}
    />
  );
  const resumoDeDispositivos = (
    <ResumoDeDispositivos
      dispositivos={dispositivos}
      selecionado={dispositivo}
      aoSelecionar={selecionarDispositivo}
      destinoGerenciar={destinoDoWorkspace("/dispositivos", search)}
      className={CARTAO}
      classeDoLink={LINK_DO_CARTAO}
    />
  );
  const calendario = (
    <CalendarioDoSono dispositivo={dispositivo} demo={demo} selecionado={diaSelecionado} aoSelecionarDia={selecionarDia}
      ancora={ancoraDoCalendario} aoNavegar={setAncoraDoCalendario} destinoDoGrafico={telaLarga ? vagaDoGrafico : null} />
  );
  // Onde o gráfico entra em tela larga. Esticado (`*:flex-1`), ele acompanha a altura do que está
  // ao lado.
  const espacoDoGrafico = telaLarga
    ? <div ref={setVagaDoGrafico} data-vaga-do-grafico className="flex min-w-0 *:flex-1" />
    : null;
  // Nos estados sem sessão (carregando, erro, dia vazio) a coluna da direita começa pelo gráfico,
  // na altura do primeiro cartão. Com sessão, ele fica ao lado dos cartões do resumo (ver abaixo).
  // `esticar`: o conteúdo é um cartão só, que acompanha a altura do gráfico (e vice-versa).
  const comColunaDoGrafico = (conteudo: ReactNode, esticar = false) => telaLarga ? (
    <div className={`grid grid-cols-[minmax(0,1.8fr)_minmax(220px,0.9fr)] gap-3.5 ${esticar ? "" : "items-start"}`}>
      <div className={`min-w-0 space-y-3.5 ${esticar ? "flex flex-col *:flex-1" : ""}`}>{conteudo}</div>
      {espacoDoGrafico}
    </div>
  ) : conteudo;
  const linkHistorico = (
    <Link to={destinoDoWorkspace("/historico", search)} className={LINK_DO_CARTAO}>Ver histórico</Link>
  );
  const avisoHistoricoParcial = historicoParcial && (
    <p role="status" className="rounded-xl border border-border px-3 py-3 text-sm text-muted-foreground">
      Histórico parcial. Parte dos registros do período ficou fora da consulta.
    </p>
  );

  // O seletor aparece tambem nos tres estados iniciais: se o dispositivo
  // escolhido nao tem leitura, e preciso poder trocar sem sair da tela.
  if (carregando) {
    return (
      <div className="space-y-6">
        <Cabecalho acao={seletor} calendario={calendario} instrumento={instrumento} titulo={tituloDoDia} telaLarga={telaLarga} />
        {comColunaDoGrafico(<>
          {avisoDePausa}
          <Carregando mensagem={diaSelecionado ? "Carregando registros do dia..." : undefined} />
          {diaSelecionado && linkHistorico}
        </>)}
      </div>
    );
  }

  if (erro) {
    return (
      <div className="space-y-6">
        <Cabecalho acao={seletor} calendario={calendario} instrumento={instrumento} titulo={tituloDoDia} telaLarga={telaLarga} />
        {comColunaDoGrafico(<>
          {avisoDePausa}
          <FalhaAoCarregar mensagem={erro} aoTentarNovamente={recarregar} />
          {diaSelecionado && linkHistorico}
        </>)}
      </div>
    );
  }

  if (leituras.length === 0) {
    return (
      <div className="space-y-6">
        <Cabecalho acao={seletor} calendario={calendario} instrumento={instrumento} titulo={tituloDoDia} telaLarga={telaLarga} />
        {avisoDePausa}
        <NotaDeEscopo />
        {comColunaDoGrafico(
          <div id="sessoes-recentes">
            {diaSelecionado ? (
              <div className={`${CARTAO} h-full`}>
                {avisoHistoricoParcial}
                <p className="py-5 text-sm font-medium" role="status">
                  {historicoParcial ? "Sem registros do dia entre os dados carregados" : "Sem registros neste dia"}
                </p>
                {linkHistorico}
              </div>
            ) : <SemLeituras />}
          </div>,
          true,
        )}
        {resumoDeDispositivos}
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
  //
  // UI-38: recebe também a bancada, para cortar onde ela está. Sem o corte, a
  // bancada marcada no meio apareceria como pausa do aparelho.
  const sessoes = sessoesSelecionadas ?? sessoesDaMarca(recebidas, false);
  // UI-40: a última está no resumo; a lista é do que veio antes dela.
  const sessoesAnteriores = sessoes.slice(0, -1).slice(-3).reverse();
  const ultima = sessoes.length > 0 ? sessoes[sessoes.length - 1] : null;
  const leiturasVisiveis = verTudo || ultima === null ? leituras : ultima.leituras;

  const borda = diaSelecionado ? undefined : leituraNaBordaDoLimite(recebidas, LIMITE_DO_PAINEL);
  const recorteParcial = borda !== undefined && leiturasVisiveis.includes(borda);
  const m = calcularMetricas(leiturasVisiveis);
  const podeRecortar = !verTudo && ultima !== null && m.totalLeituras > 1;
  const meio = podeRecortar ? ultima.inicio + (ultima.fim - ultima.inicio) / 2 : null;
  const recorteDoGrafico = meio === null || periodo === "Sessão toda"
    ? undefined
    : periodo === "1ª metade" ? { fim: meio } : { inicio: meio };
  const serie = prepararSerie(leiturasVisiveis, m.cobertura, recorteDoGrafico);
  const temLacuna = serie.some((p) => p.lacuna);
  // Por TEMPO MEDIDO, e não por contagem de amostra (DASH-09). Com
  // amostragem irregular, "9 eventos em 20 leituras = 45%" não significava
  // nada: as 20 leituras podiam cobrir três minutos de uma janela de duas
  // horas.
  const pctMovimento = m.fracaoEmMovimento == null ? null : m.fracaoEmMovimento * 100;
  const cob = m.cobertura;
  const pctCoberto =
    cob.janelaMs > 0 ? (cob.tempoCobertoMs / cob.janelaMs) * 100 : null;
  // O aviso acompanha os pontos do gráfico, inclusive ao mostrar uma metade da sessão.
  const aparelhosDoGrafico = new Set<string>();
  for (const leitura of leiturasVisiveis) {
    const instante = Date.parse(instanteDaLeitura(leitura));
    if (
      leitura.device_id && Number.isFinite(instante)
      && instante >= (recorteDoGrafico?.inicio ?? -Infinity)
      && instante < (recorteDoGrafico?.fim ?? Infinity)
    ) {
      aparelhosDoGrafico.add(leitura.device_id);
    }
  }
  const dispositivosDoGrafico = dispositivos.filter(({ id }) => aparelhosDoGrafico.has(id));
  const leiturasFora = leituras.length - leiturasVisiveis.length;
  const aparelhosVisiveis = new Set(leiturasVisiveis.map((l) => l.device_id));
  const aparelhoDaSessao = aparelhosVisiveis.size === 1
    ? dispositivos.find((item) => aparelhosVisiveis.has(item.id))
    : undefined;
  const aparelhoDoResumo = aparelhoDaSessao?.nome
    ?? (aparelhosVisiveis.size > 1 ? "Todos os dispositivos" : instrumento);
  // A tabela promete "da mais recente para a mais antiga". A API devolve
  // assim, mas o agrupamento reordena crescente para poder recortar — no
  // modo padrão a tabela mostrava as MAIS ANTIGAS sob o rótulo contrário, e a
  // ordem virava sozinha ao clicar "Ver todas" (DASH-11). Ordenar aqui deixa a
  // promessa valer nos dois modos.
  // Instante da MEDICAO, com fallback para o da chegada (DASH-12) — a mesma
  // base do resto da tela. Com bases diferentes, a tabela podia listar numa
  // ordem e o gráfico ao lado desenhar noutra.
  const instanteDe = (l: LeituraSono) => {
    const quando = instanteDaLeitura(l);
    return quando === "" ? NaN : new Date(quando).getTime();
  };
  const maisRecentes = [...leiturasVisiveis]
    .filter((l) => !Number.isNaN(instanteDe(l)))
    .sort((a, b) => instanteDe(b) - instanteDe(a))
    .slice(0, 8);

  return (
    <div className="mx-auto max-w-[1540px] space-y-3.5">
      <Cabecalho
        instrumento={instrumento}
        acao={seletor}
        calendario={calendario}
        telaLarga={telaLarga}
        titulo={tituloDoDia}
        // Em tela estreita o título fica no resumo, logo acima dos cartões; em tela larga, no topo.
        mostrarTitulo={false}
        // UI-49: o aviso é consequência do filtro ("Todos os dispositivos"), então fica junto dele.
        aviso={aparelhosDoGrafico.size > 1 && <AvisoDeMistura dispositivos={dispositivosDoGrafico} />}
      />
      {avisoDePausa}

      {/* A coleta teve buracos? Isso precisa aparecer ANTES dos números, e
          não depois — porque é o que decide se eles significam algo. */}
      {recorteParcial && (
        <p role="status" className="rounded-xl border border-border px-3 py-3 text-sm text-muted-foreground">
          Período incompleto: só os registros mais recentes foram carregados.
        </p>
      )}
      {avisoHistoricoParcial}
      <AvisoDeLacuna cobertura={cob} />

      <ResumoDaSessao
        sessoes={verTudo || ultima === null ? sessoes : [ultima]}
        verTudo={verTudo}
        metricas={m}
        titulo={tituloDoDia}
        idDoTitulo={telaLarga ? ID_DO_TITULO : undefined}
        // UI-48: em tela larga, o gráfico de tempo por dia fica na mesma linha dos cartões,
        // alinhado no topo e na base com eles.
        lateral={espacoDoGrafico}
      >
        {/* O recorte, e como sair dele. */}
        {sessoes.length > 1 && (
          <SeletorDeSessao
            total={sessoes.length}
            verTudo={verTudo}
            aoAlternar={() => {
              setVerTudo((v) => !v);
              setPeriodo("Sessão toda");
            }}
          />
        )}
      </ResumoDaSessao>

      <div className="grid gap-3.5 min-[1050px]:grid-cols-[minmax(0,1.8fr)_minmax(220px,0.9fr)]">
        <figure aria-labelledby="titulo-linha-do-tempo" className={`min-w-0 ${CARTAO}`}>
          <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 id="titulo-linha-do-tempo" className="text-base font-semibold text-foreground">Movimento ao longo do tempo</h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                Intensidade do movimento
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted-foreground">
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-sm inline-block" style={{ background: COR_REPOUSO }} />
                Intensidade
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-sm inline-block" style={{ background: COR_MOVIMENTO }} />
                Com movimento
              </span>
              <span className="flex items-center gap-1.5">
                {/* Tracejada, como a linha do grafico. O valor esta nos detalhes; a
                    linha fica, porque sem ela o grafico engana (DASH-07). */}
                <span
                  className="w-3 inline-block border-t-2 border-dashed"
                  style={{ borderColor: COR_MOVIMENTO }}
                />
                Limite de movimento
              </span>
              {temLacuna && (
                <span className="flex items-center gap-1.5">
                  <span className="inline-block size-3 rounded-sm border border-muted-foreground/40 bg-[repeating-linear-gradient(135deg,transparent_0_2px,currentColor_2px_3px)]" />
                  Sem registro
                </span>
              )}
            </div>
          </div>
          {podeRecortar && (
            <div className="mb-4">
              <SeletorSegmentado rotulo="Período do gráfico" opcoes={PERIODOS} selecionado={periodo} aoSelecionar={setPeriodo} />
            </div>
          )}
          <div className="h-40 sm:h-64">
            {/* Desenhado à mão desde o UI-43 (etapa 1): o mesmo gráfico, sem o recharts. A linha
                do limite segue sempre visível (DASH-07), e a lacuna, hachurada (DASH-09). */}
            {serie.length > 0
              ? <GraficoDeMovimento key={periodo} serie={serie} limite={LIMIAR_DE_MOVIMENTO} />
              : <p className="text-sm text-muted-foreground">Sem registros no período.</p>}
          </div>
          {temLacuna && (
            <figcaption className="mt-3 text-xs text-muted-foreground">
              As faixas hachuradas são trechos sem registro. A largura da faixa
              não representa quanto tempo ele durou.
            </figcaption>
          )}
        </figure>
        {resumoDeDispositivos}
      </div>

      {/* Fora do aviso de lacuna de propósito: numa captação de ESP32 com
          cobertura perfeita — justamente onde TUDO é inferido — não há aviso
          de lacuna, e a inferência não aparecia em lugar nenhum da tela. */}
      <NotaDeInferencia cobertura={cob} />

      {diaSelecionado ? (
        <div id="sessoes-recentes">{linkHistorico}</div>
      ) : (
        <section aria-labelledby="sessoes-recentes" className={CARTAO}>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 id="sessoes-recentes" className="text-base font-extrabold tracking-tight text-foreground">Sessões anteriores</h2>
            {linkHistorico}
          </div>
          {sessoesAnteriores.length === 0 ? (
            <p className="mt-2 text-sm text-muted-foreground">Nenhuma sessão anterior nos registros carregados.</p>
          ) : (
            <table className="mt-3 w-full text-left text-sm">
              <thead className="border-b border-border text-xs text-muted-foreground">
                <tr>
                  <th scope="col" className="pb-2 pr-3">Quando</th>
                  <th scope="col" className="pb-2">Registrado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {sessoesAnteriores.map((sessao) => {
                  const resumo = calcularCobertura(sessao.leituras);
                  const registrado = resumo.janelaMs > 0
                    ? `${formatarDuracao(resumo.tempoCobertoMs)} de ${formatarDuracao(resumo.janelaMs)}`
                    : "—";
                  return (
                    <tr key={sessao.inicio}>
                      <td className="py-3 pr-3">{descreverQuando(sessao.inicio, sessao.fim)}</td>
                      <td className="py-3">
                        {registrado}{borda !== undefined && sessao.leituras.includes(borda) ? " · Parcial" : ""}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </section>
      )}

      {/* UI-40: fórmula, limite, contagens e amostras. Recolhido, e por isso
          NENHUM aviso de falha entra aqui. */}
      <details className="rounded-[14px] border border-border bg-card">
        <summary className="cursor-pointer px-4 py-3 text-sm font-semibold text-foreground">
          Detalhes técnicos
        </summary>
        <div className="space-y-4 border-t border-border p-4">
          <ul className="space-y-1 text-xs text-muted-foreground">
            <li>Dispositivo no resumo: {aparelhoDoResumo}.</li>
            {leiturasFora > 0 && (
              <li>
                {leiturasFora.toLocaleString("pt-BR")} {leiturasFora === 1 ? "registro ficou" : "registros ficaram"} fora do recorte.
              </li>
            )}
            <li>
              Intensidade: |magnitude − {GRAVIDADE.toFixed(2).replace(".", ",")} m/s²|, o desvio do repouso.
            </li>
            <li>
              Limite de referência: {LIMIAR_DE_MOVIMENTO.toFixed(1).replace(".", ",")} m/s². Quem marca
              cada registro como movimento é o próprio aparelho.
            </li>
            <li>
              {m.totalLeituras} registros no período, {m.eventosDeMovimento} com movimento.
              {!verTudo && pctCoberto != null && ` Registrado: ${formatarPorcentagem(pctCoberto)} do período.`}
            </li>
            <li>O maior período sem movimento registrado não atravessa as paradas.</li>
          </ul>
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
            <div className="lg:col-span-2 bg-card border border-border rounded-2xl p-4 sm:p-6">
              <h3 className="text-sm font-semibold text-foreground">Repouso × Movimento</h3>
              <p className="text-xs text-muted-foreground mt-0.5 mb-5">
                Proporção do <strong className="font-semibold">tempo registrado</strong> — não da
                quantidade de registros
              </p>

              {pctMovimento == null ? (
                <p className="text-sm text-muted-foreground">
                  Sem registro suficiente para calcular a proporção.
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
                    <p className="text-xs text-muted-foreground mt-0.5">Primeiro registro</p>
                  </div>
                  <div className="text-center">
                    <p className="text-lg font-bold text-foreground">{formatarHora(m.janela.fim)}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">Último registro</p>
                  </div>
                </div>
              ) : null}
            </div>

            <div className="lg:col-span-3 bg-card border border-border rounded-2xl p-4 sm:p-6">
              <div className="mb-5">
                <h3 className="text-sm font-semibold text-foreground">Registros recentes</h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Um por linha, do mais recente para o mais antigo
                </p>
              </div>

              <div className="overflow-x-auto -mx-4 sm:mx-0 px-4 sm:px-0">
                <table className="w-full text-sm min-w-[22rem]">
                  <thead>
                    <tr className="text-xs text-muted-foreground uppercase tracking-wider">
                      <th className="text-left font-medium pb-2">Hora</th>
                      <th className="text-right font-medium pb-2">Intensidade</th>
                      <th className="text-right font-medium pb-2">Temperatura</th>
                      <th className="text-right font-medium pb-2">Estado</th>
                    </tr>
                  </thead>
                  <tbody>
                    {maisRecentes.map((leitura, i) => {
                      const valor = intensidade(leitura);
                      const movimento = ehMovimento(leitura.status);
                      const instante = new Date(instanteDaLeitura(leitura));
                      const origem = origemDaTemperatura(dispositivos.find((item) => item.id === leitura.device_id)?.tipo);
                      return (
                        <tr key={i} className="border-t border-border">
                          <td className="py-2.5 text-foreground">
                            {Number.isNaN(instante.getTime()) ? "--" : formatarHora(instante)}
                          </td>
                          <td className="py-2.5 text-right font-mono text-muted-foreground">
                            {valor == null ? "--" : valor.toFixed(2)}
                          </td>
                          <td className="py-2.5 text-right text-muted-foreground">
                            {leitura.temp == null ? "--" : (
                              <>
                                {`${leitura.temp.toFixed(1)}°C`}
                                <span className="block text-xs">{origem ?? "Origem desconhecida"}</span>
                              </>
                            )}
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
                Registros da medição mais recente à mais antiga. Sem horário de medição, vale o horário de chegada.
              </p>
            </div>
          </div>
        </div>
      </details>

      {/* Por último e fora dos detalhes (UI-40): depois dos números, e não
          antes. A revisão apontou que quem abre o painel lia dois parágrafos
          de ressalva antes de ver qualquer dado — continua na tela, e em
          qualquer captura dela, mas não na frente. */}
      <NotaDeEscopo />
    </div>
  );
}

const ID_DO_TITULO = "titulo-do-inicio";

function Cabecalho({
  instrumento,
  acao,
  calendario,
  telaLarga,
  aviso,
  mostrarTitulo = true,
  titulo = "Seus registros",
}: {
  instrumento: string;
  acao?: ReactNode;
  calendario: ReactNode;
  telaLarga: boolean;
  /** O aviso de mistura de aparelhos, que acompanha o seletor. */
  aviso?: ReactNode;
  /** Só em tela estreita: em tela larga o título está sempre no topo. */
  mostrarTitulo?: boolean;
  titulo?: string;
}) {
  const cabecalho = (
    <>
      <h1 id={ID_DO_TITULO} className="text-2xl font-extrabold tracking-tight text-foreground sm:text-[27px]">
        {titulo}
      </h1>
      <p className="sr-only">{instrumento}</p>
    </>
  );

  // UI-49: em tela larga o topo usa as mesmas duas colunas do resto do Início. À esquerda, o título
  // em cima e o filtro embaixo; à direita, o calendário, na largura do gráfico que vem abaixo dele.
  // Aberto, o calendário ocupa as duas colunas (ver `CalendarioDoSono`).
  if (telaLarga) {
    return (
      <header>
        <BarraDoWorkspace secao="Visão geral" />
        <div data-topo-do-inicio className="grid grid-cols-[minmax(0,1.8fr)_minmax(220px,0.9fr)] gap-x-3.5 gap-y-3">
          <div className="flex min-w-0 flex-col justify-between gap-3">
            <div className="min-w-0">{cabecalho}</div>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
              {acao}
              {aviso}
            </div>
          </div>
          {calendario}
        </div>
      </header>
    );
  }

  return (
    <header>
      <BarraDoWorkspace secao="Visão geral" />
      <div className="flex flex-wrap items-start gap-x-4 gap-y-2">
        {acao}
        {aviso && <div className="w-full">{aviso}</div>}
        {calendario}
      </div>
      {mostrarTitulo && <div className="mt-3 min-w-0">{cabecalho}</div>}
    </header>
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
          {detalhe} · {formatarPorcentagem(porcentagem)}
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
