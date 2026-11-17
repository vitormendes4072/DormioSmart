// envio_da_fila.cpp -- ver envio_da_fila.h.

#include "envio_da_fila.h"

#include <stdio.h>

#include "payload.h"

namespace dormio {

// O rascunho de uma leitura, na pilha de quem chama. O pior caso e
// `PIOR_LEITURA_BYTES` (341 B medidos no teste); 512 da folga.
static const uint32_t TAMANHO_DA_LEITURA = 512;
static_assert(PIOR_LEITURA_BYTES < TAMANHO_DA_LEITURA, "o rascunho nao cabe o pior caso");

PreparoDoLote preparar_lote(FilaNaFlash *fila, const ResolucaoDeParede &parede,
                            RegistroDeEpoca *rascunho, uint32_t max, char *destino,
                            uint32_t tamanho) {
  PreparoDoLote p;
  p.no_lote = 0;
  p.descartados = 0;
  p.tamanho = 0;
  if (max > MAX_LEITURAS_POR_LOTE) max = MAX_LEITURAS_POR_LOTE;

  MontadorDeLote lote(destino, tamanho);
  const uint32_t n = fila->ler_pendentes(rascunho, max);
  for (uint32_t i = 0; i < n; i++) {
    char leitura[TAMANHO_DA_LEITURA];
    uint32_t escritos = 0;
    const ResultadoDeMontagem r = montar_payload_do_registro(
        rascunho[i], fila->sessao(), parede, leitura, sizeof(leitura), &escritos);
    if (r != PAYLOAD_OK) {
      // Na frente da fila: nunca sera enviavel, sai e e contado. Atras de uma
      // leitura ja no lote: o lote para aqui, e ele chega a frente depois.
      if (lote.quantidade() == 0 && r != PAYLOAD_BUFFER_PEQUENO) {
        if (fila->confirmar(1) == 1) p.descartados++;
        continue;
      }
      break;
    }
    if (!lote.adicionar(leitura, escritos)) break;
  }
  p.no_lote = lote.quantidade();
  p.tamanho = lote.fechar();
  return p;
}

DecisaoDoLote aplicar_resposta(FilaNaFlash *fila, int status_http, const char *corpo,
                               uint32_t tamanho, uint32_t enviadas) {
  DecisaoDoLote d = interpretar_resposta_do_lote(status_http, corpo, tamanho, enviadas);
  if (d.acao == LOTE_CONFIRMAR && d.confirmar > 0) fila->confirmar(d.confirmar);
  return d;
}

uint32_t formatar_folga(const FolgaDeMemoria &f, char *destino, uint32_t tamanho) {
  if (destino == 0 || tamanho == 0) return 0;
  const int n = snprintf(destino, tamanho,
                         "[memoria] heap %u (minimo %u); maior bloco %u antes, %u depois; "
                         "pilha livre: envio %u de %u B, medicao %u de %u B; "
                         "maior lote %u de %u B; %u conexoes TLS para %u lotes",
                         static_cast<unsigned>(f.heap_livre), static_cast<unsigned>(f.heap_minimo),
                         static_cast<unsigned>(f.maior_bloco_antes),
                         static_cast<unsigned>(f.maior_bloco_depois),
                         static_cast<unsigned>(f.pilha_envio_livre),
                         static_cast<unsigned>(f.pilha_envio_total),
                         static_cast<unsigned>(f.pilha_medicao_livre),
                         static_cast<unsigned>(f.pilha_medicao_total),
                         static_cast<unsigned>(f.maior_lote), static_cast<unsigned>(f.buffer_do_lote),
                         static_cast<unsigned>(f.conexoes_tls), static_cast<unsigned>(f.lotes));
  if (n < 0 || static_cast<uint32_t>(n) >= tamanho) {
    destino[0] = '\0';
    return 0;
  }
  uint32_t usado = static_cast<uint32_t>(n);
  if (f.pilha_envio_livre < LIMIAR_DE_PILHA_BAIXA_BYTES ||
      f.pilha_medicao_livre < LIMIAR_DE_PILHA_BAIXA_BYTES) {
    const int m = snprintf(destino + usado, tamanho - usado, "; PILHA BAIXA");
    if (m < 0 || usado + static_cast<uint32_t>(m) >= tamanho) {
      destino[0] = '\0';
      return 0;
    }
    usado += static_cast<uint32_t>(m);
  }
  return usado;
}

}  // namespace dormio
