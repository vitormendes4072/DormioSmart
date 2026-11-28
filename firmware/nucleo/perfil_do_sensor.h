// perfil_do_sensor.h -- o que muda entre o MPU6050 e o MPU6500 (FW-21).
//
// ── POR QUE EXISTE ─────────────────────────────────────────────────────
//
// O MPU-6050 saiu de linha (a TDK o marca como EOL), e os modulos GY-521
// vendidos como "MPU-6050" chegam com outro chip. Em 26 e 27/11 os quatro
// modulos de duas compras responderam WHO_AM_I 0x70 em 2 000 de 2 000
// leituras e encheram a FIFO com 512 B (`diagnostico-i2c`, HW-12): sao
// MPU6500 (ou copias dele) com "MPU-6050" gravado por cima.
//
// Para a C2 o MPU6500 serve -- a mesma taxa (medida: 49,5 Hz com o divisor
// 19), a mesma escala (4 096 LSB/g em +-8 g, folha PS-MPU-6500A-01 rev. 1.3,
// tabela 2) e os mesmos registradores da FIFO -- com duas diferencas:
//
//   1. a FIFO tem 512 B, nao 1 024 (folha, secao 4.14). Esvaziada a cada
//      1,7 s ela transborda (85 amostras cabem em 1,7 s a 50 Hz), e toda
//      epoca e recusada. A drenagem passa a ~0,85 s: metade da FIFO, a mesma
//      regra da C2;
//   2. o filtro do acelerometro fica em ACCEL_CONFIG 2 (0x1D), e nao em
//      CONFIG (0x1A), que no MPU6500 so filtra o giroscopio. Sem gravar o
//      0x1D, o acelerometro roda sem o filtro de ~21 Hz e o sinal a 50 Hz
//      dobra o espectro. O valor 4 e o do driver oficial do Linux
//      (`inv_mpu6050`, mantido pela InvenSense), que grava o mesmo numero nos
//      dois registradores; a tabela de banda do mapa de registradores
//      (RM-MPU-6500A-00) nao estava acessivel em 27/11 (HTTP 403) e o efeito
//      foi conferido na bancada, pelo ruido parado.
//
//   3. a temperatura do chip (TEMP_OUT, 0x41-0x42) tem outra conversao. No
//      MPU6050, T = bruto / 340 + 36,53; no MPU6500, T = bruto / 333,87 + 21.
//      Conferido em 27/11 no driver do Linux (`inv_mpu_iio.h`):
//      INV_MPU6050_TEMP_OFFSET 12420 e _SCALE 2941176, INV_MPU6500_TEMP_OFFSET
//      7011 e _SCALE 2995178, ou T = (bruto + offset) * scale / 1e9 --
//      (bruto + 12420) * 0,002941176 = bruto / 340 + 36,53, e (bruto + 7011) *
//      0,002995178 = bruto / 333,87 + 21,0. Com a formula do MPU6050, um
//      MPU6500 a 25 C marcaria ~40,5 C: o erro ia ao servidor em cada epoca,
//      a calibracao (CAL-03) e o ensaio termico (CALC-05). Achado na revisao
//      do FW-21, 27/11.
//
// O sketch le o WHO_AM_I ao configurar o sensor e usa o perfil que ele
// indica. Chip desconhecido usa o perfil conservador: FIFO de 512 B (o
// menor dos dois) e sem escrever o 0x1D, que no MPU6050 nao e documentado.
// A temperatura dele segue a conversao do MPU6050, a de antes do FW-21: nao
// ha como saber a certa, e o log do sensor ja diz "desconhecido".

#ifndef DORMIO_NUCLEO_PERFIL_DO_SENSOR_H
#define DORMIO_NUCLEO_PERFIL_DO_SENSOR_H

#include <stdint.h>

#include "cadeia_c2.h"
#include "fifo_mpu.h"

namespace dormio {

const uint8_t MPU_REG_ACCEL_CONFIG2 = 0x1D;
const uint8_t MPU_REG_WHO_AM_I = 0x75;
const uint8_t WHO_AM_I_MPU6050 = 0x68;
const uint8_t WHO_AM_I_MPU6500 = 0x70;

// ACCEL_CONFIG 2: ACCEL_FCHOICE_B = 0 (bit 3) e A_DLPF_CFG = 4 (bits 2:0) --
// o mesmo 4 do C2_DLPF_CFG (~21 Hz no MPU6050).
const uint8_t C2_A_DLPF_CFG = 4;

const uint16_t FIFO_MPU6500_BYTES = 512;

struct PerfilDoSensor {
  const char *nome;
  uint16_t fifo_bytes;              // o teto da contagem: FIFO cheia
  uint32_t intervalo_de_drenagem_us;  // a base; `intervalo_de_drenagem_us` soma a variacao
  bool filtro_em_accel_config2;     // gravar C2_A_DLPF_CFG em 0x1D
  float temp_lsb_por_grau;          // T = bruto / temp_lsb_por_grau + temp_com_bruto_zero_c
  float temp_com_bruto_zero_c;
};

const float TEMP_MPU6050_LSB_POR_GRAU = 340.0f;
const float TEMP_MPU6050_BRUTO_ZERO_C = 36.53f;
const float TEMP_MPU6500_LSB_POR_GRAU = 333.87f;
const float TEMP_MPU6500_BRUTO_ZERO_C = 21.0f;

const PerfilDoSensor PERFIL_MPU6050 = {"MPU6050", FIFO_CAPACIDADE_BYTES, INTERVALO_DE_DRENAGEM_US,
                                       false, TEMP_MPU6050_LSB_POR_GRAU,
                                       TEMP_MPU6050_BRUTO_ZERO_C};
const PerfilDoSensor PERFIL_MPU6500 = {"MPU6500", FIFO_MPU6500_BYTES,
                                       INTERVALO_DE_DRENAGEM_MPU6500_US, true,
                                       TEMP_MPU6500_LSB_POR_GRAU, TEMP_MPU6500_BRUTO_ZERO_C};
const PerfilDoSensor PERFIL_DESCONHECIDO = {"desconhecido", FIFO_MPU6500_BYTES,
                                            INTERVALO_DE_DRENAGEM_MPU6500_US, false,
                                            TEMP_MPU6050_LSB_POR_GRAU,
                                            TEMP_MPU6050_BRUTO_ZERO_C};

// A temperatura do chip, em graus C, pela conversao do perfil.
inline float temperatura_do_chip_c(const PerfilDoSensor *p, int16_t bruto) {
  return static_cast<float>(bruto) / p->temp_lsb_por_grau + p->temp_com_bruto_zero_c;
}

inline const PerfilDoSensor *perfil_do_sensor(uint8_t who_am_i) {
  if (who_am_i == WHO_AM_I_MPU6050) return &PERFIL_MPU6050;
  if (who_am_i == WHO_AM_I_MPU6500) return &PERFIL_MPU6500;
  return &PERFIL_DESCONHECIDO;
}

}  // namespace dormio

#endif
