import { Check, Layers } from "lucide-react";
import { useId } from "react";
import { Link } from "react-router";

import {
  classificarUltimoEnvio,
  descreverUltimoContato,
  estaAtivo,
  estadoDoDispositivo,
  precisaEscolherDispositivo,
  type Dispositivo,
} from "../lib/dispositivos";
import { EstadoDoDispositivo, IconeDoDispositivo } from "./CartaoDeDispositivo";

const LINHA = "flex w-full min-w-0 items-center gap-2.5 rounded-xl border border-transparent px-2 py-2 text-left hover:bg-secondary aria-pressed:border-primary/30 aria-pressed:bg-primary/10 focus-visible:outline-2 focus-visible:outline-ring";

export function ResumoDeDispositivos({
  dispositivos, selecionado, aoSelecionar, destinoGerenciar, destinoParear, listaConhecida = true, className, classeDoLink,
}: {
  dispositivos: Dispositivo[];
  selecionado: string | null;
  aoSelecionar: (id: string | null) => void;
  destinoGerenciar: string;
  destinoParear?: string;
  listaConhecida?: boolean;
  className: string;
  classeDoLink: string;
}) {
  const disponiveis = dispositivos.filter(estaAtivo);
  const podeEscolher = precisaEscolherDispositivo(dispositivos);
  const detalhado = selecionado === null
    ? (disponiveis.length === 1 ? disponiveis[0] : undefined)
    : dispositivos.find((item) => item.id === selecionado);

  return (
    <aside id="resumo-dispositivo" aria-label="Resumo do dispositivo" className={`flex min-w-0 flex-col gap-3 ${className}`}>
      <h2 className="text-base font-extrabold tracking-tight text-foreground">Seu dispositivo</h2>
      {(podeEscolher || disponiveis.length > 0) && (
        <ul aria-label="Dispositivos disponíveis" className="space-y-1">
          {podeEscolher && (
            <li>
              <button type="button" aria-pressed={selecionado === null} onClick={() => aoSelecionar(null)} className={LINHA}>
                <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-primary/10 text-primary">
                  <Layers className="size-4" aria-hidden />
                </span>
                <span className="flex-1 text-sm font-semibold">Todos os dispositivos</span>
                {selecionado === null && <Check className="size-4 shrink-0 text-primary" aria-hidden />}
              </button>
            </li>
          )}
          {disponiveis.map((item) => (
            <LinhaDeDispositivo
              key={item.id}
              dispositivo={item}
              selecionado={selecionado === item.id}
              aoSelecionar={podeEscolher ? aoSelecionar : undefined}
            />
          ))}
        </ul>
      )}
      {detalhado && (
        <div className="border-t border-border pt-3">
          {!estaAtivo(detalhado) && <p className="mb-1 break-words text-sm font-semibold">{detalhado.nome}</p>}
          <DetalhesDoEnvio dispositivo={detalhado} />
        </div>
      )}
      {listaConhecida && disponiveis.length === 0 && !detalhado && (
        <p className="text-sm text-muted-foreground">{destinoParear ? "Nenhum aparelho conectado ainda." : "Nenhum dispositivo disponível para detalhar."}</p>
      )}
      <Link to={destinoParear ?? destinoGerenciar} className={`mt-auto self-start ${destinoParear
        ? "inline-flex min-h-11 items-center rounded-lg bg-primary px-3 text-sm font-semibold text-primary-foreground hover:bg-primary/90 focus-visible:outline-2 focus-visible:outline-ring"
        : classeDoLink}`}>
        {destinoParear ? "Parear o travesseiro" : "Gerenciar dispositivos"}
      </Link>
    </aside>
  );
}

function LinhaDeDispositivo({
  dispositivo, selecionado, aoSelecionar,
}: {
  dispositivo: Dispositivo;
  selecionado: boolean;
  aoSelecionar?: (id: string) => void;
}) {
  const nome = useId();
  const descricao = useId();
  const horario = classificarUltimoEnvio(dispositivo) === "Horário indisponível"
    ? "Horário indisponível"
    : descreverUltimoContato(dispositivo, "longo");
  const conteudo = (
    <>
      <IconeDoDispositivo tipo={dispositivo.tipo} />
      <span className="min-w-0 flex-1 space-y-1">
        <span id={nome} className="block break-words text-sm font-semibold">{dispositivo.nome}</span>
        <span id={descricao} className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <EstadoDoDispositivo estado={estadoDoDispositivo(dispositivo)} />
          <span className="text-xs text-muted-foreground">
            {dispositivo.last_seen_at ? <><span className="sr-only">Último envio </span>{horario}</> : "Nunca enviou dados"}
          </span>
        </span>
      </span>
      {selecionado && <Check className="size-4 shrink-0 text-primary" aria-hidden />}
    </>
  );
  return (
    <li>
      {aoSelecionar ? (
        <button
          type="button"
          aria-labelledby={nome}
          aria-describedby={descricao}
          aria-pressed={selecionado}
          onClick={() => aoSelecionar(dispositivo.id)}
          className={LINHA}
        >
          {conteudo}
        </button>
      ) : (
        <span className="flex min-w-0 items-center gap-2.5 px-2 py-2">{conteudo}</span>
      )}
    </li>
  );
}

function DetalhesDoEnvio({ dispositivo }: { dispositivo: Dispositivo }) {
  const estado = classificarUltimoEnvio(dispositivo);

  return (
    <dl className="space-y-1 text-sm">
      <dt className="text-muted-foreground">Último envio</dt>
      <dd className="flex flex-wrap items-center gap-2">
        {dispositivo.last_seen_at && estado !== "Horário indisponível" && (
          <span className="font-medium text-foreground">{descreverUltimoContato(dispositivo)}</span>
        )}
        <span className={`rounded-full px-2 py-1 text-xs font-semibold ${estado === "Enviou recentemente"
          ? "bg-emerald-500/10 text-emerald-800 dark:text-emerald-300"
          : "bg-secondary text-muted-foreground"}`}>
          {estado}
        </span>
      </dd>
    </dl>
  );
}
