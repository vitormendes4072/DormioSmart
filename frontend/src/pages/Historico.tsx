import { useEffect, useMemo, useState, type ReactNode } from "react";
import { useLocation } from "react-router";

import { BarraDoWorkspace } from "../components/BarraDoWorkspace";
import { Carregando, FalhaAoCarregar } from "../components/EstadoDaTela";
import { apagarSessao, buscarJanelaDoHistorico, ErroApi, marcarSessao, MAX_PAGINAS_DO_HISTORICO } from "../lib/api";
import { agruparEmSessoes, calcularCobertura } from "../lib/cobertura";
import { estaEmModoDemo } from "../lib/demo";
import { formatarDuracao } from "../lib/metricas";
import { ehBancada, trechoDaSessao, type Trecho } from "../lib/trecho";
import { instanteDaLeitura, type LeituraSono } from "../types/sleep";

const DIA_MS = 24 * 60 * 60 * 1000;
const DATA = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit", month: "short", year: "numeric",
});
const DATA_E_HORA = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
});

type Linha = {
  chave: string;
  inicio: number;
  tempo: number;
  cobertura: number | null;
  leituras: number;
  lacunas: boolean;
  parcial?: boolean;
  /** Aparelho e instantes da sessão, para excluir ou marcar (DATA-16). Ausente
   *  nos exemplos e nas leituras sem aparelho. */
  trecho?: Trecho | null;
  /** A sessão foi marcada como bancada/teste. */
  bancada?: boolean;
};

const SESSOES_DO_PROTOTIPO: Array<[number, number, number, number, number, number, boolean]> = [
  [2026, 11, 3, 434, 96, 18, false],
  [2026, 11, 2, 408, 90, 24, true],
  [2026, 11, 1, 422, 98, 15, false],
  [2026, 10, 31, 395, 87, 21, true],
  [2026, 10, 30, 461, 99, 13, false],
];

const EXEMPLOS = SESSOES_DO_PROTOTIPO.map(([ano, mes, dia, minutos, cobertura, leituras, lacunas]) => {
  const inicio = new Date(ano, mes - 1, dia, 22).getTime();
  return {
    chave: String(inicio), inicio, tempo: minutos * 60_000,
    cobertura, leituras, lacunas,
  };
});

function resumirSessoes(leituras: LeituraSono[], desdeMs: number, truncada: boolean): Linha[] {
  const borda = truncada ? leituras.at(-1) : undefined;
  // DATA-16: a bancada é agrupada à parte, para que uma sessão marcada não se
  // junte a uma normal do mesmo aparelho e as duas virem uma só na tela.
  const porGrupo = new Map<string, { id: string | null; bancada: boolean; leituras: LeituraSono[] }>();
  for (const leitura of leituras) {
    // A API recorta pela chegada. Exclui medições antigas enviadas com atraso.
    if (!(Date.parse(instanteDaLeitura(leitura)) >= desdeMs)) continue;
    const id = leitura.device_id ?? null;
    const bancada = ehBancada(leitura);
    const chave = `${id ?? "sem-dispositivo"}:${bancada ? "bancada" : "normal"}`;
    const grupo = porGrupo.get(chave);
    if (grupo) grupo.leituras.push(leitura);
    else porGrupo.set(chave, { id, bancada, leituras: [leitura] });
  }

  return Array.from(porGrupo.values(), ({ id, bancada, leituras: grupo }) =>
    agruparEmSessoes(grupo).map((sessao) => {
      const cobertura = calcularCobertura(sessao.leituras);
      return {
        chave: `${id ?? "sem-dispositivo"}:${bancada ? "bancada" : "normal"}:${sessao.inicio}`,
        trecho: trechoDaSessao(sessao.leituras),
        bancada,
        inicio: sessao.inicio,
        tempo: cobertura.tempoCobertoMs,
        cobertura: cobertura.janelaMs > 0 ? (100 * cobertura.tempoCobertoMs) / cobertura.janelaMs : null,
        leituras: sessao.leituras.length,
        lacunas: cobertura.lacunas.length > 0,
        parcial: borda !== undefined && sessao.leituras.includes(borda),
      };
    }),
  ).flat().sort((a, b) => b.inicio - a.inicio);
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
            <h1 className="text-2xl font-extrabold tracking-tight text-foreground sm:text-[27px]">Histórico de sessões</h1>
            <p className="mt-0.5 text-xs text-muted-foreground">Acompanhe os períodos de coleta e a cobertura das medições.</p>
          </div>
          <select
            aria-label="Período do histórico"
            value={dias}
            onChange={(evento) => setDias(Number(evento.target.value))}
            className="min-h-10 rounded-xl border border-border bg-card px-3 text-sm text-foreground"
          >
            <option value={1}>Últimas 24 horas</option>
            <option value={7}>Últimos 7 dias</option>
            <option value={30}>Últimos 30 dias</option>
          </select>
        </div>
      </header>

      <section aria-label="Sessões do período" className="rounded-[14px] border border-border bg-card p-4 shadow-sm">
        {demo ? (
          <>
            <TabelaDeSessoes linhas={EXEMPLOS.filter((linha) => linha.inicio > EXEMPLOS[0].inicio - dias * DIA_MS)} />
            <p className="pt-4 text-xs text-muted-foreground">Dados de exemplo para demonstrar a navegação do histórico.</p>
          </>
        ) : <SessoesDaConta key={dias} dias={dias} />}
      </section>

      <p className="rounded-xl border border-border border-l-4 border-l-primary px-3 py-3 text-xs text-muted-foreground">
        A cobertura descreve a janela observada da sessão. Onde faltam medições, não é possível saber se houve movimento.
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
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    const controle = new AbortController();
    buscarJanelaDoHistorico(janela, controle.signal, setPagina).then(
      (dados) => { if (!controle.signal.aborted) setResultado(dados); },
      (falha: unknown) => {
        if (!controle.signal.aborted) {
          setErro(falha instanceof ErroApi ? falha.message : "Não foi possível carregar as sessões.");
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
  const [aviso, setAviso] = useState<{ texto: string; falha: boolean } | null>(null);

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
        setAviso({ texto: `Sessão excluída: ${n} ${n === 1 ? "época apagada" : "épocas apagadas"}.`, falha: false });
      } else {
        const n = await marcarSessao(linha.trecho, acao === "marcar");
        setAviso({
          texto: acao === "marcar"
            ? `Sessão marcada como bancada/teste (${n} ${n === 1 ? "época" : "épocas"}). Ela sai do painel e das análises.`
            : `Sessão desmarcada (${n} ${n === 1 ? "época" : "épocas"}). Ela volta ao painel e às análises.`,
          falha: false,
        });
      }
      setConfirmando(null);
      recarregar();
    } catch (falha) {
      setAviso({
        texto: falha instanceof ErroApi ? falha.message : "Não foi possível concluir. Tente novamente.",
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
        className="rounded-lg border border-border px-2 py-1 text-[11px] font-semibold text-foreground hover:bg-secondary disabled:opacity-50"
      >
        {linha.bancada ? "Desmarcar" : "Marcar como bancada"}
      </button>
      <button
        type="button"
        disabled={ocupado}
        onClick={() => { setAviso(null); setConfirmando(linha); }}
        className="rounded-lg border border-destructive/40 px-2 py-1 text-[11px] font-semibold text-destructive hover:bg-destructive/5 disabled:opacity-50"
      >
        Excluir…
      </button>
    </div>
  ) : null;

  return (
    <>
      {resultado.truncada && (
        <p role="status" className="mb-3 rounded-lg bg-amber-500/10 px-3 py-2 text-xs text-foreground">
          A consulta atingiu o limite de leituras. O histórico deste período pode estar incompleto.
        </p>
      )}
      {aviso && (
        <p role={aviso.falha ? "alert" : "status"} className={`mb-3 rounded-lg px-3 py-2 text-xs ${aviso.falha
          ? "bg-destructive/10 text-destructive"
          : "bg-emerald-500/10 text-foreground"}`}>
          {aviso.texto}
        </p>
      )}
      {confirmando && (
        <div role="alertdialog" aria-label="Confirmar exclusão da sessão"
          className="mb-3 space-y-3 rounded-xl border border-destructive/40 bg-destructive/5 p-3 text-xs text-foreground">
          <p>
            Excluir a sessão de <strong>{DATA_E_HORA.format(confirmando.inicio)}</strong>, com{" "}
            <strong>{confirmando.leituras} {confirmando.leituras === 1 ? "leitura" : "leituras"}</strong>?
            As épocas são apagadas do servidor e não há como desfazer.
          </p>
          <div className="flex gap-2">
            <button type="button" disabled={ocupado} onClick={() => setConfirmando(null)}
              className="flex-1 rounded-lg border border-border px-3 py-2 font-medium hover:bg-secondary disabled:opacity-60">
              Cancelar
            </button>
            <button type="button" disabled={ocupado} onClick={() => agir(confirmando, "apagar")}
              className="flex-1 rounded-lg bg-destructive px-3 py-2 font-medium text-white hover:opacity-90 disabled:opacity-40">
              {ocupado ? "Apagando..." : "Excluir definitivamente"}
            </button>
          </div>
        </div>
      )}
      {normais.length > 0
        ? <TabelaDeSessoes linhas={normais} acoes={acoes} />
        : <p className="py-12 text-center text-sm text-muted-foreground">Nenhuma sessão no período selecionado.</p>}
      {marcadas.length > 0 && (
        <section aria-label="Sessões marcadas como bancada/teste" className="mt-6 space-y-2">
          <h2 className="text-sm font-semibold text-foreground">Marcadas como bancada/teste</h2>
          <p className="text-xs text-muted-foreground">
            Continuam guardadas, mas ficam fora do painel e das análises. Desmarque para que voltem.
          </p>
          <TabelaDeSessoes linhas={marcadas} acoes={acoes} rotulo="Tabela das sessões marcadas como bancada" />
        </section>
      )}
    </>
  );
}

function TabelaDeSessoes({ linhas, acoes, rotulo = "Tabela do histórico" }: {
  linhas: Linha[];
  acoes?: (linha: Linha) => ReactNode;
  rotulo?: string;
}) {
  return (
    <div className="overflow-x-auto rounded-sm" role="region" aria-label={rotulo} tabIndex={0}>
      <table className="w-full min-w-[32rem] text-left text-xs text-foreground">
        <thead className="border-b border-border text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
          <tr>
            <th scope="col" className="px-2 py-3">Data</th>
            <th scope="col" className="px-2 py-3">Tempo medido</th>
            <th scope="col" className="px-2 py-3">Cobertura</th>
            <th scope="col" className="px-2 py-3">Leituras</th>
            <th scope="col" className="px-2 py-3 text-right">Status</th>
            {acoes && <th scope="col" className="px-2 py-3 text-right">Ações</th>}
          </tr>
        </thead>
        <tbody className="divide-y divide-border border-b border-border">
          {linhas.map((linha) => {
            const { chave, inicio, tempo, cobertura, leituras, lacunas, parcial } = linha;
            return (
            <tr key={chave}>
              <th scope="row" className="whitespace-nowrap px-2 py-3 font-semibold">{DATA.format(inicio).replace(/ de |\./g, " ").replace(/ +/g, " ")}</th>
              <td className="whitespace-nowrap px-2 py-3">{formatarDuracao(tempo)}</td>
              <td className="px-2 py-3">{cobertura === null ? "—" : `${Math.round(cobertura)}%`}</td>
              <td className="px-2 py-3">{leituras}</td>
              <td className="px-2 py-3 text-right">
                <span className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2 py-1 text-[11px] font-semibold ${parcial || lacunas
                  ? "bg-amber-500/10 text-amber-800 dark:text-amber-300"
                  : cobertura === null
                    ? "bg-secondary text-muted-foreground"
                    : "bg-emerald-500/10 text-emerald-800 dark:text-emerald-300"}`}>
                  <span className="size-1.5 rounded-full bg-current" aria-hidden />
                  {parcial ? "Parcial" : cobertura === null ? "Sem estimativa" : lacunas ? "Com lacunas" : "Completa"}
                </span>
              </td>
              {acoes && <td className="px-2 py-3 text-right">{acoes(linha)}</td>}
            </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
