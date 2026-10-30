// reamostragem.h -- da taxa do sensor para a grade de 32 Hz do pipeline.
//
// E a mesma cadeia de `ml/src/sinal.py::reamostrar`, com uma diferenca de
// escopo que e a razao deste arquivo existir: o `ml/` filtra a NOITE INTEIRA de
// uma vez, e o ESP32 nao tem a noite inteira -- tem a epoca que acabou. Entao
// o firmware filtra por epoca, com `MARGEM_S` de sinal de cada lado, e joga a
// margem fora antes da grade.
//
//   1. Butterworth de 4a ordem a 12,8 Hz (0,8 x Nyquist da grade), aplicado
//      ida e volta -- fase zero --, NA TAXA DE ORIGEM. A ordem importa: filtrar
//      depois de reamostrar seria filtrar o que ja dobrou.
//   2. Interpolacao linear para os instantes da grade.
//
// Medido em 30/10 (`ml/testes/dourado_cadeia_c2.py`): com o instante
// verdadeiro de cada amostra, esta cadeia por epoca com 0,5 s de margem da a
// mesma grade que o `reamostrar` da noite inteira em 1,5e-6 g. Sem margem, a
// borda do filtro move `mag_din_media` em ate 1 %.
//
// ── POR QUE DUAS SECOES, E NAO `filtrar_ida_e_volta` DUAS VEZES ────────
//
// `butter(4, ...)` do scipy NAO e um Butterworth de 2a ordem aplicado duas
// vezes: sao duas secoes de 2a ordem com Q DIFERENTES (0,541 e 1,307), que
// juntas tem a resposta maximamente plana. Dois biquads iguais de Q = 0,707
// dariam um filtro de 4a ordem com o joelho caido 3 dB a mais no corte -- o
// sabotador `ordem_2` do dourado mede o efeito de errar isso no outro sentido.

#ifndef DORMIO_NUCLEO_REAMOSTRAGEM_H
#define DORMIO_NUCLEO_REAMOSTRAGEM_H

#include <stdint.h>

#include "filtro.h"

namespace dormio {

const float TAXA_DA_GRADE_HZ = 32.0f;
const float FRACAO_DE_NYQUIST_DO_ANTIALIASING = 0.8f;  // ml/config.yaml
const float CORTE_ANTIALIASING_HZ =
    FRACAO_DE_NYQUIST_DO_ANTIALIASING * TAXA_DA_GRADE_HZ / 2.0f;  // 12,8 Hz

// Os Q das duas secoes de um Butterworth de 4a ordem: 1/(2 cos(pi/8)) e
// 1/(2 cos(3 pi/8)).
const double Q_SECAO_1 = 0.54119610014619701;
const double Q_SECAO_2 = 1.3065629648763766;

// Uma secao de Butterworth de 2a ordem com o Q dado. Com Q = 1/sqrt(2) da
// exatamente `coeficientes_butterworth2`.
CoeficientesBiquad coeficientes_secao(float fs, float corte_hz, double q);

// O anti-aliasing, no lugar: as duas secoes na ida, as duas na volta.
// Devolve false (sem tocar em `v`) se `n < 2` ou se 12,8 Hz nao cabe abaixo
// do Nyquist de `fs` -- caso em que nao ha o que filtrar, e quem chamou
// deveria ter recusado a taxa antes.
bool filtrar_antialiasing(float *v, uint32_t n, float fs);

// Interpolacao linear de `v` em `m` posicoes FRACIONARIAS de indice:
// `x_j = x0 + j * dx`. Quem chama converte tempo em indice (`cadeia_c2.cpp`);
// aqui so ha aritmetica. Posicao fora de [0, n-1] satura na borda -- com a
// margem isso nao acontece, e se acontecer o erro fica limitado a um valor
// de borda em vez de ler memoria alheia.
void interpolar_linear(const float *v, uint32_t n, double x0, double dx, float *saida,
                       uint32_t m);

}  // namespace dormio

#endif  // DORMIO_NUCLEO_REAMOSTRAGEM_H
