import type { serieDaSemana } from "../lib/calendarioDoSono";
import { projetarMeta, tempoDaMeta } from "../lib/metaDiaria";

export function ComparacaoDaMeta({ serie, meta, hoje, parcial, orientacao }: {
  serie: ReturnType<typeof serieDaSemana>;
  meta: number;
  hoje: Date;
  parcial: boolean;
  orientacao?: "travesseiro" | "app";
}) {
  const projecao = projetarMeta(serie, meta, hoje, parcial);
  const dias = serie.comRegistro.length;
  const dica = orientacao === "travesseiro" ? "Para registrar o repouso inteiro, deixe o travesseiro ligado."
    : orientacao === "app" ? "Para registrar o repouso inteiro, inicie a sessão no app antes de se deitar." : null;
  const mensagem = projecao?.tipo === "atingida" ? "A média da semana está na meta."
    : projecao?.tipo === "fora-do-alcance" ? "Nesta semana, a média não chega mais à meta."
    : projecao?.tipo === "possivel"
      ? `${projecao.restantes === 1 ? "No dia que resta" : `Nos ${projecao.restantes} dias que restam`}, cerca de ${tempoDaMeta(projecao.porDia)} registradas por dia levariam a média à meta.`
      : null;

  return (
    <div className="mt-2 space-y-1 rounded-lg bg-secondary/60 p-2 text-xs text-muted-foreground">
      <p>
        {serie.media === null ? "Sem média nesta semana" : `Média dos dias com registro: ${tempoDaMeta(serie.media / 60_000)} (em ${dias} ${dias === 1 ? "dia" : "dias"})`}
        {" · "}<strong>Sua meta: {tempoDaMeta(meta)}</strong>
      </p>
      {mensagem && <p>{mensagem}</p>}
      {dica && <p>{dica}</p>}
    </div>
  );
}
