#include "fifo_mpu.h"

namespace dormio {

EstadoDaLeitura avaliar_fifo(uint16_t fifo_count, uint8_t int_status) {
  if ((int_status & MPU_INT_STATUS_FIFO_OFLOW) != 0) return LEITURA_TRANSBORDOU;
  // A contagem no teto e transbordo mesmo sem o bit: a interrupcao pode estar
  // desligada (INT_ENABLE nao e responsabilidade deste modulo), e o bit de
  // status so e confiavel quando ela esta ligada.
  if (fifo_count >= FIFO_CAPACIDADE_BYTES) return LEITURA_TRANSBORDOU;
  if (fifo_count % BYTES_POR_AMOSTRA != 0) return LEITURA_DESALINHADA;
  return LEITURA_OK;
}

uint16_t bytes_para_ler(uint16_t fifo_count, uint16_t teto_bytes) {
  uint16_t n = fifo_count < teto_bytes ? fifo_count : teto_bytes;
  return static_cast<uint16_t>(n - n % BYTES_POR_AMOSTRA);
}

uint16_t decodificar_fifo(const uint8_t *bytes, uint16_t n_bytes, AmostraBruta *destino,
                          uint16_t capacidade) {
  if (bytes == 0 || destino == 0) return 0;
  uint16_t n = static_cast<uint16_t>(n_bytes / BYTES_POR_AMOSTRA);
  if (n > capacidade) n = capacidade;
  for (uint16_t i = 0; i < n; i++) {
    const uint8_t *p = bytes + static_cast<uint32_t>(i) * BYTES_POR_AMOSTRA;
    // Big-endian, byte alto primeiro (Register Map, ACCEL_XOUT_H/L). A
    // conversao passa por uint16_t para o deslocamento nao tocar o bit de
    // sinal de um int: o padrao so define o resultado em unsigned.
    destino[i].x = static_cast<int16_t>(static_cast<uint16_t>((p[0] << 8) | p[1]));
    destino[i].y = static_cast<int16_t>(static_cast<uint16_t>((p[2] << 8) | p[3]));
    destino[i].z = static_cast<int16_t>(static_cast<uint16_t>((p[4] << 8) | p[5]));
  }
  return n;
}

}  // namespace dormio
