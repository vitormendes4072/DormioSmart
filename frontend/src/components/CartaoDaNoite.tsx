import { BatteryWarning, Loader2, Moon, Square, UploadCloud } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { Moldura } from "./Blueprint";
import { TelaDeConsentimento } from "./TelaDeConsentimento";
import { usePortaoDoConsentimento } from "../hooks/usePortaoDoConsentimento";
import { type EnviarLote, contarRestantes, enviarNoites } from "../lib/envioDaNoite";
import {
  type EstadoDaNoite,
  type PluginNoite,
  Noite,
  coberturaDaNoite,
  POSICOES,
  type Posicao,
  noiteInterrompida,
} from "../lib/noiteNativa";

/** De quanto em quanto tempo a tela relê o estado do serviço. */
export const INTERVALO_DE_LEITURA_MS = 5000;

/**
 * O registro da noite inteira, só no app Android (APP-02, etapas 2 e 3).
 *
 * Mínimo de propósito: iniciar, encerrar e os números que dizem se a noite
 * está sendo registrada de verdade. A tela completa é a etapa 4. Os números
 * não se escondem: a cobertura é o que mostra se o aparelho deixou o app
 * trabalhar a noite toda, e a taxa recusada mostra um sensor que o núcleo
 * não aceita.
 */
export function CartaoDaNoite({
  plugin = Noite,
  agora = () => Date.now(),
  enviar,
  aoMudar,
  consentimento,
}: {
  plugin?: PluginNoite;
  agora?: () => number;
  /**
   * Manda um lote ao servidor (etapa 3). Ausente enquanto o aparelho não tem
   * o dispositivo preparado ou a sessão: aí as épocas esperam no aparelho.
   */
  enviar?: EnviarLote;
  /** Chamado depois de iniciar, encerrar ou enviar (a lista de noites relê). */
  aoMudar?: () => void;
  /**
   * LGPD-12: com isto, "Iniciar a noite" passa antes pela tela do consentimento
   * destacado se ele não estiver vigente. Ausente, inicia direto.
   */
  consentimento?: { vigente: boolean; registrar: () => Promise<void> };
}) {
  const portao = usePortaoDoConsentimento(consentimento);
  const [estado, setEstado] = useState<EstadoDaNoite | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [restantes, setRestantes] = useState<number | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [resultado, setResultado] = useState<string | null>(null);
  const [progresso, setProgresso] = useState<{ confirmadas: number; total: number } | null>(null);
  // Etapa 4: a posição do celular entra no protocolo e é obrigatória para
  // iniciar. Uma noite sem posição anotada não serve à comparação
  // fronha × colchão, que é o que a noite real quer medir.
  const [posicao, setPosicao] = useState<Posicao | null>(null);
  const tentouAoAbrir = useRef(false);

  const ler = useCallback(async () => {
    try {
      setEstado(await plugin.estado());
    } catch {
      setErro("Não foi possível ler o estado da noite.");
    }
  }, [plugin]);

  useEffect(() => {
    void ler();
    const id = setInterval(() => void ler(), INTERVALO_DE_LEITURA_MS);
    return () => clearInterval(id);
  }, [ler]);

  const lerRestantes = useCallback(async () => {
    try {
      setRestantes(await contarRestantes(plugin));
    } catch {
      setRestantes(null);
    }
  }, [plugin]);

  const enviarAgora = useCallback(async () => {
    if (!enviar) return;
    setEnviando(true);
    setProgresso(null);
    try {
      const r = await enviarNoites(plugin, enviar, setProgresso);
      setRestantes(r.restantes);
      const partes: string[] = [];
      if (r.confirmadas > 0) partes.push(`${r.confirmadas} épocas enviadas.`);
      if (r.rejeitadas > 0) {
        partes.push(`${r.rejeitadas} recusadas pelo servidor (${r.primeiraRejeicao ?? "sem motivo"}).`);
      }
      if (r.erro) partes.push(r.erro);
      setResultado(partes.length ? partes.join(" ") : "Nada a enviar.");
      aoMudar?.();
    } catch {
      setResultado("Não foi possível ler as noites do aparelho.");
    } finally {
      setEnviando(false);
      setProgresso(null);
    }
  }, [plugin, enviar, aoMudar]);

  useEffect(() => {
    void lerRestantes();
  }, [lerRestantes]);

  // Ao abrir o app com épocas esperando e nenhuma noite em curso, envia uma vez.
  useEffect(() => {
    if (tentouAoAbrir.current || !enviar || estado === null || restantes === null) return;
    if (estado.ativa || restantes === 0) return;
    tentouAoAbrir.current = true;
    void enviarAgora();
  }, [enviar, estado, restantes, enviarAgora]);

  const agir = async (acao: () => Promise<unknown>) => {
    setOcupado(true);
    setErro(null);
    try {
      await acao();
      await ler();
      aoMudar?.();
    } catch {
      setErro("O aparelho recusou o pedido.");
    } finally {
      setOcupado(false);
    }
  };

  const interrompida = estado ? noiteInterrompida(estado) : false;
  const ativa = (estado?.ativa ?? false) && !interrompida;
  const cobertura = estado ? coberturaDaNoite(estado, agora()) : null;

  return (
    <Moldura>
      <div className="space-y-4" data-testid="cartao-da-noite">
        <div className="flex items-center gap-2">
          <Moon className="w-5 h-5 text-primary" aria-hidden />
          <h2 className="text-base font-semibold text-foreground">Registrar a noite inteira</h2>
        </div>
        <p className="text-sm text-muted-foreground">
          O registro continua com a tela apagada. Escolha onde o celular fica, inicie antes de
          dormir e encerre ao acordar.
        </p>

        {ativa ? (
          <button
            type="button"
            disabled={ocupado}
            onClick={() =>
              void agir(async () => {
                await plugin.encerrar();
                // Ao encerrar, a noite vai para a conta (etapa 3).
                await enviarAgora();
              })
            }
            className="inline-flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Square className="w-4 h-4" aria-hidden />
            Encerrar a noite
          </button>
        ) : (
          <div className="space-y-3">
          {!interrompida && (
            <fieldset className="space-y-2">
              <legend className="text-sm font-medium text-foreground">Onde o celular vai ficar?</legend>
              <div className="flex flex-wrap gap-2">
                {POSICOES.map((p) => (
                  <label
                    key={p.valor}
                    className={`inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 text-sm ${
                      posicao === p.valor ? "border-primary text-foreground" : "border-border text-muted-foreground"
                    }`}
                  >
                    <input
                      type="radio"
                      name="posicao"
                      value={p.valor}
                      checked={posicao === p.valor}
                      onChange={() => setPosicao(p.valor)}
                    />
                    {p.rotulo}
                  </label>
                ))}
              </div>
              <p className="text-xs text-muted-foreground">
                Dentro da fronha, não deixe o celular carregando: bateria abafada esquenta. Se o
                aparelho passar de 45 °C, o Dormio encerra a noite sozinho.
              </p>
            </fieldset>
          )}
          <button
            type="button"
            disabled={ocupado || estado === null || (!interrompida && posicao === null)}
            onClick={() => portao.pedir(() => agir(() => plugin.iniciar(posicao ? { posicao } : undefined)))}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {ocupado ? <Loader2 className="w-4 h-4 animate-spin" aria-hidden /> : <Moon className="w-4 h-4" aria-hidden />}
            Iniciar a noite
          </button>
          </div>
        )}

        {interrompida && (
          <div className="space-y-2">
            <p className="text-sm text-destructive" role="alert">
              O registro desta noite foi interrompido pelo aparelho. Toque em Iniciar para
              continuar no mesmo arquivo, ou encerre a noite.
            </p>
            <button
              type="button"
              disabled={ocupado}
              onClick={() => void agir(() => plugin.encerrar())}
              className="inline-flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Square className="w-4 h-4" aria-hidden />
              Encerrar a noite
            </button>
          </div>
        )}

        {enviar && restantes !== null && restantes > 0 && !ativa && (
          <div className="flex flex-wrap items-center gap-3 text-sm">
            <span className="text-muted-foreground">{restantes} épocas aguardando envio.</span>
            <button
              type="button"
              disabled={enviando}
              onClick={() => void enviarAgora()}
              className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-1.5 font-medium"
            >
              {enviando ? <Loader2 className="w-4 h-4 animate-spin" aria-hidden /> : <UploadCloud className="w-4 h-4" aria-hidden />}
              Enviar agora
            </button>
          </div>
        )}

        {enviando && progresso && (
          <p className="text-sm text-muted-foreground" aria-live="polite">
            Enviando: {progresso.confirmadas} de {progresso.total} épocas. Mantenha o app aberto.
          </p>
        )}

        {resultado && !enviando && (
          <p className="text-sm text-muted-foreground" role="status">
            {resultado}
          </p>
        )}

        {portao.telaAberta && (
          <TelaDeConsentimento aoConcordar={portao.concordar} aoRecusar={portao.recusar} erro={portao.erro} />
        )}

        {erro && (
          <p className="text-sm text-destructive" role="alert">
            {erro}
          </p>
        )}

        {estado && !ativa && !interrompida && estado.epocasGravadas > 0 && (
          <h3 className="text-sm font-semibold text-foreground">Última noite</h3>
        )}
        {estado && (estado.ativa || estado.epocasGravadas > 0) && (
          <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
            <dt className="text-muted-foreground">Épocas gravadas</dt>
            <dd className="tabular-nums">{estado.epocasGravadas}</dd>
            <dt className="text-muted-foreground">Cobertura</dt>
            <dd className="tabular-nums">
              {cobertura === null ? "—" : `${Math.round(cobertura * 100)} %`}
            </dd>
            <dt className="text-muted-foreground">Taxa do sensor</dt>
            <dd className="tabular-nums">{estado.taxaHz > 0 ? `${estado.taxaHz.toFixed(1)} Hz` : "—"}</dd>
            <dt className="text-muted-foreground">Recusadas por taxa</dt>
            <dd className="tabular-nums">{estado.recusadasPorTaxa}</dd>
            <dt className="text-muted-foreground">Retomadas</dt>
            <dd className="tabular-nums">{estado.retomadas}</dd>
            {estado.temperaturaC !== undefined && (
              <>
                <dt className="text-muted-foreground">Temperatura do aparelho</dt>
                <dd className="tabular-nums">{estado.temperaturaC.toFixed(1)} °C</dd>
              </>
            )}
          </dl>
        )}

        {estado && estado.recusadasPorTaxa > 0 && estado.epocasGravadas === 0 && (
          <p className="text-sm text-destructive" role="alert">
            O sensor deste aparelho está fora da taxa que o Dormio aceita (40 a 60 Hz). As épocas
            estão sendo recusadas.
          </p>
        )}

        {estado && !estado.isentoDeBateria && (
          <button
            type="button"
            disabled={ocupado}
            onClick={() => void agir(() => plugin.pedirIsencaoDeBateria())}
            className="inline-flex items-center gap-2 text-sm text-amber-600 underline"
          >
            <BatteryWarning className="w-4 h-4" aria-hidden />
            Permitir que o Dormio funcione com a economia de bateria
          </button>
        )}
      </div>
    </Moldura>
  );
}
