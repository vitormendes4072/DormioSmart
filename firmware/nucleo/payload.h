// payload.h -- monta o corpo do POST /api/data a partir de uma epoca.
//
// Fica no nucleo, e nao no .ino, por um motivo pratico: e a camada onde os
// erros de contrato aparecem (campo faltando, `metodo` sem `epoca_s`, `total`
// que nao bate com ax/ay/az), e aqui ela roda no host, com g++, contra
// `docs/DATA-CONTRACT.md`. No .ino so daria para descobrir gravando a placa e
// lendo o 400 no monitor serial.
//
// Sem `String` do Arduino: escreve num buffer de char que o chamador possui.

#ifndef DORMIO_NUCLEO_PAYLOAD_H
#define DORMIO_NUCLEO_PAYLOAD_H

#include <stdint.h>

#include "caracteristicas.h"
#include "epoca.h"
#include "relogio.h"

namespace dormio {

// Criterio de movimento, contrato secao 2.2. Quem classifica e o DISPOSITIVO;
// o painel exibe o rotulo e nunca recalcula.
const float GRAVIDADE_MS2 = 9.81f;
const float LIMIAR_MOVIMENTO_MS2 = 1.2f;  // PROVISORIO -- recalibrar em VIA-01

// Faixa fisicamente plausivel de |a|. Fora dela nao e medida: e sensor mudo.
// Ver a nota longa no topo de `envio-continuo.ino`.
const float MAGNITUDE_MINIMA_PLAUSIVEL = 3.0f;
const float MAGNITUDE_MAXIMA_PLAUSIVEL = 20.0f;

const char *const METODO_AGREGACAO = "pico-da-magnitude";
const char *const STATUS_REPOUSO = "Repouso";
const char *const STATUS_MOVIMENTO = "Movimento";

inline const char *classificar(float total) {
  float intensidade = total - GRAVIDADE_MS2;
  if (intensidade < 0) intensidade = -intensidade;
  return intensidade > LIMIAR_MOVIMENTO_MS2 ? STATUS_MOVIMENTO : STATUS_REPOUSO;
}

inline bool magnitude_plausivel(float total) {
  return total >= MAGNITUDE_MINIMA_PLAUSIVEL && total <= MAGNITUDE_MAXIMA_PLAUSIVEL;
}

enum ResultadoDeMontagem {
  PAYLOAD_OK = 0,
  // A epoca nao recebeu amostra nenhuma. NAO existe payload honesto para ela:
  // `ax/ay/az/total` sao obrigatorios e inventa-los seria fabricar medida.
  // A lacuna aparece no backend como intervalo entre dois `ts` -- que e
  // exatamente o que ela e.
  PAYLOAD_EPOCA_VAZIA = 1,
  // Pico fora da faixa fisica: sensor respondendo e nao medindo.
  PAYLOAD_MAGNITUDE_IMPLAUSIVEL = 2,
  // Duracao acima do teto do backend. So acontece se alguem mexer em
  // NIVEL_MAXIMO sem olhar `validar_agregacao`.
  PAYLOAD_EPOCA_LONGA_DEMAIS = 3,
  PAYLOAD_BUFFER_PEQUENO = 4,
};

// Converte epoch unix em ms para "AAAA-MM-DDTHH:MM:SS.mmmZ".
//
// Sem `gmtime`: o algoritmo de dias civis e determinístico, cabe em vinte
// linhas e e testavel no host sem depender de fuso, locale ou de qual libc a
// toolchain do ESP32 usa hoje. `destino` precisa de 25 bytes.
// Devolve o numero de caracteres escritos, ou 0 se nao coube.
uint32_t formatar_iso8601_utc(int64_t unix_ms, char *destino, uint32_t tamanho);

// Monta o JSON. `destino` precisa de ~200 bytes com folga, e de ~420 com `f`.
//
// `parede` resolve o instante da MEDIÇÃO. Se nao estiver sincronizada, o
// campo `ts` sai FORA do payload -- e o backend cai no `created_at` do
// recebimento, que e o comportamento antigo e conhecido. Carimbar uma hora
// inventada seria pior: o backend aceitaria, e a noite ficaria arquivada com
// um horario que ninguem mais consegue corrigir.
//
// `ts` e o INICIO da epoca, nao o fim nem o instante do pico. Convencao de
// actigrafia (a epoca e rotulada pelo seu inicio) e a unica que mantem
// `ts[k+1] - ts[k] == epoca_s` para epocas consecutivas -- o que faz a
// deteccao de lacuna do dashboard funcionar por subtracao simples. Com o fim,
// a primeira epoca da serie apareceria 30 s adiantada; com o instante do
// pico, o espacamento viraria ruido.
//
// ── `f`, `g` e `fs` (contrato §2.6, DATA-07b) ──────────────────────────
//
// Com `features` nao nulo, o payload ganha o vetor da epoca: as 6 features em
// g, na ordem canonica, a direcao da gravidade e a taxa da grade que as
// produziu. Mas SO quando o vetor e honesto para aquela leitura:
//
//   - epoca de nivel 0 (30 s). Epoca degradada e a fusao de varias, e as
//     features nao fundem (`caracteristicas.h`): o vetor de uma delas
//     descreveria 30 s de uma leitura que resume 60 ou mais.
//   - cada valor dentro da faixa do contrato. Uma epoca de movimento violento
//     pode levar `mag_din_media` acima de 2 g; o backend recusaria a leitura
//     INTEIRA com 400, e o pico, que e valido, se perderia junto. Sem `f`, a
//     leitura entra e o vetor daquela epoca e que falta -- perda declarada e
//     menor.
//
// Fora disso o payload sai sem `f`, com PAYLOAD_OK: payload sem `f` continua
// sendo o payload correto (dispositivo antigo e dispositivo valido).
// `features_incluidas`, quando nao nulo, diz qual dos dois saiu.
ResultadoDeMontagem montar_payload(const Epoca &e, const ResolucaoDeParede &parede,
                                   uint64_t mono_do_inicio_da_epoca_ms, char *destino,
                                   uint32_t tamanho, uint32_t *escritos,
                                   const FeaturesDeEpoca *features = 0, float fs_hz = 0.0f,
                                   bool *features_incluidas = 0);

// O vetor esta dentro das faixas do contrato §2.6? (`g` unitario a 1e-3.)
bool features_no_contrato(const FeaturesDeEpoca &f, float fs_hz);

}  // namespace dormio

#endif  // DORMIO_NUCLEO_PAYLOAD_H
