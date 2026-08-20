/**
 * Exportacao das leituras em CSV.
 *
 * Serve a dois propositos: o usuario levar embora o proprio dado (LGPD, e a
 * secao "Conta e Privacidade" promete isso) e a analise externa — planilha, R,
 * Python — que e o caminho natural para o trabalho de validacao do TCC.
 */
import { ehMovimento, intensidade, type LeituraSono } from "../types/sleep";

export const COLUNAS = [
  "created_at",
  "movimento_total",
  "intensidade",
  "temp_chip",
  "status",
  "movimento",
] as const;

/**
 * Escapa um campo para CSV (RFC 4180).
 *
 * Necessario de verdade: `status` e texto livre vindo do dispositivo. Um
 * rotulo com virgula — "Movimento Detectado!" ja tem pontuacao — quebraria o
 * alinhamento das colunas em qualquer planilha.
 */
function escapar(valor: string | number | null): string {
  if (valor === null || valor === undefined) return "";
  const texto = String(valor);
  if (/[",\r\n]/.test(texto)) {
    return `"${texto.replace(/"/g, '""')}"`;
  }
  return texto;
}

export function gerarCsv(leituras: LeituraSono[]): string {
  const linhas = [COLUNAS.join(",")];

  for (const leitura of leituras) {
    const valor = intensidade(leitura);
    linhas.push(
      [
        escapar(leitura.created_at),
        escapar(leitura.movimento_total),
        // Intensidade e derivada, nao vem do banco. Vai junto por conveniencia
        // de quem analisa — e a coluna que realmente interessa na actigrafia.
        escapar(valor === null ? null : valor.toFixed(4)),
        escapar(leitura.temp),
        escapar(leitura.status),
        escapar(ehMovimento(leitura.status) ? "1" : "0"),
      ].join(","),
    );
  }

  // CRLF conforme a RFC; e o que o Excel espera.
  return linhas.join("\r\n");
}

export function nomeDoArquivo(agora: Date = new Date()): string {
  const p = (n: number) => String(n).padStart(2, "0");
  const data = `${agora.getFullYear()}-${p(agora.getMonth() + 1)}-${p(agora.getDate())}`;
  const hora = `${p(agora.getHours())}${p(agora.getMinutes())}`;
  return `dormio-smart-leituras-${data}-${hora}.csv`;
}

/** Dispara o download no navegador. */
export function baixarCsv(leituras: LeituraSono[]) {
  // BOM UTF-8: sem ele o Excel no Windows abre "Terça" como "TerÃ§a".
  const conteudo = "﻿" + gerarCsv(leituras);
  const blob = new Blob([conteudo], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);

  const link = document.createElement("a");
  link.href = url;
  link.download = nomeDoArquivo();
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  // Libera a memoria do blob; sem isso ele fica retido ate a aba fechar.
  URL.revokeObjectURL(url);
}
