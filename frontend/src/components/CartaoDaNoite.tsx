import { BatteryWarning, Loader2, Moon, Square } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { Moldura } from "./Blueprint";
import { type EstadoDaNoite, type PluginNoite, Noite, coberturaDaNoite } from "../lib/noiteNativa";

/** De quanto em quanto tempo a tela relê o estado do serviço. */
export const INTERVALO_DE_LEITURA_MS = 5000;

/**
 * O registro da noite inteira, só no app Android (APP-02, etapa 2).
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
}: {
  plugin?: PluginNoite;
  agora?: () => number;
}) {
  const [estado, setEstado] = useState<EstadoDaNoite | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

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

  const agir = async (acao: () => Promise<unknown>) => {
    setOcupado(true);
    setErro(null);
    try {
      await acao();
      await ler();
    } catch {
      setErro("O aparelho recusou o pedido.");
    } finally {
      setOcupado(false);
    }
  };

  const ativa = estado?.ativa ?? false;
  const cobertura = estado ? coberturaDaNoite(estado, agora()) : null;

  return (
    <Moldura>
      <div className="space-y-4" data-testid="cartao-da-noite">
        <div className="flex items-center gap-2">
          <Moon className="w-5 h-5 text-primary" aria-hidden />
          <h2 className="text-base font-semibold text-foreground">Registrar a noite inteira</h2>
        </div>
        <p className="text-sm text-muted-foreground">
          O registro continua com a tela apagada. Deixe o celular carregando e apoiado no lugar
          combinado para a noite.
        </p>

        {ativa ? (
          <button
            type="button"
            disabled={ocupado}
            onClick={() => void agir(() => plugin.encerrar())}
            className="inline-flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm font-medium"
          >
            <Square className="w-4 h-4" aria-hidden />
            Encerrar a noite
          </button>
        ) : (
          <button
            type="button"
            disabled={ocupado || estado === null}
            onClick={() => void agir(() => plugin.iniciar())}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
          >
            {ocupado ? <Loader2 className="w-4 h-4 animate-spin" aria-hidden /> : <Moon className="w-4 h-4" aria-hidden />}
            Iniciar a noite
          </button>
        )}

        {erro && (
          <p className="text-sm text-destructive" role="alert">
            {erro}
          </p>
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
