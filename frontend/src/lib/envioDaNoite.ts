import type { RespostaDoLote } from "./coleta";
import type { PluginNoite } from "./noiteNativa";

/**
 * O envio das noites gravadas no aparelho (APP-02, etapa 3).
 *
 * O serviço nativo grava cada época numa linha do arquivo da noite; este laço
 * lê de 60 em 60 (o teto do lote, `web-app/lote.py`), manda pelo
 * `POST /api/data/lote` e grava até onde o servidor confirmou.
 *
 * ── A REGRA DO PONTO ────────────────────────────────────────────────────
 *
 * O ponto só avança até a última época de um PREFIXO resolvido: aceita
 * (gravada) ou rejeitada (inválida; reenviar não adianta, como o firmware).
 * A primeira pendente para tudo, e ela e as seguintes ficam para a próxima
 * vez. Avançar por cima de uma pendente perderia a época em silêncio; parar
 * antes de uma aceita só a reenvia, e o servidor deduplica (migração 011).
 * Errar para o lado do reenvio é de graça; para o lado da perda, não.
 *
 * Nada é marcado antes da resposta: sem rede, com sessão vencida ou com o
 * servidor fora, o ponto fica onde estava.
 */

export type FonteDaNoite = Pick<PluginNoite, "noites" | "lerEpocas" | "marcarEnviadas">;

export type EnviarLote = (leituras: object[]) => Promise<RespostaDoLote>;

export type ResultadoDoEnvio = {
  /** Épocas confirmadas neste envio (aceitas + rejeitadas). */
  confirmadas: number;
  rejeitadas: number;
  /** O motivo da primeira rejeição, para a tela. */
  primeiraRejeicao: string | null;
  /** Épocas que ainda faltam enviar, em todas as noites. */
  restantes: number;
  /** Por que o envio parou antes do fim, ou null se foi até o fim. */
  erro: string | null;
};

/** Quantas épocas do começo do lote estão resolvidas (aceitas ou rejeitadas). */
export function prefixoResolvido(r: RespostaDoLote, tamanho: number): number {
  const resolvidas = new Set<number>(r.aceitas);
  for (const x of r.rejeitadas) resolvidas.add(x.indice);
  let k = 0;
  while (k < tamanho && resolvidas.has(k)) k++;
  return k;
}

export async function contarRestantes(fonte: FonteDaNoite): Promise<number> {
  const { noites } = await fonte.noites();
  return noites.reduce((s, n) => s + Math.max(0, n.epocas - n.enviadas), 0);
}

export async function enviarNoites(fonte: FonteDaNoite, enviar: EnviarLote): Promise<ResultadoDoEnvio> {
  const r: ResultadoDoEnvio = { confirmadas: 0, rejeitadas: 0, primeiraRejeicao: null, restantes: 0, erro: null };
  const { noites } = await fonte.noites();

  envio: for (const noite of noites) {
    let ponto = noite.enviadas;
    while (ponto < noite.epocas) {
      const { epocas } = await fonte.lerEpocas({ arquivo: noite.arquivo, de: ponto });
      if (epocas.length === 0) break;
      // Cada linha foi montada pelo núcleo e gravada inteira; uma que não
      // seja JSON vai como está e o servidor a rejeita com o motivo.
      const leituras: object[] = epocas.map((linha) => {
        try {
          return JSON.parse(linha) as object;
        } catch {
          return { linha_ilegivel: linha };
        }
      });

      let resposta: RespostaDoLote;
      try {
        resposta = await enviar(leituras);
      } catch (e) {
        r.erro = e instanceof Error ? e.message : "Falha ao enviar.";
        break envio;
      }

      const k = prefixoResolvido(resposta, leituras.length);
      for (const x of resposta.rejeitadas) {
        if (x.indice < k) {
          r.rejeitadas++;
          if (r.primeiraRejeicao === null) r.primeiraRejeicao = x.erro;
        }
      }
      if (k > 0) {
        ponto = (await fonte.marcarEnviadas({ arquivo: noite.arquivo, ate: ponto + k })).enviadas;
        r.confirmadas += k;
      }
      if (k < leituras.length) {
        r.erro = `${leituras.length - k} épocas ficaram pendentes no servidor. Tente de novo em instantes.`;
        break envio;
      }
    }
  }

  r.restantes = await contarRestantes(fonte);
  return r;
}
