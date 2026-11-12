// calibracao.h -- autocalibracao do acelerometro pela gravidade (CAL-03).
//
// ── O ERRO ───────────────────────────────────────────────────────────────
//
// Cada eixo tem um desvio e um erro de escala, e os dois andam com a
// temperatura. Parado, o sensor deveria ler 1 g em qualquer posicao; o Moto E7
// le de 0,991 a 1,020 g conforme a posicao (diario, 10/11 iv). O ENMO,
// max(||a|| - 1, 0), le esse erro como movimento quando ||a|| > 1 (18,7 mg
// parado com a tela para baixo) e esconde o movimento pequeno quando < 1.
//
// ── O METODO ─────────────────────────────────────────────────────────────
//
// O de van Hees et al. (2014), o do GGIR: cada epoca parada e um ponto que
// deveria estar na esfera de raio 1 g. A cada iteracao o ponto calibrado e
// projetado na esfera, e por eixo se ajusta a reta que leva o bruto ao alvo:
//
//   calibrado_k = desvio_k + escala_k * bruto_k + coef_temp_k * (T - T_ref)
//
// O que difere do GGIR (que recusa sem pontos espalhados pela esfera): cada
// eixo usa so o que os pontos identificam -- COMPLETO (passou de +-0,3 g dos
// dois lados: desvio e escala), DESVIO (de um lado so: so o desvio) ou FIXO
// (nunca passou: fica como esta). Um celular deitado no colchao so mexe em z,
// e e z que pesa na norma nessa posicao. O porque, por extenso, esta em
// `ml/src/calibracao.py`, que e a REFERENCIA: este arquivo faz a mesma conta,
// e `make calibracao` confere contra o dourado gravado por ela
// (`ml/testes/dourado_calibracao.json`).
//
// ── ONDE ENTRA ───────────────────────────────────────────────────────────
//
// Em cada amostra, em g, ANTES da cadeia (`ColetorCelular::amostrar`). O
// filtro da cadeia e linear com ganho 1 em DC, entao calibrar antes ou depois
// dele daria o mesmo no sinal parado; antes e o que mantem o ENMO, o pico e o
// `gn` coerentes entre si.
//
// Quem estima e o app, entre noites, com as epocas paradas das noites
// anteriores (etapa 2 do CAL-03). Este arquivo da a conta; nao guarda nada.

#ifndef DORMIO_NUCLEO_CALIBRACAO_H
#define DORMIO_NUCLEO_CALIBRACAO_H

#include <stdint.h>

#include "fifo_mpu.h"

namespace dormio {

// As constantes da referencia (`ml/src/calibracao.py`). Mudar uma aqui e
// mudar la: o dourado acusa a divergencia.
const double LIMIAR_PARADO_G = 0.010;
const double LADO_MINIMO_G = 0.3;
const double FAIXA_MINIMA_TEMPERATURA_C = 2.0;  // PROVISORIO (etapa 3)
const uint32_t PONTOS_MINIMOS_CALIBRACAO = 40;
const double ERRO_MAXIMO_ACEITO_G = 0.010;
const uint32_t ITERACOES_MAXIMAS_CALIBRACAO = 200;
const double TOLERANCIA_CALIBRACAO = 1e-10;

enum ModoDoEixo {
  EIXO_FIXO = 0,
  EIXO_DESVIO = 1,
  EIXO_COMPLETO = 2,
};

struct Calibracao {
  // Sem `aceita`, os parametros sao os da identidade e `aplicar` nao mexe.
  bool aceita;
  double desvio[3];
  double escala[3];
  double coef_temp[3];
  double temp_ref_c;
  uint8_t modos[3];
  bool usou_temperatura;
  uint32_t n;
  double erro_antes_g;
  double erro_depois_g;
  uint32_t iteracoes;

  Calibracao();
  void identidade();
};

// Calibra uma amostra em g. Sem `aceita`, copia.
void aplicar_calibracao(const Calibracao &c, double temp_c, const double entrada[3],
                        double saida[3]);

// O inverso: do calibrado de volta ao bruto. O app precisa dele (etapa 2): a
// epoca guardada saiu calibrada pela calibracao daquela noite, e a proxima
// estimativa parte do bruto.
void desfazer_calibracao(const Calibracao &c, double temp_c, const double entrada[3],
                         double saida[3]);

// Estima a partir de `n` epocas paradas: `pontos[i]` e o vetor medio da
// aceleracao da epoca, em g, BRUTO; `temp_c[i]`, a temperatura dela.
Calibracao estimar_calibracao(const double (*pontos)[3], const double *temp_c, uint32_t n);

// Calibra `n` amostras do MPU6050 na escala da C2 (`LSB_POR_G`), no lugar
// (FW-11): o travesseiro aplica a calibracao de bancada da unidade a cada
// drenagem, antes da cadeia -- o mesmo ponto em que o celular aplica a dele
// (`ColetorCelular::amostrar`). A volta para inteiro arredonda e satura em
// +-8 g como `g_para_lsb`, e `testes_c2` confere as duas iguais. Sem `aceita`,
// nao mexe: a amostra sai byte a byte como entrou.
void calibrar_amostras(const Calibracao &c, double temp_c, AmostraBruta *amostras, uint16_t n);

}  // namespace dormio

#endif  // DORMIO_NUCLEO_CALIBRACAO_H
