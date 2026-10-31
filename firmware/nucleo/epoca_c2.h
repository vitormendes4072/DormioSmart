// epoca_c2.h -- a `Epoca` de uma epoca da cadeia C2 (FW-07 (b)).
//
// ── A LACUNA QUE ISTO FECHA ────────────────────────────────────────────
//
// A cadeia C2 (`cadeia_c2.h`) entrega 960 pontos em g por epoca, e deles saem
// as features. Mas o payload do contrato tambem leva `ax/ay/az/total/t` -- o
// pico da epoca em m/s^2 e a temperatura --, e quem os produzia era o
// `AcumuladorDeEpoca`, que recebe amostras soltas do caminho antigo. Na C2
// ninguem montava a `Epoca`. Este arquivo monta, a partir da mesma grade.
//
// ── O PICO E O DA GRADE, NAO O DA LEITURA BRUTA ────────────────────────
//
// A grade ja passou pelo anti-aliasing de 12,8 Hz e foi reamostrada para
// 32 Hz: um pico de 1 a 2 amostras brutas a 50 Hz chega atenuado. E uma
// diferenca declarada em relacao ao caminho antigo, e a escolha certa para a
// C2: o `total` passa a descrever o MESMO sinal de que saem as features, em
// vez de um sinal paralelo que nenhuma feature ve.
//
// ── A TEMPERATURA ──────────────────────────────────────────────────────
//
// A FIFO da C2 so leva o acelerometro (`C2_FIFO_EN`). A temperatura e lida
// do registrador uma vez, quando a epoca fecha -- e nao "no instante do
// pico", como no caminho antigo. A temperatura do chip varia em minutos, nao
// em segundos; a diferenca nao e observavel numa epoca de 30 s.

#ifndef DORMIO_NUCLEO_EPOCA_C2_H
#define DORMIO_NUCLEO_EPOCA_C2_H

#include <stdint.h>

#include "epoca.h"

namespace dormio {

// TEMP_OUT_H; TEMP_OUT_L e o seguinte (0x42). int16 big-endian.
const uint8_t MPU_REG_TEMP_OUT_H = 0x41;

// Folha do MPU6050 (registro 0x41-0x42): T = bruto / 340 + 36,53 graus C.
inline float temperatura_mpu_c(int16_t bruto) {
  return static_cast<float>(bruto) / 340.0f + 36.53f;
}

// Monta a `Epoca` de uma epoca PRONTA da cadeia: o indice na grade de 30 s, o
// pico da magnitude (em m/s^2) e os tres eixos da amostra de pico, a
// temperatura, e `amostras` = `esperadas` = `n`. Com `n` == 0 a epoca sai
// vazia (EPOCA_VAZIA) -- nao ha pico honesto sem amostra.
Epoca epoca_da_grade(uint32_t indice, const float *gx, const float *gy, const float *gz,
                     uint32_t n, float temp_c);

// Instante monotonico (ms) do inicio da epoca `indice`, na grade que a cadeia
// ancorou em `origem_us`.
inline uint64_t inicio_da_epoca_c2_ms(uint64_t origem_us, uint32_t indice) {
  return (origem_us + static_cast<uint64_t>(indice) * 30000000ull) / 1000ull;
}

}  // namespace dormio

#endif  // DORMIO_NUCLEO_EPOCA_C2_H
