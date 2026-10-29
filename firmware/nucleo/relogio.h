// relogio.h -- tempo monotonico estendido, sem depender do Arduino.
//
// ── POR QUE ESTA CAMADA EXISTE ─────────────────────────────────────────
//
// O ESP32 nao tem RTC com bateria: perde o relogio de parede a cada Deep
// Sleep e so reaprende a hora depois que a rede sobe. Se o buffer guardasse
// hora de parede, uma noite inteira captada offline sairia carimbada com a
// hora errada -- ou pior, com a hora do BOOT, que e sempre a mesma.
//
// Entao o buffer guarda tempo MONOTONICO (millis()) e a hora de parede so e
// resolvida na hora de drenar, quando ela existe. Ver `ResolucaoDeParede`
// no fim deste arquivo.
//
// ── O PROBLEMA DO WRAP ─────────────────────────────────────────────────
//
// `millis()` e uint32 e da a volta em 2^32 ms = 49,7 dias. Uma noite nao
// chega perto disso, mas um instrumento de bancada que fica semanas ligado
// chega -- e o modo como ele falha e silencioso: `agora - antes` vira um
// numero gigante e a cadencia colapsa sem nenhum erro aparecer.
//
// A subtracao de uint32 sobrevive ao wrap sozinha (aritmetica modular), mas
// so para intervalos curtos. O indice de epoca precisa crescer para sempre,
// entao aqui estendemos para 64 bits contando as voltas.

#ifndef DORMIO_NUCLEO_RELOGIO_H
#define DORMIO_NUCLEO_RELOGIO_H

#include <stdint.h>

namespace dormio {

// Estende millis() (uint32, da a volta em 49,7 dias) para 64 bits.
//
// Contrato de uso: `atualizar` tem de ser chamado com frequencia maior que o
// periodo de wrap. Como o laco de amostragem roda em segundos e o wrap e em
// semanas, a margem e de sete ordens de grandeza.
class RelogioMonotonico {
 public:
  RelogioMonotonico() : ultimo_bruto_(0), voltas_(0), iniciado_(false) {}

  // Recebe a leitura crua de millis() e devolve o tempo estendido em ms.
  uint64_t atualizar(uint32_t bruto) {
    if (!iniciado_) {
      iniciado_ = true;
      ultimo_bruto_ = bruto;
      return bruto;
    }
    if (bruto < ultimo_bruto_) {
      // O contador andou para tras: so pode ter dado a volta.
      voltas_++;
    }
    ultimo_bruto_ = bruto;
    return (static_cast<uint64_t>(voltas_) << 32) | static_cast<uint64_t>(bruto);
  }

  uint64_t agora() const {
    return (static_cast<uint64_t>(voltas_) << 32) | static_cast<uint64_t>(ultimo_bruto_);
  }

  uint32_t voltas() const { return voltas_; }

 private:
  uint32_t ultimo_bruto_;
  uint32_t voltas_;
  bool iniciado_;
};

// ── Resolucao para hora de parede ──────────────────────────────────────
//
// O buffer guarda `mono_ms`. Na hora de enviar, ja com rede e hora
// sincronizada, sabemos o par (mono_agora, parede_agora) e resolvemos:
//
//     parede_do_dado = parede_agora - (mono_agora - mono_do_dado)
//
// Sempre para TRAS, nunca para frente. Isso importa porque o backend so
// recusa timestamp no futuro (`validar_captacao`, tolerancia de 5 min):
// leitura antiga passa, leitura adiantada nao. Resolver para tras e, por
// construcao, o lado seguro.
//
// `valida` e falso enquanto a hora de parede nunca foi sincronizada. Nesse
// caso o firmware envia SEM o campo `ts` -- o backend entao usa o
// `created_at` do recebimento, que e o comportamento antigo e conhecido.
// Enviar uma hora inventada seria pior que nao enviar hora nenhuma.
struct ResolucaoDeParede {
  bool valida;
  uint64_t mono_referencia_ms;   // tempo monotonico no instante da sincronia
  int64_t parede_referencia_ms;  // epoch unix em ms no mesmo instante

  ResolucaoDeParede() : valida(false), mono_referencia_ms(0), parede_referencia_ms(0) {}

  void sincronizar(uint64_t mono_ms, int64_t parede_unix_ms) {
    mono_referencia_ms = mono_ms;
    parede_referencia_ms = parede_unix_ms;
    valida = true;
  }

  // Devolve o instante de parede (epoch unix ms) de um evento monotonico.
  // So chame com `valida == true`.
  int64_t resolver(uint64_t mono_do_evento_ms) const {
    // Deslocamento assinado: evento anterior a referencia da negativo, que e
    // o caso normal do buffer (dado velho sendo drenado agora).
    int64_t delta = static_cast<int64_t>(mono_do_evento_ms) -
                    static_cast<int64_t>(mono_referencia_ms);
    return parede_referencia_ms + delta;
  }
};

}  // namespace dormio

#endif  // DORMIO_NUCLEO_RELOGIO_H
