// epoca_c2.cpp -- ver epoca_c2.h.

#include "epoca_c2.h"

#include <math.h>

#include "payload.h"

namespace dormio {

Epoca epoca_da_grade(uint32_t indice, const float *gx, const float *gy, const float *gz,
                     uint32_t n, float temp_c) {
  Epoca e;
  e.indice = indice;
  e.duracao_s = DURACAO_EPOCA_BASE_S;
  e.nivel = 0;
  e.temp_pico = temp_c;
  e.amostras = static_cast<uint16_t>(n > 0xFFFFu ? 0xFFFFu : n);
  e.esperadas = e.amostras;
  if (n == 0) {
    e.flags = EPOCA_VAZIA;
    return e;
  }

  // O fator g -> m/s^2 e o mesmo `GRAVIDADE_MS2` que `classificar` usa como
  // referencia de repouso: um travesseiro parado a 1 g sai com intensidade
  // zero, e nao com o resto de 9,81 - 9,80665.
  uint32_t i_pico = 0;
  float m2_pico = -1.0f;
  for (uint32_t i = 0; i < n; i++) {
    const float m2 = gx[i] * gx[i] + gy[i] * gy[i] + gz[i] * gz[i];
    if (m2 > m2_pico) {
      m2_pico = m2;
      i_pico = i;
    }
  }
  e.pico_total = sqrtf(m2_pico) * GRAVIDADE_MS2;
  e.pico_ax = gx[i_pico] * GRAVIDADE_MS2;
  e.pico_ay = gy[i_pico] * GRAVIDADE_MS2;
  e.pico_az = gz[i_pico] * GRAVIDADE_MS2;
  return e;
}

}  // namespace dormio
