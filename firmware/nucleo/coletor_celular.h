// coletor_celular.h -- a cadeia C2 alimentada pelo acelerometro de um celular (APP-02).
//
// ── POR QUE O APP RODA O NUCLEO DO FIRMWARE ─────────────────────────────
//
// O app Android registra a noite pelo acelerometro do celular. Se ele
// calculasse as features com outra implementacao, o servidor receberia dois
// vetores com o mesmo nome e contas diferentes -- e o modelo do ML-INF foi
// validado so contra uma delas. Entao o app compila ESTE nucleo pelo NDK, e o
// celular percorre o caminho que a placa percorre:
//
//   amostras -> drenagens -> CadeiaC2 (linha do tempo, anti-aliasing, grade
//   de 32 Hz) -> AcumuladorDeFeatures -> quantizar/desquantizar (o caminho da
//   fila de flash) -> epoca_da_grade -> montar_payload
//
// O payload sai byte a byte no formato do firmware.
//
// ── O QUE MUDA EM RELACAO A PLACA ───────────────────────────────────────
//
// 1. O instante de cada amostra. A FIFO do MPU6050 nao tem carimbo, e a placa
//    so sabe quando drenou; o celular entrega o instante de cada amostra
//    (`SensorEvent.timestamp`). O coletor junta as amostras em drenagens a
//    cada `INTERVALO_DE_DRENAGEM_US`, como a placa, e carimba cada drenagem
//    meio passo depois da ultima amostra -- a convencao que a regressao da
//    `CadeiaC2` assume (`cadeia_c2.h`, "o meio passo").
//
// 2. A unidade. O celular mede em m/s^2; o coletor converte para g e QUANTIZA
//    para a escala do MPU6050 na C2 (+-8 g, 4096 LSB/g). Isso poe o sinal do
//    celular na mesma grade numerica do dispositivo; o passo, 2,4e-4 g, fica
//    abaixo do ruido de qualquer acelerometro de celular.
//
// 3. A temperatura. O celular nao tem a do chip do MPU; o app passa a da
//    bateria, que e a "temperatura do aparelho" -- e e a que importa para o
//    risco de aquecimento dentro da fronha. O contrato (v2.10.0, DATA-14) diz
//    isso: `t` e a temperatura do aparelho que mediu. Enquanto o app nao a
//    informar, ela e DESCONHECIDA: o payload sai sem `t` e nenhum ponto de
//    calibracao e gravado. Ate 13/11 o coletor comecava em 25,0 C, e esse
//    numero inventado ia ao servidor como medida se o Android nao entregasse
//    a temperatura da bateria.
//
// ── A TAXA ──────────────────────────────────────────────────────────────
//
// A `CadeiaC2` recusa epoca com taxa medida fora de [0,8; 1,2] x 50 Hz. O app
// pede 20 ms ao sistema, mas cada celular entrega o que quer. Epoca recusada
// por taxa e contada (`recusadas_por_taxa`), e a tela mostra: se o aparelho
// entregar 100 Hz, nenhuma epoca passa, e isso tem de aparecer na primeira
// noite, nao na analise.

#ifndef DORMIO_NUCLEO_COLETOR_CELULAR_H
#define DORMIO_NUCLEO_COLETOR_CELULAR_H

#include <stdint.h>

#include "cadeia_c2.h"
#include "calibracao.h"
#include "caracteristicas.h"
#include "fifo_mpu.h"
#include "payload.h"
#include "relogio.h"

namespace dormio {

// A gravidade padrao, para converter m/s^2 em g. Nao e a `GRAVIDADE_MS2` do
// payload (9,81), que e o limiar de `total`, e sim a da conversao do `ml/`.
const float G_PADRAO_MS2 = 9.80665f;

// Amostras guardadas ate a proxima drenagem. A 60 Hz (o teto que a cadeia
// aceita), 1,7 s sao 102 amostras; a folga cobre um celular mais rapido que
// so vai ter as epocas recusadas.
const uint16_t CAPACIDADE_DA_DRENAGEM = 512;

// Quanto depois da primeira amostra a epoca 0 deve comecar. A cadeia filtra
// com `MARGEM_S` de sinal antes da epoca e ajusta a linha do tempo com
// drenagens de `FOLGA_DO_AJUSTE_S` antes dela: uma origem em cima da primeira
// amostra faz a epoca 0 sair recusada. 3 s cobrem os 2,5 s com folga.
const uint64_t ANTECEDENCIA_DA_ORIGEM_US = 3000000u;

// Um payload com `f` cabe em ~420 bytes (`payload.h`).
const uint32_t TAMANHO_DO_PAYLOAD = 512;

enum ResultadoDoColetor {
  COLETOR_NADA = 0,           // nenhuma epoca fechou ainda
  COLETOR_PAYLOAD = 1,        // `destino` tem o JSON de uma epoca
  COLETOR_EPOCA_RECUSADA = 2, // a cadeia recusou uma epoca (contada)
  COLETOR_SEM_PAYLOAD = 3,    // epoca pronta sem payload honesto (contada)
};

// int16 na escala do MPU6050 da C2, saturado em +-8 g como o sensor saturaria.
int16_t g_para_lsb(float g);

class ColetorCelular {
 public:
  ColetorCelular();

  // `origem_us`: inicio da epoca 0 no relogio monotonico das amostras.
  // `parede`: a correspondencia entre esse relogio e o UTC (o celular sabe a
  // hora; e o que a placa obtem por NTP).
  void iniciar(uint64_t origem_us, const ResolucaoDeParede &parede);

  // Uma amostra, em m/s^2, no instante monotonico `t_us`. Amostras fora de
  // ordem ou repetidas sao descartadas e contadas: a cadeia supoe tempo
  // crescente, e uma amostra fora de ordem entortaria a linha do tempo.
  void amostrar(uint64_t t_us, float ax_ms2, float ay_ms2, float az_ms2);

  // A temperatura que vai no proximo payload (`t`), em graus C. E tambem a
  // que a calibracao usa no termo de temperatura. Sem chamar, ela e
  // desconhecida (DATA-14): sem `t` no payload, sem ponto de calibracao, e a
  // correcao usa a temperatura de referencia da propria calibracao.
  void definir_temperatura(float graus_c) {
    temperatura_c_ = graus_c;
    temperatura_conhecida_ = true;
  }

  // A calibracao das amostras (CAL-03). Sem chamar, ou com uma recusada, as
  // amostras passam como vieram e o payload diz `cal: 0`. Quem estima e o app,
  // entre noites (`estimar_calibracao`); a noite inteira usa a mesma.
  void definir_calibracao(const Calibracao &c) { calibracao_ = c; }
  const Calibracao &calibracao() const { return calibracao_; }

  // O ponto de calibracao da ultima epoca pronta (CAL-03, etapa 2): se ela foi
  // PARADA (`mag_din_media` abaixo de `LIMIAR_PARADO_G`), `saida` recebe o
  // vetor medio da gravidade em g, DESFEITO para o bruto pela calibracao desta
  // noite, e a temperatura: {x, y, z, temp_c}. Bruto porque a proxima
  // estimativa parte do sinal original, e esta noite pode ja ter saido
  // calibrada. Devolve false se a epoca nao foi parada ou nao teve features.
  // Vale ate a proxima chamada de `proximo`.
  bool ponto_parado(double saida[4]) const;

  // Tenta fechar uma epoca. Chamar em laco ate devolver COLETOR_NADA. Com
  // COLETOR_PAYLOAD, `destino` (TAMANHO_DO_PAYLOAD bytes) recebe o JSON,
  // terminado em zero, e `escritos` o tamanho.
  ResultadoDoColetor proximo(char *destino, uint32_t tamanho, uint32_t *escritos);

  uint64_t amostras_recebidas() const { return recebidas_; }
  uint32_t amostras_fora_de_ordem() const { return fora_de_ordem_; }
  uint32_t epocas_com_payload() const { return com_payload_; }
  uint32_t epocas_recusadas() const { return recusadas_; }
  uint32_t recusadas_por_taxa() const { return recusadas_taxa_; }
  // Payload enviado sem `f` (vetor fora das faixas do contrato).
  uint32_t epocas_sem_features() const { return sem_features_; }
  // Epoca pronta sem payload honesto (pico implausivel: sensor nao medindo).
  uint32_t epocas_sem_payload() const { return sem_payload_; }
  // A taxa medida pela cadeia na ultima epoca pronta, em Hz (0 se nenhuma).
  double ultima_taxa_hz() const { return ultima_taxa_hz_; }
  // As features da ultima epoca pronta ANTES da quantizacao do payload, e se
  // houve. Expostas para o teste contra o pipeline do `ml/`.
  const FeaturesDeEpoca &ultimas_features() const { return ultimas_features_; }
  bool ultima_teve_features() const { return ultima_teve_features_; }

 private:
  void drenar();

  CadeiaC2 cadeia_;
  AcumuladorDeFeatures acumulador_;
  ResolucaoDeParede parede_;
  uint64_t origem_us_;
  bool iniciado_;

  AmostraBruta pendentes_[CAPACIDADE_DA_DRENAGEM];
  uint16_t n_pendentes_;
  uint64_t t_primeira_pendente_us_;
  uint64_t t_ultima_us_;
  uint64_t t_ultima_drenagem_us_;
  bool tem_amostra_;

  float grade_x_[AMOSTRAS_NA_GRADE];
  float grade_y_[AMOSTRAS_NA_GRADE];
  float grade_z_[AMOSTRAS_NA_GRADE];

  float temperatura_c_;
  bool temperatura_conhecida_;
  Calibracao calibracao_;
  uint64_t recebidas_;
  uint32_t fora_de_ordem_;
  uint32_t com_payload_;
  uint32_t recusadas_;
  uint32_t recusadas_taxa_;
  uint32_t sem_features_;
  uint32_t sem_payload_;
  double ultima_taxa_hz_;
  FeaturesDeEpoca ultimas_features_;
  bool ultima_teve_features_;
  double ponto_[4];
  bool tem_ponto_;
};

}  // namespace dormio

#endif  // DORMIO_NUCLEO_COLETOR_CELULAR_H
