import { useMemo, useState } from "react";

import type { EstadoDaNoite, NoiteGravada, PluginNoite } from "../lib/noiteNativa";
import { ConteudoDaNoite } from "./Noite";

const CENARIOS = {
  parada: "Parada",
  gravando: "Gravando",
  interrompida: "Interrompida",
  encerrada: "Encerrada",
  bateria: "Sem isenção de bateria",
  lista: "Lista de noites",
} as const;

type Cenario = keyof typeof CENARIOS;

function criarPlugin(cenario: Cenario): PluginNoite {
  const ativa = cenario === "gravando" || cenario === "interrompida";
  const encerrada = cenario === "encerrada";
  const agora = Date.now();
  const duracao = (encerrada ? 7 * 60 + 32 : 2 * 60 + 18) * 60_000;
  let estado: EstadoDaNoite = {
    ativa,
    rodando: cenario === "gravando",
    inicioUtcMs: ativa || encerrada ? agora - duracao : 0,
    ultimaEpocaUtcMs: ativa || encerrada ? agora : 0,
    epocasGravadas: encerrada ? 876 : ativa ? 264 : 0,
    isentoDeBateria: cenario !== "bateria",
    taxaHz: ativa || encerrada ? 50 : 0,
    recusadas: 0,
    recusadasPorTaxa: 0,
    semFeatures: 0,
    amostras: 0,
    retomadas: 0,
  };
  const inicioDaEnviada = encerrada ? estado.inicioUtcMs : agora - 2 * 86400_000;
  const enviada: NoiteGravada = {
    arquivo: "enviada",
    epocas: 876,
    enviadas: 876,
    primeiraTs: new Date(inicioDaEnviada).toISOString(),
    ultimaTs: new Date(inicioDaEnviada + 452 * 60_000 - 30_000).toISOString(),
    notas: { posicao: "fronha" },
  };
  let noites: NoiteGravada[] = cenario === "lista" ? [
    enviada,
    { ...enviada, arquivo: "teste", epocas: 8, enviadas: 0, teste: true,
      ultimaTs: new Date(inicioDaEnviada + 210_000).toISOString() },
    { ...enviada, arquivo: "em-andamento", ativa: true, enviadas: 0, notas: { posicao: "colchao" } },
  ] : encerrada ? [enviada] : [];

  return {
    estado: async () => ({ ...estado }),
    noites: async () => ({ noites }),
    iniciar: async () => {
      estado = { ...estado, ativa: true, rodando: true,
        inicioUtcMs: estado.ativa ? estado.inicioUtcMs : Date.now(),
        epocasGravadas: estado.ativa ? estado.epocasGravadas : 0 };
      return { notificacoes: true };
    },
    encerrar: async () => {
      estado = { ...estado, ativa: false, rodando: false, ultimaEpocaUtcMs: Date.now() };
    },
    pedirIsencaoDeBateria: async () => {
      estado = { ...estado, isentoDeBateria: true };
      return { isentoDeBateria: true };
    },
    compartilharTeste: async () => {},
    apagarTeste: async ({ arquivo }) => { noites = noites.filter((noite) => noite.arquivo !== arquivo); },
    salvarNotas: async ({ arquivo, notas }) => {
      noites = noites.map((noite) => noite.arquivo === arquivo ? { ...noite, notas: { ...noite.notas, ...notas } } : noite);
      return noites.find((noite) => noite.arquivo === arquivo)?.notas ?? notas;
    },
    lerEpocas: async () => ({ epocas: [] }),
    marcarEnviadas: async () => ({ enviadas: 0 }),
    lembrete: async () => ({ ativo: false, hora: 22, minuto: 0, notificacoes: true }),
    definirLembrete: async (valor) => ({ ...valor, notificacoes: true }),
  };
}

export default function NoiteDemo() {
  const [cenario, setCenario] = useState<Cenario>("parada");
  const plugin = useMemo(() => criarPlugin(cenario), [cenario]);

  return (
    <div className="space-y-4">
      <label className="flex flex-wrap items-center gap-2 text-sm font-medium">
        Cenário da demonstração
        <select
          className="rounded-lg border border-border bg-card px-2 py-1.5"
          value={cenario}
          onChange={(evento) => setCenario(evento.target.value as Cenario)}
        >
          {Object.entries(CENARIOS).map(([valor, rotulo]) => (
            <option key={valor} value={valor}>{rotulo}</option>
          ))}
        </select>
      </label>
      <ConteudoDaNoite key={cenario} disponivel plugin={plugin} />
    </div>
  );
}
