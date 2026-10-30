// fifo_mpu.h -- os bytes da FIFO do MPU6050, e os registradores que a C2 usa.
//
// Arquitetura C2 (`ARQ-01`, decidida em 2026-10-30): o sensor amostra sozinho
// a 50 Hz e empilha as leituras do acelerometro na FIFO interna de 1024 B; o
// ESP32 dorme em sono leve e acorda a cada ~1,7 s para esvaziar metade dela.
// Este modulo e a parte que nao precisa de I2C para ser testada: o que os
// bytes significam, quantos ler, e quando a leitura nao merece confianca.
//
// ── POR QUE AS CONSTANTES ESTAO AQUI, E NAO NO SKETCH ──────────────────
//
// O sketch escreve estes valores nos registradores; o resto do nucleo conta
// com eles (a taxa nominal em `cadeia_c2.h`, a escala em `lsb_para_g`). Se o
// sketch escrevesse um divisor e o nucleo assumisse outro, a estimativa de
// taxa ainda funcionaria -- e mediria a taxa certa -- mas a faixa plausivel
// seria a de outra taxa, e a epoca seria recusada sem que nada dissesse por
// que. Uma definicao so, com teste.
//
// Fonte dos enderecos e bits: MPU-6000/MPU-6050 Register Map and Descriptions,
// rev. 4.2. A escala de 4096 LSB/g e a do AFS_SEL = 2 (+-8 g), que e o que os
// tres sketches configuram (`MPU6050_RANGE_8_G`).
//
// ⚠️ NAO EXERCITADO EM PLACA. Ate a solda (Etapa 0) nenhum destes valores foi
// escrito num MPU6050 de verdade; o que esta verificado e a aritmetica.

#ifndef DORMIO_NUCLEO_FIFO_MPU_H
#define DORMIO_NUCLEO_FIFO_MPU_H

#include <stdint.h>

namespace dormio {

// ── Registradores ─────────────────────────────────────────────────────
const uint8_t MPU_REG_SMPLRT_DIV = 0x19;
const uint8_t MPU_REG_CONFIG = 0x1A;
const uint8_t MPU_REG_ACCEL_CONFIG = 0x1C;
const uint8_t MPU_REG_FIFO_EN = 0x23;
const uint8_t MPU_REG_INT_STATUS = 0x3A;
const uint8_t MPU_REG_USER_CTRL = 0x6A;
const uint8_t MPU_REG_FIFO_COUNTH = 0x72;  // COUNTL e o seguinte, 0x73
const uint8_t MPU_REG_FIFO_R_W = 0x74;

// ── Valores da C2 ─────────────────────────────────────────────────────
//
// Taxa = 1 kHz / (1 + SMPLRT_DIV) quando o DLPF esta ligado (DLPF_CFG de 1 a
// 6). 19 da 50 Hz: a menor taxa nativa acima dos 42 Hz com a dobra do
// espectro longe do DLPF (`docs/DECISAO-ARQ-01-CADENCIA.md` §5).
const uint8_t C2_SMPLRT_DIV = 19;
// DLPF_CFG = 4: acelerometro com banda de 21 Hz -- o mesmo filtro do `FW-06`.
const uint8_t C2_DLPF_CFG = 4;
// AFS_SEL = 2 nos bits 4:3 -> +-8 g.
const uint8_t C2_ACCEL_CONFIG = 2u << 3;
// ACCEL_FIFO_EN (bit 3): so o acelerometro entra na FIFO. Giroscopio e
// temperatura ficam de fora -- o modelo nao os usa, e cada um custaria mais
// 6 ou 2 bytes por amostra, encurtando a FIFO de 3,4 s para 1,7 s ou 2,6 s.
const uint8_t C2_FIFO_EN = 1u << 3;
// USER_CTRL: FIFO_EN (bit 6) liga; FIFO_RESET (bit 2) esvazia.
const uint8_t MPU_USER_CTRL_FIFO_EN = 1u << 6;
const uint8_t MPU_USER_CTRL_FIFO_RESET = 1u << 2;
// INT_STATUS: FIFO_OFLOW_INT (bit 4).
const uint8_t MPU_INT_STATUS_FIFO_OFLOW = 1u << 4;

const uint16_t FIFO_CAPACIDADE_BYTES = 1024;
const uint16_t BYTES_POR_AMOSTRA = 6;  // X, Y, Z em int16 big-endian
// 170: o que cabe inteiro. 1024 nao e multiplo de 6 -- sobram 4 bytes, e e
// por isso que FIFO cheia tambem significa FIFO desalinhada.
const uint16_t FIFO_CAPACIDADE_AMOSTRAS = FIFO_CAPACIDADE_BYTES / BYTES_POR_AMOSTRA;

const float LSB_POR_G = 4096.0f;

inline float taxa_nominal_hz(uint8_t smplrt_div) {
  return 1000.0f / (1.0f + static_cast<float>(smplrt_div));
}

struct AmostraBruta {
  int16_t x, y, z;
};

inline float lsb_para_g(int16_t v) { return static_cast<float>(v) / LSB_POR_G; }

enum EstadoDaLeitura {
  LEITURA_OK = 0,
  // FIFO_OFLOW ligado, ou contagem no teto: amostras se perderam e, como
  // 1024 nao e multiplo de 6, o fluxo pode estar desalinhado. A unica saida
  // segura e descartar tudo, resetar a FIFO e marcar a descontinuidade.
  // Emendar os dois lados faria a contagem mentir sobre o tempo -- e e da
  // contagem que sai o instante de cada amostra (`cadeia_c2.h`).
  LEITURA_TRANSBORDOU = 1,
  // Contagem que nao e multipla de 6 sem ter transbordado. Nao deveria
  // acontecer: a FIFO so recebe amostras inteiras. Se acontecer, e
  // leitura no meio de uma escrita ou barramento corrompido.
  LEITURA_DESALINHADA = 2,
};

// Classifica a leitura de FIFO_COUNT e INT_STATUS antes de ler os bytes.
EstadoDaLeitura avaliar_fifo(uint16_t fifo_count, uint8_t int_status);

// Quantos bytes ler: a contagem arredondada para baixo em amostras inteiras,
// e no maximo `teto_bytes` (o buffer de quem chama).
uint16_t bytes_para_ler(uint16_t fifo_count, uint16_t teto_bytes);

// Converte `n_bytes` lidos de FIFO_R_W em amostras. Devolve quantas escreveu
// em `destino` (no maximo `capacidade`). Bytes que nao completam uma amostra
// sao ignorados -- quem chamou leu mais do que `bytes_para_ler` mandou.
uint16_t decodificar_fifo(const uint8_t *bytes, uint16_t n_bytes, AmostraBruta *destino,
                          uint16_t capacidade);

}  // namespace dormio

#endif  // DORMIO_NUCLEO_FIFO_MPU_H
