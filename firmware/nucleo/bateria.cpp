// bateria.cpp -- ver bateria.h.

#include "bateria.h"

#include <stdio.h>

namespace dormio {

uint32_t tensao_da_bateria_mv(const uint32_t *amostras_mv, uint32_t n) {
  if (amostras_mv == 0 || n == 0) return 0;
  uint64_t soma = 0;
  for (uint32_t i = 0; i < n; i++) soma += amostras_mv[i];
  return static_cast<uint32_t>((soma + n / 2) / n) * DIVISOR_DA_BATERIA;
}

EstadoDaBateria classificar_bateria(uint32_t tensao_mv, EstadoDaBateria anterior) {
  if (tensao_mv < BATERIA_MINIMA_PLAUSIVEL_MV) return BATERIA_INDISPONIVEL;
  // Limites para ENTRAR num estado pior; para sair dele, a histerese.
  uint32_t limite_critica = BATERIA_CRITICA_MV;
  uint32_t limite_baixa = BATERIA_BAIXA_MV;
  if (anterior == BATERIA_CRITICA) limite_critica += HISTERESE_DA_BATERIA_MV;
  if (anterior == BATERIA_CRITICA || anterior == BATERIA_BAIXA) {
    limite_baixa += HISTERESE_DA_BATERIA_MV;
  }
  if (tensao_mv < limite_critica) return BATERIA_CRITICA;
  if (tensao_mv < limite_baixa) return BATERIA_BAIXA;
  return BATERIA_OK;
}

const char *nome_do_estado(EstadoDaBateria estado) {
  switch (estado) {
    case BATERIA_OK:
      return "ok";
    case BATERIA_BAIXA:
      return "baixa";
    case BATERIA_CRITICA:
      return "critica";
    default:
      return "indisponivel";
  }
}

uint32_t formatar_bateria(uint32_t repouso_mv, uint32_t envio_mv, EstadoDaBateria estado,
                          char *destino, uint32_t tamanho) {
  if (destino == 0 || tamanho == 0) return 0;
  int n;
  if (estado == BATERIA_INDISPONIVEL) {
    n = snprintf(destino, tamanho,
                 "[bateria] indisponivel: %u mV em repouso (sem divisor no GPIO35?)",
                 static_cast<unsigned>(repouso_mv));
  } else {
    n = snprintf(destino, tamanho, "[bateria] %u mV em repouso, %u mV no envio (%s)",
                 static_cast<unsigned>(repouso_mv), static_cast<unsigned>(envio_mv),
                 nome_do_estado(estado));
  }
  if (n < 0 || static_cast<uint32_t>(n) >= tamanho) {
    destino[0] = '\0';
    return 0;
  }
  return static_cast<uint32_t>(n);
}

}  // namespace dormio
