// bateria.h -- a tensao da celula LiFePO4, lida pelo ADC (HW-10, etapa 1).
//
// ── O CIRCUITO ─────────────────────────────────────────────────────────
//
// `docs/ESTUDO-ENERGIA.md` §8.1 e `DIAG-02` v3: um divisor de 1 MOhm + 1 MOhm
// do 3V3 (que, sem regulador, e a propria celula) ao GND, com 100 nF no meio,
// ligado ao GPIO35 (ADC1 -- o ADC2 nao funciona com o Wi-Fi ligado). O ADC ve
// metade da tensao da celula; `analogReadMilliVolts` ja aplica a calibracao
// de fabrica do ESP32.
//
// ── O QUE ESTE MODULO DECIDE ───────────────────────────────────────────
//
//   - a tensao da celula a partir das amostras do ADC (media, vezes o divisor);
//   - o estado para a LiFePO4: ok, baixa, critica -- com histerese, para nao
//     piscar entre dois estados quando a tensao fica na fronteira;
//   - "indisponivel" quando a leitura nao pode ser uma celula: sem o divisor
//     montado, o pino fica solto e o ADC le ruido perto de zero.
//
// A LiFePO4 passa a maior parte da descarga em 3,2 a 3,3 V e cai rapido perto
// do fim: a tensao serve para avisar o fim, nao para dar porcentagem. Por isso
// nao ha porcentagem aqui. Etapa 2 (contrato, servidor, painel) e outro passo.
#ifndef DORMIO_NUCLEO_BATERIA_H
#define DORMIO_NUCLEO_BATERIA_H

#include <stdint.h>

namespace dormio {

// 1 MOhm + 1 MOhm: o ADC ve metade.
const uint32_t DIVISOR_DA_BATERIA = 2;

// Abaixo disto, nao e uma celula: e o pino solto (sem o divisor) ou um fio
// partido. A LiFePO4 e cortada pela placa de protecao em ~2,5 V.
const uint32_t BATERIA_MINIMA_PLAUSIVEL_MV = 2000;
// Fim do patamar da LiFePO4: abaixo de 3,1 V em repouso resta pouco.
const uint32_t BATERIA_BAIXA_MV = 3100;
// 3,0 V: o minimo do modulo ESP32 para o radio funcionar dentro da faixa.
const uint32_t BATERIA_CRITICA_MV = 3000;
// Para sair de um estado pior, a tensao tem de subir isto acima do limite.
const uint32_t HISTERESE_DA_BATERIA_MV = 50;

enum EstadoDaBateria {
  BATERIA_INDISPONIVEL = 0,
  BATERIA_OK = 1,
  BATERIA_BAIXA = 2,
  BATERIA_CRITICA = 3,
};

// Media das amostras do ADC (mV no pino), vezes o divisor. 0 sem amostras.
uint32_t tensao_da_bateria_mv(const uint32_t *amostras_mv, uint32_t n);

// O estado da celula pela tensao em repouso, com histerese sobre o anterior.
EstadoDaBateria classificar_bateria(uint32_t tensao_mv, EstadoDaBateria anterior);

const char *nome_do_estado(EstadoDaBateria estado);

// A linha `[bateria] ...` do log. Devolve os caracteres escritos, ou 0 (e a
// string vazia) se nao coube.
uint32_t formatar_bateria(uint32_t repouso_mv, uint32_t envio_mv, EstadoDaBateria estado,
                          char *destino, uint32_t tamanho);

}  // namespace dormio

#endif
