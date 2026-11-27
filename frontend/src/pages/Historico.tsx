import { MensagemDeFalha } from "../components/MensagemDeFalha";
import { useEffect, useMemo, useRef, useState, useSyncExternalStore, type ReactNode } from "react";
import { Link, useLocation } from "react-router";

import { BarraDoWorkspace } from "../components/BarraDoWorkspace";
import { CartaoDeMetrica, CartaoEmDestaque, EtiquetaDeRegistro } from "../components/CartoesDeRegistro";
import { Carregando, FalhaAoCarregar } from "../components/EstadoDaTela";
import { SeletorSegmentado } from "../components/SeletorSegmentado";
import { usePresencaDeRegistros } from "../hooks/usePresencaDeRegistros";
import { apagarSessao, buscarJanelaDoHistorico, ErroApi, marcarSessao, MAX_PAGINAS_DO_HISTORICO } from "../lib/api";
import { calcularCobertura } from "../lib/cobertura";
import { estaEmModoDemo } from "../lib/demo";
import { formatarDuracao } from "../lib/metricas";
import { sessoesDaMarca, trechoDaSessao, type Trecho } from "../lib/trecho";
import { instanteDaLeitura, type LeituraSono } from "../types/sleep";

const TELA_ESTREITA = "(max-width: 767px)";

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
};

const SESSOES_DO_PROTOTIPO: Array<[number, number, number, number, number, number, boolean]> = [
  [2026, 11, 3, 434, 100, 18, false],
  [2026, 11, 2, 408, 90, 24, true],
  [2026, 11, 1, 422, 98, 15, false],
  [2026, 10, 31, 395, 87, 21, true],
  [2026, 10, 30, 461, 100, 13, false],
];

const EXEMPLOS = SESSOES_DO_PROTOTIPO.map(([ano, mes, dia, minutos, cobertura, leituras, pausas]) => {
  const inicio = new Date(ano, mes - 1, dia, 22).getTime();
  return {
    chave: String(inicio), inicio, fim: inicio + minutos * 60_000, tempo: minutos * 60_000,
    periodo: (minutos * 60_000 * 100) / cobertura, leituras, lacunas: cobertura < 100, pausas,
  };
});

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

export function Historico() {
  const { search } = useLocation();
  const demo = estaEmModoDemo(search);
  const [dias, setDias] = useState(7);

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
          <div className="w-full sm:max-w-sm">
            <SeletorSegmentado rotulo="Período do histórico" opcoes={JANELAS} selecionado={dias} aoSelecionar={setDias} />
          </div>
        </div>
      </header>

      <section aria-label="Sessões do período" className="md:rounded-2xl md:border md:border-border md:bg-card md:p-4 md:shadow-sm">
        {demo ? (
          <>
            <ListaDeSessoes linhas={EXEMPLOS.filter((linha) => linha.inicio > EXEMPLOS[0].inicio - dias * DIA_MS)} />
            <p className="pt-4 text-xs text-muted-foreground">Dados de exemplo para demonstrar a navegação do histórico.</p>
          </>
        ) : <SessoesDaConta key={dias} dias={dias} />}
      </section>

      <p className="rounded-xl border border-border border-l-4 border-l-primary px-3 py-3 text-xs text-muted-foreground">
        O tempo registrado é só o que o aparelho mediu. Onde faltam registros, não é possível saber se houve movimento.
      </p>
    </div>
  );
}

function SessoesDaConta({ dias }: { dias: number }) {
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

  const normais = linhas.filter((linha) => !linha.bancada);
  const marcadas = linhas.filter((linha) => linha.bancada);
  const acoes = (linha: Linha) => linha.trecho ? (
    <div className="flex flex-wrap justify-end gap-1.5">
      <button
        type="button"
        disabled={ocupado}
        onClick={() => agir(linha, linha.bancada ? "desmarcar" : "marcar")}
        className="rounded-lg border border-border min-h-9 px-2 py-1 text-xs font-semibold md:min-h-0 md:text-[11px] text-foreground hover:bg-secondary disabled:opacity-50"
      >
        {linha.bancada ? "Desmarcar" : "Marcar como bancada"}
      </button>
      <button
        type="button"
        disabled={ocupado}
        onClick={() => { setAviso(null); setConfirmando(linha); }}
        className="rounded-lg border border-destructive/40 min-h-9 px-2 py-1 text-xs font-semibold md:min-h-0 md:text-[11px] text-destructive hover:bg-destructive/5 disabled:opacity-50"
      >
        Excluir…
      </button>
    </div>
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
      {normais.length > 0
        ? <ListaDeSessoes linhas={normais} acoes={acoes} />
        : <HistoricoVazio podeConferirConta={!resultado.truncada} />}
      {marcadas.length > 0 && (
        <section aria-label="Sessões marcadas como bancada/teste" className="mt-6 space-y-2">
          <h2 className="text-sm font-semibold text-foreground">Marcadas como bancada/teste</h2>
          <p className="text-xs text-muted-foreground">
            Continuam guardadas, mas ficam fora do painel e das análises. Desmarque para que voltem.
          </p>
          <ListaDeSessoes linhas={marcadas} acoes={acoes} rotulo="Tabela das sessões marcadas como bancada" />
        </section>
      )}
    </>
  );
}

function HistoricoVazio({ podeConferirConta }: { podeConferirConta: boolean }) {
  const presenca = usePresencaDeRegistros(podeConferirConta ? null : undefined);
  if (presenca !== "sem-registro") {
    return <p className="py-12 text-center text-sm text-muted-foreground">Nenhuma sessão no período selecionado.</p>;
  }

  return (
    <div className="flex flex-col items-center gap-3 py-8">
      <p className="text-sm text-muted-foreground">Ainda não há sessões.</p>
      <Link to="/dashboard" className="inline-flex min-h-11 items-center rounded-lg border border-border px-3 text-sm font-semibold text-primary hover:bg-secondary focus-visible:outline-2 focus-visible:outline-ring">
        Ir para o Início
      </Link>
    </div>
  );
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

function ListaDeSessoes({ linhas, acoes, rotulo = "Tabela do histórico" }: {
  linhas: Linha[];
  acoes?: (linha: Linha) => ReactNode;
  rotulo?: string;
}) {
  const estreita = useSyncExternalStore(observarLargura, telaEstreita);
  if (estreita) return (
    <ul aria-label={rotulo === "Tabela do histórico" ? "Sessões do histórico" : "Sessões de bancada"}
      className="space-y-3">
      {linhas.map((linha, indice) => (
        <li key={linha.chave}>
          <article className="space-y-3 rounded-2xl border border-border bg-card p-3 text-foreground">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-sm font-semibold">{dataDaSessao(linha)}</h3>
              <SituacaoDaSessao linha={linha} />
            </div>
            <ul aria-label="Métricas da sessão" className="grid grid-cols-[minmax(0,2fr)_minmax(0,1fr)] gap-2">
              {indice === 0 && !linha.bancada && linha.periodo !== null ? (
                <li>
                  <CartaoEmDestaque rotulo="Registrado" valor={formatarDuracao(linha.tempo)}>
                    de {formatarDuracao(linha.periodo)}
                  </CartaoEmDestaque>
                </li>
              ) : (
                <CartaoDeMetrica valor={tempoDaSessao(linha)}>Registrado</CartaoDeMetrica>
              )}
              <CartaoDeMetrica valor={linha.leituras}>Registros</CartaoDeMetrica>
            </ul>
            {acoes?.(linha)}
          </article>
        </li>
      ))}
    </ul>
  );

  return (
    <div className="overflow-x-auto rounded-sm" role="region" aria-label={rotulo} tabIndex={0}>
      <table className="w-full min-w-[32rem] text-left text-xs text-foreground">
        <thead className="border-b border-border text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
          <tr>
            <th scope="col" className="px-2 py-3">Data</th>
            <th scope="col" className="px-2 py-3">Registrado</th>
            <th scope="col" className="px-2 py-3">Registros</th>
            <th scope="col" className="px-2 py-3 text-right">Situação</th>
            {acoes && <th scope="col" className="px-2 py-3 text-right">Ações</th>}
          </tr>
        </thead>
        <tbody className="divide-y divide-border border-b border-border">
          {linhas.map((linha) => (
            <tr key={linha.chave}>
              <th scope="row" className="whitespace-nowrap px-2 py-3 font-semibold">{dataDaSessao(linha)}</th>
              <td className="px-2 py-3">{tempoDaSessao(linha)}</td>
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
