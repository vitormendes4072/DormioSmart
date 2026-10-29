// cadencia.h -- quando amostrar, e o que fazer quando o ritmo escapa.
//
// ── A CADENCIA E SAGRADA ───────────────────────────────────────────────
//
// Actigrafia opera em epoca FIXA de 30 s. Um dado cuja base de tempo derivou
// nao e um dado pior: e um dado que parece bom e nao e. A perda de uma epoca
// a analise ve; 25 s de deriva acumulada ela nao ve, e continua contando como
// se fosse 30.
//
// Dai as duas regras deste modulo:
//
// 1. A grade e ABSOLUTA. O proximo instante de amostragem e sempre
//    `t0 + k * periodo`, calculado a partir da ancora, NUNCA
//    `ultima_amostra + periodo`. Na segunda forma, todo atraso de execucao
//    entra permanentemente na base de tempo e nunca mais sai. Na primeira, um
//    atraso e absorvido pelo tick seguinte.
//
// 2. Atraso NAO se recupera amostrando mais rapido. Se o laco ficou preso e
//    tres ticks passaram, este modulo pula para o tick corrente e CONTA os
//    tres perdidos. Disparar tres amostras em sequencia para "compensar"
//    poria tres medidas no instante errado -- de novo, distorcao com cara de
//    dado. Os ticks perdidos viram `EPOCA_INCOMPLETA` la no acumulador.
//
// ── POR QUE ISTO NAO CHAMA delay() ─────────────────────────────────────
//
// O modulo so responde `deve_amostrar(agora)`. Quem espera e o laco, e ele
// espera pouco e sem bloquear. Um `delay(500)` dentro do laco de amostragem
// -- que e o que `conectarWiFi()` faz hoje no envio-continuo -- transforma
// cada queda de rede em 20 s de cegueira sensorial. Com intervalo de 10 s,
// isso e a cadencia inteira colapsando por causa do roteador.

#ifndef DORMIO_NUCLEO_CADENCIA_H
#define DORMIO_NUCLEO_CADENCIA_H

#include <stdint.h>

namespace dormio {

class ControleDeCadencia {
 public:
  ControleDeCadencia()
      : ancora_ms_(0), periodo_ms_(1000), proximo_tick_(0), ticks_servidos_(0),
        ticks_perdidos_(0), maior_atraso_ms_(0), iniciado_(false) {}

  void iniciar(uint64_t mono_ms, uint32_t periodo_ms) {
    ancora_ms_ = mono_ms;
    periodo_ms_ = periodo_ms == 0 ? 1 : periodo_ms;
    proximo_tick_ = 0;
    ticks_servidos_ = 0;
    ticks_perdidos_ = 0;
    maior_atraso_ms_ = 0;
    iniciado_ = true;
  }

  uint64_t instante_do_tick(uint64_t k) const {
    return ancora_ms_ + k * static_cast<uint64_t>(periodo_ms_);
  }

  // True quando ha um tick devido. Consome o tick: contabiliza o atraso e os
  // ticks que passaram em branco, e agenda o proximo na GRADE.
  bool deve_amostrar(uint64_t mono_ms) {
    if (!iniciado_) return false;
    uint64_t devido = instante_do_tick(proximo_tick_);
    if (mono_ms < devido) return false;

    uint64_t atraso = mono_ms - devido;
    if (atraso > maior_atraso_ms_) maior_atraso_ms_ = atraso;

    // Quantos ticks inteiros ja passaram alem deste.
    uint64_t pulados = atraso / periodo_ms_;
    if (pulados > 0) {
      ticks_perdidos_ += pulados;
      proximo_tick_ += pulados;  // pula para o tick corrente, sem compensar
    }

    ticks_servidos_++;
    proximo_tick_++;
    return true;
  }

  // Quanto falta para o proximo tick. O laco usa isto para dormir POUCO --
  // nunca mais do que o teto que ele mesmo define.
  uint32_t ms_ate_o_proximo(uint64_t mono_ms) const {
    if (!iniciado_) return periodo_ms_;
    uint64_t devido = instante_do_tick(proximo_tick_);
    if (mono_ms >= devido) return 0;
    uint64_t falta = devido - mono_ms;
    return falta > 0xFFFFFFFFull ? 0xFFFFFFFFu : static_cast<uint32_t>(falta);
  }

  uint32_t periodo_ms() const { return periodo_ms_; }
  uint64_t ticks_servidos() const { return ticks_servidos_; }
  uint64_t ticks_perdidos() const { return ticks_perdidos_; }
  uint64_t maior_atraso_ms() const { return maior_atraso_ms_; }

  // Quantas amostras uma epoca de `duracao_s` deveria conter nesta cadencia.
  // O acumulador usa isto para saber o que cobrar.
  uint16_t amostras_por_epoca(uint16_t duracao_s) const {
    uint32_t n = (static_cast<uint32_t>(duracao_s) * 1000u) / periodo_ms_;
    if (n == 0) n = 1;
    return n > 0xFFFFu ? 0xFFFFu : static_cast<uint16_t>(n);
  }

 private:
  uint64_t ancora_ms_;
  uint32_t periodo_ms_;
  uint64_t proximo_tick_;
  uint64_t ticks_servidos_;
  uint64_t ticks_perdidos_;
  uint64_t maior_atraso_ms_;
  bool iniciado_;
};

}  // namespace dormio

#endif  // DORMIO_NUCLEO_CADENCIA_H
