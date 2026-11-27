import { MensagemDeFalha } from "../components/MensagemDeFalha";
import { useEffect, useMemo, useRef, useState, useSyncExternalStore, type ReactNode } from "react";
import { Link, useLocation } from "react-router";

import { BarraDoWorkspace } from "../components/BarraDoWorkspace";
import { CartaoDeMetrica, EtiquetaDeRegistro } from "../components/CartoesDeRegistro";
import { FaixaDaSessao } from "../components/FaixaDaSessao";
import { MenuDaSessao } from "../components/MenuDaSessao";
import { MiniGraficoDaSessao } from "../components/MiniGraficoDaSessao";
import { ResumoDoPeriodo } from "../components/ResumoDoPeriodo";
import { SeletorDeDispositivo } from "../components/SeletorDeDispositivo";
import { useDispositivos } from "../hooks/useDispositivos";
import { Carregando, FalhaAoCarregar } from "../components/EstadoDaTela";
import { SeletorSegmentado } from "../components/SeletorSegmentado";
import { apagarSessao, buscarJanelaDoHistorico, ErroApi, marcarSessao, MAX_PAGINAS_DO_HISTORICO } from "../lib/api";
import { calcularCobertura, type Trecho as TrechoComRegistro } from "../lib/cobertura";
import { marcasDaRegua, reguaDoHorario } from "../lib/faixaDaSessao";
import { estaEmModoDemo } from "../lib/demo";
import { destinoDoDia } from "../lib/diaNoEndereco";
import { precisaEscolherDispositivo, rotuloDoTipo, type Dispositivo } from "../lib/dispositivos";
import { calcularMetricas, formatarDuracao, formatarPorcentagem, prepararSerie, type PontoDaSerie } from "../lib/metricas";
import { ehBancada, sessoesDaMarca, trechoDaSessao, type Trecho } from "../lib/trecho";
import { ehMovimento, instanteDaLeitura, type LeituraSono } from "../types/sleep";

const TELA_ESTREITA = "(max-width: 767px)";
/** No computador, a lista fica num cartão; no celular, os cartões já são das sessões. */
const CARTAO_DA_LISTA = "md:rounded-2xl md:border md:border-border md:bg-card md:p-4 md:shadow-sm";

/** UI-52: tocar numa barra do gráfico leva à sessão na lista. */
function irParaSessao(chave: string) {
  const alvo = document.getElementById(idDaSessao(chave));
  if (!alvo) return;
  alvo.scrollIntoView({ block: "center" });
  alvo.focus({ preventScroll: true });
}

function idDaSessao(chave: string) {
  return `sessao-${chave}`;
}

function observarLargura(atualizar: () => void) {
  const midia = window.matchMedia?.(TELA_ESTREITA);
  midia?.addEventListener("change", atualizar);
  return () => midia?.removeEventListener("change", atualizar);
}

function telaEstreita() {
  return window.matchMedia?.(TELA_ESTREITA).matches ?? false;
}

const DIA_MS = 24 * 60 * 60 * 1000;
const JANELAS = [
  { valor: 1, rotulo: "Últimas 24 horas" },
  { valor: 7, rotulo: "Últimos 7 dias" },
  { valor: 30, rotulo: "Últimos 30 dias" },
];
const DATA = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit", month: "short", year: "numeric",
});
const DATA_E_HORA = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
});

type Linha = {
  chave: string;
  /** UI-55: o aparelho que gravou a sessão; `null` nas leituras sem aparelho. */
  aparelho?: string | null;
  inicio: number;
  fim: number;
  tempo: number;
  /** Do início ao fim, com os trechos sem registro; `null` se não dá para calcular. */
  periodo: number | null;
  leituras: number;
  lacunas: boolean;
  /** O aparelho parou. Sem isto, trecho sem registro não é pausa (UI-39). */
  pausas: boolean;
  parcial?: boolean;
  /** Aparelho e instantes da sessão, para excluir ou marcar (DATA-16). Ausente
   *  nos exemplos e nas leituras sem aparelho. */
  trecho?: Trecho | null;
  /** A sessão foi marcada como bancada/teste. */
  bancada?: boolean;
  /** UI-53: os trechos com registro e os instantes com movimento, para a faixa. */
  trechos?: TrechoComRegistro[];
  movimentos?: number[];
  /** UI-53: o gráfico de movimento do cartão no celular. */
  serie?: PontoDaSerie[];
  /** Fração do tempo registrado com movimento, a mesma conta do Início; `null` sem registro suficiente. */
  movimento?: number | null;
};

const SESSOES_DO_PROTOTIPO: Array<[number, number, number, number, number, number, boolean]> = [
  [2026, 11, 3, 434, 100, 18, false],
  [2026, 11, 2, 408, 90, 24, true],
  [2026, 11, 1, 422, 98, 15, false],
  [2026, 10, 31, 395, 87, 21, true],
  [2026, 10, 30, 461, 100, 13, false],
];

const EXEMPLOS: Linha[] = SESSOES_DO_PROTOTIPO.map(([ano, mes, dia, minutos, cobertura, leituras, pausas]) => {
  const inicio = new Date(ano, mes - 1, dia, 22).getTime();
  const periodo = (minutos * 60_000 * 100) / cobertura;
  const fim = inicio + periodo;
  // Nos exemplos, a falta de registro fica no meio da sessão, e o movimento, espalhado.
  const falta = periodo - minutos * 60_000;
  const meio = inicio + periodo / 2;
  return {
    chave: String(inicio), inicio, fim, tempo: minutos * 60_000, periodo, leituras,
    lacunas: cobertura < 100, pausas, aparelho: "demo-travesseiro",
    trechos: falta > 0 ? [{ inicio, fim: meio - falta / 2 }, { inicio: meio + falta / 2, fim }] : [{ inicio, fim }],
    movimentos: Array.from({ length: 6 }, (_, i) => inicio + periodo * ((i * 0.37 + 0.08) % 1)),
    movimento: 0.03 + (dia % 4) / 100,
    serie: serieDeExemplo(dia, falta > 0),
  };
});

/** A série do gráfico do cartão nos exemplos: determinística, com a falta no meio. */
function serieDeExemplo(semente: number, comFalta: boolean): PontoDaSerie[] {
  return Array.from({ length: 48 }, (_, i) => {
    if (comFalta && i === 24) return { hora: "sem dados", intensidade: null, movimento: false, lacuna: true };
    const pico = (i * 7 + semente * 3) % 11 === 0;
    const intensidade = pico ? 1.4 + ((i + semente) % 3) * 0.3 : 0.15 + ((i * 13 + semente) % 7) / 20;
    return { hora: `${String((22 + Math.floor(i / 6)) % 24).padStart(2, "0")}:${String((i % 6) * 10).padStart(2, "0")}`, intensidade, movimento: pico, lacuna: false };
  });
}

function resumirSessoes(leituras: LeituraSono[], desdeMs: number, truncada: boolean): Linha[] {
  const borda = truncada ? leituras.at(-1) : undefined;
  // UI-38: separar as marcas preserva os limites da sessão antes da
  // conferência de identidade no servidor (DATA-17).
  const porAparelho = new Map<string | null, LeituraSono[]>();
  for (const leitura of leituras) {
    // A API recorta pela chegada. Exclui medições antigas enviadas com atraso.
    if (!(Date.parse(instanteDaLeitura(leitura)) >= desdeMs)) continue;
    const id = leitura.device_id ?? null;
    const grupo = porAparelho.get(id);
    if (grupo) grupo.push(leitura);
    else porAparelho.set(id, [leitura]);
  }

  return Array.from(porAparelho, ([id, grupo]) => [false, true].flatMap((bancada) =>
    sessoesDaMarca(grupo, bancada).map((sessao, i) => {
      const cobertura = calcularCobertura(sessao.leituras);
      return {
        aparelho: id,
        trechos: cobertura.trechos,
        movimentos: sessao.leituras.filter((leitura) => ehMovimento(leitura.status))
          .map((leitura) => Date.parse(instanteDaLeitura(leitura))).filter(Number.isFinite),
        serie: prepararSerie(sessao.leituras, cobertura),
        movimento: calcularMetricas(sessao.leituras).fracaoEmMovimento,
        chave: `${id ?? "sem-dispositivo"}:${bancada ? "bancada" : "normal"}:${sessao.inicio}:${i}`,
        trecho: trechoDaSessao(sessao.leituras, grupo),
        bancada,
        inicio: sessao.inicio,
        fim: sessao.fim,
        tempo: cobertura.tempoCobertoMs,
        periodo: cobertura.janelaMs > 0 ? cobertura.janelaMs : null,
        leituras: sessao.leituras.length,
        lacunas: cobertura.lacunas.length > 0,
        pausas: cobertura.interrupcoes.length > 0,
        parcial: borda !== undefined && sessao.leituras.includes(borda),
      };
    }),
  )).flat().sort((a, b) => b.inicio - a.inicio);
}

const CHAVE_DO_APARELHO = "dormio-historico-aparelho";

/** UI-55: o aparelho escolhido no Histórico fica para a próxima visita (como a barra lateral). */
function lerAparelhoGuardado() {
  try {
    return window.localStorage.getItem(CHAVE_DO_APARELHO);
  } catch {
    return null;
  }
}

function guardarAparelho(id: string | null) {
  try {
    if (id) window.localStorage.setItem(CHAVE_DO_APARELHO, id);
    else window.localStorage.removeItem(CHAVE_DO_APARELHO);
  } catch {
    // Sem armazenamento (navegação privada): a escolha vale só nesta visita.
  }
}

export function Historico() {
  const { search } = useLocation();
  const demo = estaEmModoDemo(search);
  const [dias, setDias] = useState(7);
  const dispositivos = useDispositivos();
  const [guardado, setGuardado] = useState(lerAparelhoGuardado);
  // Um aparelho guardado que não está mais na conta (excluído) vale como "Todos".
  const aparelho = guardado && dispositivos.some((d) => d.id === guardado) ? guardado : null;
  const escolherAparelho = (id: string | null) => {
    setGuardado(id);
    guardarAparelho(id);
  };

  return (
    <div className="mx-auto max-w-[1540px] space-y-4">
      <header>
        <BarraDoWorkspace secao="Histórico" />
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <EtiquetaDeRegistro>Registros</EtiquetaDeRegistro>
            <h1 className="mt-1 text-2xl font-extrabold tracking-tight text-foreground sm:text-[27px]">Histórico de sessões</h1>
            <p className="mt-0.5 text-xs text-muted-foreground">Veja cada sessão e quanto dela foi registrado.</p>
          </div>
          <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row sm:items-center">
            <SeletorDeDispositivo dispositivos={dispositivos} selecionado={aparelho} aoSelecionar={escolherAparelho} />
            <div className="w-full sm:w-sm">
              <SeletorSegmentado rotulo="Período do histórico" opcoes={JANELAS} selecionado={dias} aoSelecionar={setDias} />
            </div>
          </div>
        </div>
      </header>

      <section aria-label="Sessões do período" className="space-y-4">
        {demo ? (() => {
          const exemplos = EXEMPLOS.filter((linha) => linha.inicio > EXEMPLOS[0].inicio - dias * DIA_MS
            && (aparelho === null || linha.aparelho === aparelho));
          return (
            <>
              <ResumoDoPeriodo sessoes={exemplos} aoEscolherSessao={irParaSessao} />
              <div className={CARTAO_DA_LISTA}>
                <ListaDeSessoes linhas={exemplos} dispositivos={dispositivos} />
                <p className="pt-4 text-xs text-muted-foreground">Dados de exemplo para demonstrar a navegação do histórico.</p>
              </div>
            </>
          );
        })() : <SessoesDaConta key={dias} dias={dias} aparelho={aparelho} dispositivos={dispositivos} />}
      </section>

      <p className="rounded-xl border border-border border-l-4 border-l-primary px-3 py-3 text-xs text-muted-foreground">
        O tempo registrado é só o que o aparelho mediu. Onde faltam registros, não é possível saber se houve movimento.
      </p>
    </div>
  );
}

function SessoesDaConta({ dias, aparelho, dispositivos }: {
  dias: number;
  /** UI-55: só as sessões deste aparelho; `null` = todos. */
  aparelho: string | null;
  dispositivos: Dispositivo[];
}) {
  const [janela] = useState(() => {
    const agora = Date.now();
    return { desde: new Date(agora - dias * DIA_MS).toISOString(), ate: new Date(agora).toISOString() };
  });
  const [tentativa, setTentativa] = useState(0);
  const [pagina, setPagina] = useState(1);
  const [resultado, setResultado] = useState<Awaited<ReturnType<typeof buscarJanelaDoHistorico>> | null>(null);
  const [erro, setErro] = useState<string | ErroApi | null>(null);

  useEffect(() => {
    const controle = new AbortController();
    buscarJanelaDoHistorico(janela, controle.signal, setPagina).then(
      (dados) => { if (!controle.signal.aborted) setResultado(dados); },
      (falha: unknown) => {
        if (!controle.signal.aborted) {
          setErro(falha instanceof ErroApi ? falha : "Não foi possível carregar as sessões.");
        }
      },
    );
    return () => controle.abort();
  }, [janela, tentativa]);

  const linhas = useMemo(() => resultado
    ? resumirSessoes(resultado.leituras, Date.parse(janela.desde), resultado.truncada)
    : [], [resultado, janela]);

  // DATA-16: excluir e marcar. `confirmando` é a sessão cuja exclusão espera
  // o segundo clique; `ocupado` trava as ações enquanto uma está no servidor.
  const [confirmando, setConfirmando] = useState<Linha | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [aviso, setAviso] = useState<{ texto: string | ErroApi; falha: boolean } | null>(null);

  function recarregar() {
    setResultado(null);
    setPagina(1);
    setTentativa((atual) => atual + 1);
  }

  async function agir(linha: Linha, acao: "apagar" | "marcar" | "desmarcar") {
    if (!linha.trecho) return;
    setOcupado(true);
    setAviso(null);
    try {
      if (acao === "apagar") {
        const n = await apagarSessao(linha.trecho);
        setAviso({ texto: `Sessão excluída: ${n} ${n === 1 ? "registro apagado" : "registros apagados"}.`, falha: false });
      } else {
        const n = await marcarSessao(linha.trecho, acao === "marcar");
        setAviso({
          texto: acao === "marcar"
            ? `Sessão marcada como bancada/teste (${n} ${n === 1 ? "registro" : "registros"}). Ela sai do painel e das análises.`
            : `Sessão desmarcada (${n} ${n === 1 ? "registro" : "registros"}). Ela volta ao painel e às análises.`,
          falha: false,
        });
      }
      setConfirmando(null);
      recarregar();
    } catch (falha) {
      if (falha instanceof ErroApi && falha.status === 409) {
        setConfirmando(null);
        recarregar();
      }
      setAviso({
        texto: falha instanceof ErroApi ? falha : "Não foi possível concluir. Tente novamente.",
        falha: true,
      });
    } finally {
      setOcupado(false);
    }
  }

  if (erro) return <FalhaAoCarregar mensagem={erro} aoTentarNovamente={() => {
    setErro(null);
    setPagina(1);
    setTentativa((atual) => atual + 1);
  }} />;
  if (!resultado) return <Carregando mensagem={`Carregando sessões... página ${pagina} de até ${MAX_PAGINAS_DO_HISTORICO}.`} />;

  const doAparelho = aparelho === null ? linhas : linhas.filter((linha) => linha.aparelho === aparelho);
  const normais = doAparelho.filter((linha) => !linha.bancada);
  const marcadas = doAparelho.filter((linha) => linha.bancada);
  const movimento = dias === 1
    ? serieDasUltimas24Horas(resultado.leituras.filter((l) => aparelho === null || l.device_id === aparelho), Date.parse(janela.desde))
    : undefined;
  const acoes = (linha: Linha) => linha.trecho ? (
    <MenuDaSessao rotulo={`Ações da sessão de ${dataDaSessao(linha)}`}>
      <button
        type="button"
        disabled={ocupado}
        onClick={() => agir(linha, linha.bancada ? "desmarcar" : "marcar")}
        className="flex items-center rounded-lg px-2.5 text-sm font-medium text-foreground hover:bg-secondary disabled:opacity-50"
      >
        {linha.bancada ? "Desmarcar" : "Marcar como bancada"}
      </button>
      <button
        type="button"
        disabled={ocupado}
        onClick={() => { setAviso(null); setConfirmando(linha); }}
        className="flex items-center rounded-lg px-2.5 text-sm font-medium text-destructive hover:bg-destructive/5 disabled:opacity-50"
      >
        Excluir…
      </button>
    </MenuDaSessao>
  ) : null;

  return (
    <>
      {resultado.truncada && (
        <p role="status" className="mb-3 rounded-lg bg-amber-500/10 px-3 py-2 text-xs text-foreground">
          Há mais registros do que esta tela consegue carregar. O histórico deste período pode estar incompleto.
        </p>
      )}
      {aviso && !confirmando && (
        <div role={aviso.falha ? "alert" : "status"} className={`mb-3 rounded-lg px-3 py-2 text-xs ${aviso.falha
          ? "bg-destructive/10 text-destructive"
          : "bg-emerald-500/10 text-foreground"}`}>
          <MensagemDeFalha erro={aviso.texto} />
        </div>
      )}
      {confirmando && (
        <ConfirmacaoDeExclusao ocupado={ocupado} aoCancelar={() => setConfirmando(null)}>
          <p>
            Excluir a sessão de <strong>{DATA_E_HORA.format(confirmando.inicio)}</strong> até{" "}
            <strong>{DATA_E_HORA.format(confirmando.fim)}</strong>, com{" "}
            <strong>{confirmando.leituras} {confirmando.leituras === 1 ? "registro" : "registros"}</strong>?
            Os registros são apagados do servidor e não há como desfazer.
          </p>
          {aviso?.falha && <div role="alert" className="text-destructive"><MensagemDeFalha erro={aviso.texto} /></div>}
          <div className="flex flex-wrap gap-2">
            <button type="button" data-foco-inicial disabled={ocupado} onClick={() => setConfirmando(null)}
              className="flex-1 rounded-lg border border-border px-3 py-2 font-medium hover:bg-secondary disabled:opacity-60">
              Cancelar
            </button>
            <button type="button" disabled={ocupado} onClick={() => agir(confirmando, "apagar")}
              className="flex-1 rounded-lg bg-destructive px-3 py-2 font-medium text-white hover:opacity-90 disabled:opacity-40">
              {ocupado ? "Apagando..." : "Excluir definitivamente"}
            </button>
          </div>
        </ConfirmacaoDeExclusao>
      )}
      {normais.length > 0 && (
        <div className="mb-4">
          <ResumoDoPeriodo sessoes={normais} parcial={resultado.truncada} movimento={movimento} aoEscolherSessao={irParaSessao} />
        </div>
      )}
      <div className={CARTAO_DA_LISTA}>
        {normais.length > 0
          ? <ListaDeSessoes linhas={normais} acoes={acoes} dispositivos={dispositivos} />
          : <p className="py-12 text-center text-sm text-muted-foreground">
              {aparelho === null ? "Nenhuma sessão no período selecionado." : "Nenhuma sessão deste aparelho no período selecionado."}
            </p>}
      </div>
      {marcadas.length > 0 && (
        <section aria-label="Sessões marcadas como bancada/teste" className={`mt-6 space-y-2 ${CARTAO_DA_LISTA}`}>
          <h2 className="text-sm font-semibold text-foreground">Marcadas como bancada/teste</h2>
          <p className="text-xs text-muted-foreground">
            Continuam guardadas, mas ficam fora do painel e das análises. Desmarque para que voltem.
          </p>
          <ListaDeSessoes linhas={marcadas} acoes={acoes} dispositivos={dispositivos} rotulo="Tabela das sessões marcadas como bancada" />
        </section>
      )}
    </>
  );
}

/**
 * UI-52: em "Últimas 24 horas", o gráfico do topo é o de movimento, como no Início.
 * Só com um aparelho: a série de dois instrumentos juntos não tem leitura (o Início avisa
 * a mistura; aqui, com mais de um, ficam as barras por sessão).
 */
function serieDasUltimas24Horas(leituras: LeituraSono[], desdeMs: number) {
  const daJanela = leituras.filter((leitura) => !ehBancada(leitura)
    && Date.parse(instanteDaLeitura(leitura)) >= desdeMs);
  if (daJanela.length === 0 || new Set(daJanela.map((leitura) => leitura.device_id ?? null)).size > 1) return undefined;
  const ordem = [...daJanela].sort((a, b) => Date.parse(instanteDaLeitura(a)) - Date.parse(instanteDaLeitura(b)));
  const serie = prepararSerie(ordem, calcularCobertura(ordem));
  return serie.length > 0 ? serie : undefined;
}

function ConfirmacaoDeExclusao({ ocupado, aoCancelar, children }: {
  ocupado: boolean;
  aoCancelar: () => void;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialogo = ref.current;
    if (!dialogo) return;
    const origem = document.activeElement;
    dialogo.showModal();
    dialogo.querySelector<HTMLElement>("[data-foco-inicial]")?.focus();
    return () => {
      dialogo.close();
      if (origem instanceof HTMLElement && origem.isConnected) origem.focus();
    };
  }, []);
  return (
    <dialog ref={ref} role="alertdialog" aria-label="Confirmar exclusão da sessão"
      onCancel={(evento) => { evento.preventDefault(); if (!ocupado) aoCancelar(); }}
      className="m-auto max-h-[calc(100dvh-2rem)] w-[calc(100%-2rem)] max-w-sm space-y-3 overflow-y-auto rounded-2xl border border-destructive/40 bg-card p-4 text-sm text-foreground shadow-xl backdrop:bg-black/60">
      {children}
    </dialog>
  );
}

function dataDaSessao(linha: Linha) {
  return DATA.format(linha.inicio).replace(/ de |\./g, " ").replace(/ +/g, " ");
}

function tempoDaSessao(linha: Linha) {
  return linha.periodo === null ? "—" : `${formatarDuracao(linha.tempo)} de ${formatarDuracao(linha.periodo)}`;
}

function SituacaoDaSessao({ linha: { parcial, lacunas, periodo, pausas } }: { linha: Linha }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2 py-1 text-[10px] font-extrabold uppercase tracking-wider ${parcial || lacunas
      ? "bg-amber-500/10 text-amber-800 dark:text-amber-300"
      : periodo === null ? "bg-secondary text-muted-foreground" : "bg-emerald-500/10 text-emerald-800 dark:text-emerald-300"}`}>
      <span className="size-1.5 shrink-0 rounded-full bg-current" aria-hidden />
      {parcial ? "Parcial" : periodo === null ? "Sem estimativa" : !lacunas ? "Completa" : pausas ? "Com pausas" : "Incompleta"}
    </span>
  );
}

function ListaDeSessoes({ linhas, acoes, dispositivos = [], rotulo = "Tabela do histórico" }: {
  linhas: Linha[];
  acoes?: (linha: Linha) => ReactNode;
  /** UI-55: com mais de um aparelho na conta, cada sessão diz de qual veio. */
  dispositivos?: Dispositivo[];
  rotulo?: string;
}) {
  const nomeDoAparelho = precisaEscolherDispositivo(dispositivos)
    ? (linha: Linha) => aparelhoDaSessao(dispositivos, linha.aparelho)
    : () => null;
  const estreita = useSyncExternalStore(observarLargura, telaEstreita);
  const { search } = useLocation();
  const regua = reguaDoHorario(linhas);
  // UI-54: a sessão abre no Início, no dia em que começou e no aparelho dela.
  const noInicio = (linha: Linha) => destinoDoDia(linha.inicio, linha.trecho?.device, search);
  if (estreita) return (
    <ul aria-label={rotulo === "Tabela do histórico" ? "Sessões do histórico" : "Sessões de bancada"}
      className="space-y-3">
      {linhas.map((linha) => (
        <li key={linha.chave}>
          <article id={idDaSessao(linha.chave)} tabIndex={-1} aria-label={`Sessão de ${dataDaSessao(linha)}`}
            className="scroll-mt-20 space-y-3 rounded-2xl border border-border bg-card p-3 text-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-sm font-semibold">
                {dataDaSessao(linha)}{" "}
                <span className="font-normal text-muted-foreground">· {HORA.format(linha.inicio)} às {HORA.format(linha.fim)}</span>
                {nomeDoAparelho(linha) && <span data-aparelho className="block text-xs font-medium text-muted-foreground">{nomeDoAparelho(linha)}</span>}
              </h3>
              <SituacaoDaSessao linha={linha} />
            </div>
            {linha.serie && linha.serie.length > 1
              ? <MiniGraficoDaSessao serie={linha.serie} />
              : linha.trechos && (
                <FaixaDaSessao regua={reguaDoHorario([linha])} inicio={linha.inicio} fim={linha.fim}
                  trechos={linha.trechos} movimentos={linha.movimentos ?? []} tempo={linha.tempo} />
              )}
            <ul aria-label="Métricas da sessão" className="grid grid-cols-3 gap-2">
              <CartaoDeMetrica valor={formatarDuracao(linha.tempo)}>
                <p>{linha.periodo === null ? "registrado" : `registrado de ${formatarDuracao(linha.periodo)}`}</p>
              </CartaoDeMetrica>
              <CartaoDeMetrica valor={movimentoDaSessao(linha)}><p>com movimento</p></CartaoDeMetrica>
              <CartaoDeMetrica valor={linha.leituras}><p>{linha.leituras === 1 ? "registro" : "registros"}</p></CartaoDeMetrica>
            </ul>
            <div className="flex items-center justify-between gap-2">
              <Link to={noInicio(linha)} className="inline-flex min-h-9 items-center rounded-lg px-1 text-sm font-semibold text-primary hover:underline focus-visible:outline-2 focus-visible:outline-ring">
                Abrir no Início
              </Link>
              {acoes?.(linha)}
            </div>
          </article>
        </li>
      ))}
    </ul>
  );

  return (
    <div className="overflow-x-auto rounded-sm" role="region" aria-label={rotulo} tabIndex={0}>
      <table className="w-full min-w-[46rem] text-left text-xs text-foreground">
        <thead className="border-b border-border text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
          <tr>
            <th scope="col" className="px-2 py-3">Data</th>
            <th scope="col" className="w-[36%] px-2 py-3">
              <span>Horário</span>
              <span aria-hidden="true" className="relative mt-1 block h-3 font-semibold normal-case tracking-normal">
                {marcasDaRegua(regua).map((marca, i, todas) => (
                  <span key={marca.fracao}
                    className={`absolute tabular-nums ${i === 0 ? "" : i === todas.length - 1 ? "-translate-x-full" : "-translate-x-1/2"}`}
                    style={{ left: `${marca.fracao * 100}%` }}>{marca.rotulo}</span>
                ))}
              </span>
            </th>
            <th scope="col" className="px-2 py-3">Registrado</th>
            <th scope="col" className="px-2 py-3">Movimento</th>
            <th scope="col" className="px-2 py-3">Registros</th>
            <th scope="col" className="px-2 py-3 text-right">Situação</th>
            {acoes && <th scope="col" className="px-2 py-3 text-right"><span className="sr-only">Ações</span></th>}
          </tr>
        </thead>
        <tbody className="divide-y divide-border border-b border-border">
          {linhas.map((linha) => (
            <tr key={linha.chave} id={idDaSessao(linha.chave)} tabIndex={-1} className="scroll-mt-20 outline-none focus:bg-secondary/60">
              <th scope="row" className="whitespace-nowrap px-2 py-3 font-semibold">
                <Link to={noInicio(linha)} title="Abrir no Início"
                  className="rounded-sm text-foreground underline-offset-2 hover:text-primary hover:underline focus-visible:outline-2 focus-visible:outline-ring">
                  {dataDaSessao(linha)}
                </Link>
                {nomeDoAparelho(linha) && <span data-aparelho className="block text-[11px] font-medium text-muted-foreground">{nomeDoAparelho(linha)}</span>}
              </th>
              <td className="px-2 py-3">
                {linha.trechos
                  ? <FaixaDaSessao regua={regua} inicio={linha.inicio} fim={linha.fim} trechos={linha.trechos}
                      movimentos={linha.movimentos ?? []} tempo={linha.tempo} />
                  : <span className="text-muted-foreground">—</span>}
              </td>
              <td className="whitespace-nowrap px-2 py-3">{tempoDaSessao(linha)}</td>
              <td className="px-2 py-3">{movimentoDaSessao(linha)}</td>
              <td className="px-2 py-3">{linha.leituras}</td>
              <td className="px-2 py-3 text-right"><SituacaoDaSessao linha={linha} /></td>
              {acoes && <td className="px-2 py-3 text-right">{acoes(linha)}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const HORA = new Intl.DateTimeFormat("pt-BR", { hour: "2-digit", minute: "2-digit" });

/** "Travesseiro" ou "Celular" (o tipo), com o nome que a pessoa deu quando ele diz algo a mais. */
function aparelhoDaSessao(dispositivos: Dispositivo[], id: string | null | undefined) {
  const d = dispositivos.find((x) => x.id === id);
  if (!d) return id ? "Aparelho removido" : null;
  const tipo = rotuloDoTipo(d.tipo);
  return d.nome && !d.nome.toLowerCase().includes(tipo.toLowerCase()) ? `${tipo} · ${d.nome}` : d.nome || tipo;
}

function movimentoDaSessao(linha: Linha) {
  return linha.movimento == null ? "—" : formatarPorcentagem(linha.movimento * 100);
}
