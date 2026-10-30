// cadeia_c2.h -- das drenagens da FIFO a grade de 32 Hz de cada epoca.
//
// O problema que este modulo resolve: a FIFO do MPU6050 nao tem carimbo de
// tempo, e a taxa dela nao e a nominal. O oscilador interno tem +-5 % a 25 C e
// -15/+10 % na faixa de temperatura (folha de produto). O que o firmware sabe
// e so isto: em cada drenagem, QUANDO ela aconteceu (relogio do ESP32) e
// QUANTAS amostras vieram.
//
// ── A LINHA DO TEMPO ──────────────────────────────────────────────────
//
// Cada drenagem e um ponto (contagem acumulada, instante). Uma regressao de
// minimos quadrados sobre as drenagens em torno da epoca da a reta
//
//     t_k = a + b * (k + 0,5)        (k = indice global da amostra)
//
// em que `1/b` e a taxa MEDIDA. O meio passo existe porque a drenagem que
// deixa a contagem em C acontece num ponto qualquer entre a amostra C-1 e a
// C: em media, meio passo depois da C-1. Sem ele a linha inteira atrasa 10 ms
// (o sabotador `sem_meio_passo` do dourado).
//
// Erro medido em 30/10 contra o tempo verdadeiro, 50 sementes x 4 taxas:
// ate ~5 ms no centro da epoca, com o despertar variado (ver
// `intervalo_de_drenagem_us`). E isso -- nao o filtro, nao o float32 -- que
// separa a grade do firmware da grade do `ml/`. As tolerancias de validade do
// dourado sao derivadas desse piso (`ml/testes/test_dourado_cadeia_c2.py`).
//
// ⚠️ O RELOGIO DO ESP32 E TOMADO COMO VERDADEIRO, E NAO E. Em sono leve ele
// conta por um oscilador interno mais pobre que o cristal, calibrado contra
// ele de tempos em tempos. Se esse relogio errar, a taxa "medida" herda o
// erro. Quanto ele erra e a parte (c) do `ARQ-01`: so a placa responde.
//
// ── POR QUE A EPOCA ESPERA ────────────────────────────────────────────
//
// A epoca k so fecha quando ja chegou uma drenagem depois de
// `fim + MARGEM_S + FOLGA_DO_AJUSTE_S`: o filtro precisa de meio segundo de
// sinal DEPOIS da epoca, e a regressao fica melhor com drenagens dos dois
// lados. Sao ~3 s de latencia num dado que vai para o buffer de qualquer
// jeito -- custo nenhum.
//
// ── O QUE E RECUSADO, E POR QUE NAO SE "APROVEITA" ────────────────────
//
// Transbordo da FIFO na janela, drenagens de menos, taxa fora da faixa,
// amostras que ja sairam do anel: a epoca sai RECUSADA, sem grade. Mesmo
// principio do `AcumuladorDeFeatures`: o dispositivo nao emite vetor de
// epoca que ele sabe estar errada. Reamostrar com uma linha do tempo que mistura
// os dois lados de um transbordo produziria 960 amostras plausiveis no lugar
// errado -- dado distorcido com cara de dado, o modo de falha mais caro deste
// projeto (README do nucleo).
//
// Referencia executavel: `cadeia_estilo_firmware` em
// `ml/testes/dourado_cadeia_c2.py`. Este modulo a copia; onde divergir, e ele
// que esta errado.

#ifndef DORMIO_NUCLEO_CADEIA_C2_H
#define DORMIO_NUCLEO_CADEIA_C2_H

#include <stdint.h>

#include "fifo_mpu.h"

namespace dormio {

const float TAXA_NOMINAL_C2_HZ = 50.0f;  // taxa_nominal_hz(C2_SMPLRT_DIV)
const double DURACAO_EPOCA_C2_S = 30.0;
const uint32_t AMOSTRAS_NA_GRADE = 960;  // 30 s x 32 Hz

// Meio segundo de sinal de cada lado entra no filtro e sai antes da grade.
// Medido: sem margem a borda move `mag_din_media` 1 %; com 0,5 s a cadeia por
// epoca bate com a noite inteira em 1,5e-6 g; 1 s nao melhora nada.
const double MARGEM_S = 0.5;
// Drenagens ate esta distancia alem da janela entram na regressao.
const double FOLGA_DO_AJUSTE_S = 2.0;
// Numa janela de 31 s + 2 x 2 s cabem ~20 drenagens; 8 aceita perder mais da
// metade sem a regressao ficar sem apoio.
const uint32_t MINIMO_DE_DRENAGENS = 8;
// Faixa plausivel da taxa medida. O oscilador promete -15/+10 %; fora de
// +-20 % a medida esta errada, nao o oscilador.
const double TAXA_MINIMA_FRAC = 0.8;
const double TAXA_MAXIMA_FRAC = 1.2;

// Metade da FIFO: 85 amostras a 50 Hz.
const uint32_t INTERVALO_DE_DRENAGEM_US = 1700000;
// Variacao deliberada do intervalo, em [0, 20 ms). A 50 Hz exatos, 1,7 s sao
// 85 amostras inteiras: o despertar trava em fase com a amostragem, toda
// drenagem cai no mesmo ponto entre duas amostras, e a regressao herda esse
// deslocamento inteiro (ate 10 ms) em vez de tirar a media. Medido: o pior
// erro de tempo no centro da epoca cai de 8,1 para 4,7 ms. Com o oscilador a
// +10 %, o intervalo maximo (1,72 s + 3 ms de latencia) da 95 amostras, longe
// das 170 da FIFO.
const uint32_t VARIACAO_DA_DRENAGEM_US = 20000;

// O proximo intervalo de drenagem, com a variacao. `estado` e um xorshift32
// que o sketch guarda (comece em qualquer valor diferente de zero).
// Deterministico de proposito: um teste consegue reproduzir a sequencia.
uint32_t intervalo_de_drenagem_us(uint32_t *estado);

// O anel guarda ~42 s a 55 Hz: a janela (31 s), a espera pela folga (2,5 s) e
// mais uns segundos de atraso de processamento. 13,8 KB.
const uint32_t CAPACIDADE_DE_AMOSTRAS = 2304;
// 48 drenagens = ~82 s de historico, o dobro do que a janela precisa.
const uint32_t CAPACIDADE_DE_DRENAGENS = 48;

enum ResultadoDaEpoca {
  EPOCA_AINDA_NAO = 0,               // falta drenagem depois da folga
  EPOCA_PRONTA = 1,
  EPOCA_RECUSADA_TRANSBORDO = 2,     // a FIFO transbordou dentro do ajuste
  EPOCA_RECUSADA_POUCAS_DRENAGENS = 3,
  EPOCA_RECUSADA_TAXA = 4,           // 1/b fora de [0,8; 1,2] x nominal
  EPOCA_RECUSADA_SEM_AMOSTRAS = 5,   // a janela nao esta (mais) no anel
};

struct LinhaDoTempo {
  double a_s;            // instante da "amostra -0,5", relativo a origem
  double b_s;            // periodo medido; a taxa e 1/b
  uint32_t n_drenagens;  // pontos que entraram na regressao
};

struct EpocaReamostrada {
  uint32_t indice;           // 0, 1, 2... desde `iniciar`
  ResultadoDaEpoca resultado;
  LinhaDoTempo linha;        // so vale com PRONTA ou RECUSADA_TAXA
  int64_t k_ini, k_fim;      // amostras globais que entraram no filtro
};

// Regressao da linha do tempo, exposta para teste. `t_s` relativo a origem,
// `acumulado` = contagem global depois da drenagem. Devolve false com menos de
// `MINIMO_DE_DRENAGENS` pontos ou contagens todas iguais.
bool ajustar_linha_do_tempo(const double *t_s, const double *acumulado, uint32_t n,
                            LinhaDoTempo *saida);

class CadeiaC2 {
 public:
  CadeiaC2();

  // `origem_us`: inicio da epoca 0 no relogio do ESP32 (o mesmo relogio que
  // carimba as drenagens). As epocas seguem na grade absoluta a partir dele.
  void iniciar(uint64_t origem_us);

  // Uma drenagem. `transbordou` = a leitura foi descartada por transbordo
  // (`avaliar_fifo`), e `n` deve ser 0: as amostras daquela leitura nao
  // entram, e as epocas cujo ajuste alcanca este instante sao recusadas.
  void registrar_drenagem(uint64_t t_us, const AmostraBruta *amostras, uint16_t n,
                          bool transbordou);

  // Tenta fechar a proxima epoca. Com PRONTA escreve 960 valores em g em
  // `gx`, `gy`, `gz`. Com qualquer RECUSADA a epoca e consumida sem grade. Com
  // AINDA_NAO nada muda: chame de novo depois da proxima drenagem.
  ResultadoDaEpoca proxima_epoca(EpocaReamostrada *info, float *gx, float *gy, float *gz);

  uint64_t amostras_recebidas() const { return total_amostras_; }
  uint32_t epoca_seguinte() const { return proxima_epoca_; }

 private:
  struct RegistroDeDrenagem {
    uint64_t t_us;
    uint64_t acumulado;  // amostras recebidas ate esta drenagem, inclusive
    bool transbordou;
  };

  double relativo_s(uint64_t t_us) const;
  const RegistroDeDrenagem &drenagem(uint32_t i) const;  // 0 = a mais antiga guardada
  uint32_t drenagens_guardadas() const;

  AmostraBruta anel_[CAPACIDADE_DE_AMOSTRAS];
  float trabalho_[CAPACIDADE_DE_AMOSTRAS];
  RegistroDeDrenagem drenagens_[CAPACIDADE_DE_DRENAGENS];
  uint64_t total_amostras_;
  uint32_t total_drenagens_;
  uint64_t origem_us_;
  uint32_t proxima_epoca_;
  bool iniciada_;
};

}  // namespace dormio

#endif  // DORMIO_NUCLEO_CADEIA_C2_H
