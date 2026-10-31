// envio_da_fila.cpp -- ver envio_da_fila.h.

#include "envio_da_fila.h"

#include "payload.h"

namespace dormio {

// Uma leitura com `f` passa de 400 B (`payload.h`); 512 da folga.
static const uint32_t TAMANHO_DA_LEITURA = 512;

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

}  // namespace dormio
