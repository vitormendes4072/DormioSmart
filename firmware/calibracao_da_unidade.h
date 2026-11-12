// calibracao_da_unidade.h -- a calibracao de bancada DESTA unidade (FW-11).
//
// Medida em 2026-11-11 (`CAL-01`, diario 11/11 xi): 6 posicoes com o sketch
// `caracterizacao/`, +-8 g e filtro de 21 Hz (os do firmware), sensor de 27,8
// a 32,1 graus C, estimada por `ml/src/calibracao.py` (van Hees, 2014). O
// erro que ela corrige: desvio de -130 mg em Z (o sensor parado lia 0,897 g
// com o chip para cima e 1,157 g com ele para baixo), 21 a 42 mg em X e Y.
// Validada fora do ajuste: em 6 posicoes paradas do monitor ao vivo, o erro
// da gravidade parada caiu de 83,6 mg para 2,3 mg (RMS).
//
// NAO e segredo, e e versionado de proposito: o dado de cada noite depende
// destes numeros, e eles tem de ser rastreaveis. Os valores valem para ESTE
// modulo GY-521. Outra unidade e outra bancada e outro arquivo.
//
// Forma: calibrado = desvio + escala * bruto, por eixo, em g (`calibracao.h`).
// Sem termo de temperatura: seis pontos nao o sustentam.

#ifndef DORMIO_CALIBRACAO_DA_UNIDADE_H
#define DORMIO_CALIBRACAO_DA_UNIDADE_H

#include "nucleo/calibracao.h"

inline dormio::Calibracao calibracao_da_unidade() {
  dormio::Calibracao c;
  c.aceita = true;
  c.desvio[0] = -0.04207;
  c.desvio[1] = 0.020988;
  c.desvio[2] = 0.12692;
  c.escala[0] = 0.994324;
  c.escala[1] = 0.99676;
  c.escala[2] = 0.976115;
  for (int k = 0; k < 3; k++) c.modos[k] = dormio::EIXO_COMPLETO;
  c.temp_ref_c = 30.0;
  return c;
}

#endif  // DORMIO_CALIBRACAO_DA_UNIDADE_H
