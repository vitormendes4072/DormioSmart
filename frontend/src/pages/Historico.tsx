import { useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router";

import { BarraDoWorkspace } from "../components/BarraDoWorkspace";
import { Carregando, FalhaAoCarregar } from "../components/EstadoDaTela";
import { buscarJanelaDoHistorico, ErroApi, MAX_PAGINAS_DO_HISTORICO } from "../lib/api";
import { agruparEmSessoes, calcularCobertura } from "../lib/cobertura";
import { estaEmModoDemo } from "../lib/demo";
import { formatarDuracao } from "../lib/metricas";
import { instanteDaLeitura, type LeituraSono } from "../types/sleep";

const DIA_MS = 24 * 60 * 60 * 1000;
const DATA = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit", month: "short", year: "numeric",
});

type Linha = {
  chave: string;
  inicio: number;
  tempo: number;
  cobertura: number | null;
  leituras: number;
  lacunas: boolean;
  parcial?: boolean;
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
  const porDispositivo = new Map<string | null, LeituraSono[]>();
  for (const leitura of leituras) {
    // A API recorta pela chegada. Exclui medições antigas enviadas com atraso.
    if (!(Date.parse(instanteDaLeitura(leitura)) >= desdeMs)) continue;
    const id = leitura.device_id ?? null;
    const grupo = porDispositivo.get(id);
    if (grupo) grupo.push(leitura);
    else porDispositivo.set(id, [leitura]);
  }

  return Array.from(porDispositivo, ([id, grupo]) =>
    agruparEmSessoes(grupo).map((sessao) => {
      const cobertura = calcularCobertura(sessao.leituras);
      return {
        chave: `${id ?? "sem-dispositivo"}:${sessao.inicio}`,
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

  if (erro) return <FalhaAoCarregar mensagem={erro} aoTentarNovamente={() => {
    setErro(null);
    setPagina(1);
    setTentativa((atual) => atual + 1);
  }} />;
  if (!resultado) return <Carregando mensagem={`Carregando sessões... página ${pagina} de até ${MAX_PAGINAS_DO_HISTORICO}.`} />;

  return (
    <>
      {resultado.truncada && (
        <p role="status" className="mb-3 rounded-lg bg-amber-500/10 px-3 py-2 text-xs text-foreground">
          A consulta atingiu o limite de leituras. O histórico deste período pode estar incompleto.
        </p>
      )}
      {linhas.length > 0
        ? <TabelaDeSessoes linhas={linhas} />
        : <p className="py-12 text-center text-sm text-muted-foreground">Nenhuma sessão no período selecionado.</p>}
    </>
  );
}

function TabelaDeSessoes({ linhas }: { linhas: Linha[] }) {
  return (
    <div className="overflow-x-auto rounded-sm" role="region" aria-label="Tabela do histórico" tabIndex={0}>
      <table className="w-full min-w-[32rem] text-left text-xs text-foreground">
        <thead className="border-b border-border text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
          <tr>
            <th scope="col" className="px-2 py-3">Data</th>
            <th scope="col" className="px-2 py-3">Tempo medido</th>
            <th scope="col" className="px-2 py-3">Cobertura</th>
            <th scope="col" className="px-2 py-3">Leituras</th>
            <th scope="col" className="px-2 py-3 text-right">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border border-b border-border">
          {linhas.map(({ chave, inicio, tempo, cobertura, leituras, lacunas, parcial }) => (
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
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
