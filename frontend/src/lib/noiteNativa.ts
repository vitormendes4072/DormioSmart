import { Capacitor, registerPlugin } from "@capacitor/core";

/**
 * O registro da noite inteira pelo app Android (APP-02, etapa 2).
 *
 * O navegador não registra a noite: o sensor para quando a tela bloqueia
 * (`useColeta.ts`). No app, quem registra é um serviço nativo
 * (`android/.../ServicoDaNoite.java`), e esta tela só o liga, desliga e lê o
 * estado pelo plugin "Noite". No site, nada disto aparece.
 *
 * A interface não tem nada de Android: um app iOS (`APP-04`) implementaria o
 * mesmo plugin.
 */

export type EstadoDaNoite = {
  ativa: boolean;
  /**
   * Se o serviço está de fato registrando. `ativa` vem do arquivo de estado e
   * sobrevive à morte do serviço; `rodando` não. Ativa sem rodar é uma noite
   * interrompida (forçada a parar, sem retomada do sistema).
   */
  rodando: boolean;
  inicioUtcMs: number;
  epocasGravadas: number;
  recusadas: number;
  recusadasPorTaxa: number;
  semFeatures: number;
  amostras: number;
  /** Taxa medida pela cadeia na última época pronta; 0 antes da primeira. */
  taxaHz: number;
  /** Quantas vezes o sistema matou o serviço e ele voltou. */
  retomadas: number;
  ultimaEpocaUtcMs: number;
  temperaturaC?: number;
  isentoDeBateria: boolean;
};

/** Uma noite gravada no aparelho e quanto dela o servidor já confirmou (etapa 3). */
export type NoiteGravada = { arquivo: string; epocas: number; enviadas: number };

export interface PluginNoite {
  iniciar(): Promise<{ notificacoes: boolean }>;
  encerrar(): Promise<void>;
  estado(): Promise<EstadoDaNoite>;
  pedirIsencaoDeBateria(): Promise<{ isentoDeBateria: boolean }>;
  noites(): Promise<{ noites: NoiteGravada[] }>;
  /** Até 60 épocas, como o texto JSON que o núcleo montou. */
  lerEpocas(o: { arquivo: string; de: number }): Promise<{ epocas: string[] }>;
  /** O ponto só avança; devolve o que ficou gravado. */
  marcarEnviadas(o: { arquivo: string; ate: number }): Promise<{ enviadas: number }>;
}

export const Noite = registerPlugin<PluginNoite>("Noite");

type Plataforma = Pick<typeof Capacitor, "isNativePlatform" | "isPluginAvailable">;

/** A noite foi interrompida: o estado diz ativa, mas o serviço não roda. */
export function noiteInterrompida(e: EstadoDaNoite): boolean {
  return e.ativa && !e.rodando;
}

/** Só dentro do app, e só se o plugin nativo existe. */
export function noiteNativaDisponivel(plataforma: Plataforma = Capacitor): boolean {
  return plataforma.isNativePlatform() && plataforma.isPluginAvailable("Noite");
}

/** A época 0 começa 3 s depois da primeira amostra (`ANTECEDENCIA_DA_ORIGEM_US`). */
export const ANTECEDENCIA_DA_ORIGEM_MS = 3000;
export const DURACAO_DA_EPOCA_MS = 30_000;
/**
 * A cadeia só fecha uma época quando já tem 2,5 s de sinal depois dela
 * (`MARGEM_S` + `FOLGA_DO_AJUSTE_S`) e a drenagem seguinte chegou (até 1,7 s).
 */
export const ATRASO_DE_FECHAMENTO_MS = 4200;

/**
 * Épocas gravadas sobre as que já deveriam ter fechado, de 0 a 1.
 *
 * É o número que diz se o aparelho deixou o app trabalhar a noite toda: um
 * fabricante que mata o serviço de madrugada aparece aqui como cobertura
 * baixa, e não como uma noite "tranquila". `null` antes de a primeira época
 * poder ter fechado.
 */
export function coberturaDaNoite(e: EstadoDaNoite, agoraMs: number): number | null {
  if (e.inicioUtcMs <= 0) return null;
  const decorrido = agoraMs - e.inicioUtcMs - ANTECEDENCIA_DA_ORIGEM_MS - ATRASO_DE_FECHAMENTO_MS;
  const esperadas = Math.floor(decorrido / DURACAO_DA_EPOCA_MS);
  if (esperadas <= 0) return null;
  return Math.min(1, e.epocasGravadas / esperadas);
}
