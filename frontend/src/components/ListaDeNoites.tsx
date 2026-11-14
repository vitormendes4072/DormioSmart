import { CheckCircle2, Clock, NotebookPen, Thermometer } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router";

import { Moldura } from "./Blueprint";
import { formatarDuracao } from "../lib/metricas";
import {
  type NoiteGravada,
  type NotasDaNoite,
  type PluginNoite,
  Noite,
  POSICOES,
  resumoDaNoiteGravada,
} from "../lib/noiteNativa";

/**
 * As noites gravadas no aparelho (APP-02, etapa 4): o "depois" da noite.
 *
 * Cada noite mostra quanto durou, a cobertura de dentro dela (as lacunas
 * baixam o número), quanto já foi para a conta e as anotações — a posição e o
 * diário de sono do protocolo. As anotações ficam no aparelho; o painel
 * mostra a noite assim que ela é enviada.
 *
 * Sono e vigília não aparecem aqui: são inferência sobre saúde, e esperam a
 * política de privacidade dizer isso (`LGPD-03`, `DASH-04`).
 */

const CAMPOS_DO_DIARIO: { chave: keyof NotasDaNoite; rotulo: string; tipo: "time" | "text" }[] = [
  { chave: "deitou", rotulo: "Deitei às", tipo: "time" },
  { chave: "adormeceu", rotulo: "Acho que adormeci às", tipo: "time" },
  { chave: "acordou", rotulo: "Acordei às", tipo: "time" },
  { chave: "despertares", rotulo: "Despertares de que lembro", tipo: "text" },
  { chave: "observacao", rotulo: "Observação", tipo: "text" },
];

function rotuloDaPosicao(p?: string) {
  return POSICOES.find((x) => x.valor === p)?.rotulo ?? "posição não anotada";
}

function FormularioDeNotas({
  noite,
  plugin,
  aoSalvar,
}: {
  noite: NoiteGravada;
  plugin: PluginNoite;
  aoSalvar: (notas: NotasDaNoite) => void;
}) {
  const [valores, setValores] = useState<NotasDaNoite>(noite.notas ?? {});
  const [salvando, setSalvando] = useState(false);
  const [mensagem, setMensagem] = useState<string | null>(null);

  const salvar = async () => {
    setSalvando(true);
    setMensagem(null);
    try {
      const notas: NotasDaNoite = {};
      for (const c of CAMPOS_DO_DIARIO) notas[c.chave] = (valores[c.chave] ?? "") as never;
      aoSalvar(await plugin.salvarNotas({ arquivo: noite.arquivo, notas }));
      setMensagem("Anotações salvas no aparelho.");
    } catch {
      setMensagem("O aparelho recusou as anotações.");
    } finally {
      setSalvando(false);
    }
  };

  return (
    <div className="space-y-2" data-testid={`notas-${noite.arquivo}`}>
      {CAMPOS_DO_DIARIO.map((c) => (
        <label key={c.chave} className="flex flex-col gap-1 text-sm">
          <span className="text-muted-foreground">{c.rotulo}</span>
          <input
            type={c.tipo}
            maxLength={c.tipo === "text" ? 500 : undefined}
            value={valores[c.chave] ?? ""}
            onChange={(e) => setValores({ ...valores, [c.chave]: e.target.value })}
            className="rounded-lg border border-border bg-transparent px-3 py-1.5"
          />
        </label>
      ))}
      <button
        type="button"
        disabled={salvando}
        onClick={() => void salvar()}
        className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-1.5 text-sm font-medium"
      >
        <NotebookPen className="w-4 h-4" aria-hidden />
        Salvar anotações
      </button>
      {mensagem && (
        <p className="text-sm text-muted-foreground" role="status">
          {mensagem}
        </p>
      )}
    </div>
  );
}

export function ListaDeNoites({
  plugin = Noite,
  recarregar = 0,
}: {
  plugin?: PluginNoite;
  /** Mude o valor para reler a lista (depois de encerrar ou enviar). */
  recarregar?: number;
}) {
  const [noites, setNoites] = useState<NoiteGravada[] | null>(null);
  const [aberta, setAberta] = useState<string | null>(null);

  const [erroLocal, setErroLocal] = useState<string | null>(null);

  async function agirNoTeste(noite: NoiteGravada, apagar: boolean) {
    if (apagar && !window.confirm("Apagar esta gravação de teste do aparelho?")) return;
    setErroLocal(null);
    try {
      const pedido = { arquivo: noite.arquivo };
      if (apagar) {
        await plugin.apagarTeste(pedido);
        setNoites((atuais) => atuais?.filter((item) => item.arquivo !== noite.arquivo) ?? null);
      } else {
        await plugin.compartilharTeste(pedido);
      }
    } catch {
      setErroLocal(apagar ? "Não foi possível apagar a gravação." : "Não foi possível compartilhar a gravação.");
    }
  }

  const [falhou, setFalhou] = useState(false);
  const [tentativa, setTentativa] = useState(0);

  useEffect(() => {
    let atual = true;
    setFalhou(false);

    async function ler() {
      try {
        // A mais recente primeiro: é a que acabou de terminar.
        const resultado = await plugin.noites();
        if (atual) setNoites([...resultado.noites].reverse());
      } catch {
        if (atual) {
          setNoites(null);
          setFalhou(true);
        }
      }
    }

    void ler();
    return () => { atual = false; };
  }, [plugin, recarregar, tentativa]);

  if (falhou) {
    return (
      <div className="space-y-2 text-sm">
        <p role="alert" className="text-destructive">
          Não foi possível carregar as noites gravadas.
        </p>
        <button
          type="button"
          onClick={() => setTentativa((valor) => valor + 1)}
          className="rounded-lg border border-border px-3 py-1.5 font-medium"
        >
          Tentar novamente
        </button>
      </div>
    );
  }
  if (noites === null) return null;
  if (noites.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">Nenhuma noite gravada neste aparelho ainda.</p>
    );
  }

  return (
    <div className="space-y-3">
      {erroLocal && <p role="alert">{erroLocal}</p>}
      {noites.map((n) => {
        const r = resumoDaNoiteGravada(n);
        return (
          <Moldura key={n.arquivo}>
            <div className="space-y-2" data-testid={`noite-${n.arquivo}`}>
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h3 className="text-sm font-semibold text-foreground">
                  {n.ativa
                    ? "Noite em andamento"
                    : r.inicio
                      ? r.inicio.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })
                      : "Noite sem épocas gravadas"}
                </h3>
                <span className="text-xs text-muted-foreground">{rotuloDaPosicao(n.notas?.posicao)}</span>
              </div>
              <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
                <dt className="text-muted-foreground">Duração</dt>
                <dd className="tabular-nums">{r.duracaoMs > 0 ? formatarDuracao(r.duracaoMs) : "—"}</dd>
                <dt className="text-muted-foreground">Épocas</dt>
                <dd className="tabular-nums">{n.epocas}</dd>
                <dt className="text-muted-foreground">Cobertura</dt>
                <dd className="tabular-nums">
                  {r.cobertura === null ? "—" : `${Math.round(r.cobertura * 100)} %`}
                </dd>
                {!n.teste && !n.ativa && n.epocas > 0 && (
                  <>
                <dt className="text-muted-foreground">Envio</dt>
                <dd className="tabular-nums inline-flex items-center gap-1">
                  {r.enviadaPorInteiro ? (
                    <CheckCircle2 className="w-4 h-4 text-primary" aria-hidden />
                  ) : (
                    <Clock className="w-4 h-4 text-amber-500" aria-hidden />
                  )}
                  {n.enviadas} de {n.epocas}
                </dd>
                  </>
                )}
              </dl>
              {n.teste && (
                <div className="space-y-2 text-sm">
                  <p>Teste · só neste aparelho</p>
                  {!n.ativa && (
                    <div className="flex flex-wrap gap-3">
                      <button type="button" className="underline" onClick={() => void agirNoTeste(n, false)}>
                        Compartilhar arquivo
                      </button>
                      <button type="button" className="underline" onClick={() => void agirNoTeste(n, true)}>
                        Apagar gravação de teste
                      </button>
                    </div>
                  )}
                </div>
              )}
              {n.notas?.fim === "temperatura" && (
                <p className="inline-flex items-center gap-2 text-sm text-destructive" role="alert">
                  <Thermometer className="w-4 h-4" aria-hidden />
                  Encerrada sozinha: o aparelho chegou a 45 °C.
                </p>
              )}
              {!n.ativa && (
              <div className="flex flex-wrap gap-3 text-sm">
                <button
                  type="button"
                  onClick={() => setAberta(aberta === n.arquivo ? null : n.arquivo)}
                  className="underline text-muted-foreground"
                >
                  {aberta === n.arquivo ? "Fechar anotações" : "Anotações da noite"}
                </button>
                {!n.teste && n.enviadas > 0 && (
                  <Link to="/dashboard" className="underline text-primary">
                    Ver no painel
                  </Link>
                )}
              </div>
              )}
              {aberta === n.arquivo && (
                <FormularioDeNotas
                  noite={n}
                  plugin={plugin}
                  aoSalvar={(notas) =>
                    setNoites((atual) => atual?.map((x) => (x.arquivo === n.arquivo ? { ...x, notas } : x)) ?? null)
                  }
                />
              )}
            </div>
          </Moldura>
        );
      })}
    </div>
  );
}
