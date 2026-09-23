// reconexao.h -- quando vale a pena tentar a rede de novo.
//
// ── O QUE ESTA POLITICA DECIDE, E O QUE ELA NAO FAZ ────────────────────
//
// Ela responde uma pergunta so: "ja posso tentar?". Nao conecta, nao espera,
// nao chama nada. A espera vira consulta a um relogio, e por isso a
// amostragem nunca para para esperar rede -- que e o requisito 1 de tudo
// isto.
//
// ── POR QUE BACKOFF EXPONENCIAL, E POR QUE COM TETO ────────────────────
//
// Tentar reconectar a cada ciclo custa radio ligado, e o radio e o maior
// consumidor da placa. Numa queda de rede de tres horas, tentar a cada 10 s
// sao 1080 tentativas de handshake -- gastando bateria para falhar.
//
// Mas o teto e igualmente necessario: sem ele, o intervalo cresceria ate
// horas, e a rede voltaria sem o aparelho perceber. O objetivo nao e
// economizar o maximo; e cobrir a queda tipica (minutos) com poucas
// tentativas e ainda reagir em menos de dois minutos quando ela acabar.
//
// ── POR QUE JITTER ────────────────────────────────────────────────────
//
// Sem jitter, varios dispositivos que perderam a mesma rede (o roteador
// reiniciou) voltam a tentar exatamente juntos, e continuam juntos para
// sempre -- e o pico coincidente derruba de novo o AP que acabou de subir.
// O jitter e determinístico aqui (sem `rand()`, que exige semente e estado
// global): deriva do numero de tentativas e de um identificador do aparelho.
//
// ── O TETO CONVERSA COM O CUSTO DE DRENAR ──────────────────────────────
//
// Drenar o buffer e, hoje, um POST por epoca -- e cada POST ao Vercel abre um
// handshake TLS novo. Seis horas de buffer a 30 s sao 720 POSTs (nao 2160:
// agregar em epoca ja divide por tres na cadencia de 10 s, e por muito mais
// quando o FW-05 subir a amostragem para >= 42 Hz). Ainda assim e muito, e e
// por isso que a drenagem aqui e LIMITADA por rajada: `maximo_por_rajada`
// entrega um pedaco, devolve o controle ao laco de amostragem e continua no
// ciclo seguinte. Um endpoint de lote no backend e o que resolve isso de
// verdade -- esta aberto no backlog como `API-03`.

#ifndef DORMIO_NUCLEO_RECONEXAO_H
#define DORMIO_NUCLEO_RECONEXAO_H

#include <stdint.h>

namespace dormio {

struct ParametrosDeBackoff {
  uint32_t base_ms;      // espera apos a primeira falha
  uint32_t teto_ms;      // espera maxima entre tentativas
  uint32_t jitter_ms;    // amplitude do desvio deterministico
  uint32_t orcamento_ms; // tempo maximo que UMA tentativa pode custar

  ParametrosDeBackoff()
      : base_ms(2000),      // 2 s: uma queda curta se resolve na primeira
        teto_ms(120000),    // 2 min: cobre uma queda longa sem sumir da rede
        jitter_ms(1500),
        orcamento_ms(8000)  // 8 s, contra os 20 s de hoje -- ver nota abaixo
  {}
};

// NOTA sobre `orcamento_ms`: 20 s de timeout (o valor de hoje no
// envio-continuo) so nao e um problema porque a conexao la e SINCRONA dentro
// do laco. Uma vez que a amostragem nao depende mais dela, o orcamento pode
// ser curto: se o AP nao respondeu em 8 s, ele nao vai responder, e o backoff
// cuida da proxima tentativa. Curto e barato quando nao custa a medida.

class PoliticaDeReconexao {
 public:
  explicit PoliticaDeReconexao(uint32_t semente_do_aparelho = 0)
      : semente_(semente_do_aparelho), tentativas_(0), proxima_em_(0),
        conectado_(false), iniciado_(false), falhas_totais_(0),
        sucessos_totais_(0) {}

  void definir_parametros(const ParametrosDeBackoff &p) { parametros_ = p; }
  const ParametrosDeBackoff &parametros() const { return parametros_; }

  void iniciar(uint64_t mono_ms) {
    iniciado_ = true;
    proxima_em_ = mono_ms;  // a primeira tentativa e imediata
    tentativas_ = 0;
    conectado_ = false;
  }

  bool conectado() const { return conectado_; }
  uint32_t tentativas_seguidas() const { return tentativas_; }
  uint32_t falhas_totais() const { return falhas_totais_; }
  uint32_t sucessos_totais() const { return sucessos_totais_; }

  // True quando a janela de backoff expirou e vale a pena tentar de novo.
  // Nao bloqueia, nao tem efeito colateral: e so uma comparacao de relogio.
  bool deve_tentar(uint64_t mono_ms) const {
    if (!iniciado_ || conectado_) return false;
    return mono_ms >= proxima_em_;
  }

  void registrar_sucesso(uint64_t /*mono_ms*/) {
    conectado_ = true;
    tentativas_ = 0;
    sucessos_totais_++;
  }

  void registrar_falha(uint64_t mono_ms) {
    conectado_ = false;
    falhas_totais_++;
    if (tentativas_ < 30) tentativas_++;  // trava o expoente antes do overflow
    proxima_em_ = mono_ms + espera_atual();
  }

  // A rede caiu depois de conectada (POST falhou por conexao, por exemplo).
  // Volta ao regime de tentativa sem penalizar como se fosse falha de
  // handshake: a primeira tentativa de reconexao e imediata.
  void registrar_queda(uint64_t mono_ms) {
    conectado_ = false;
    tentativas_ = 0;
    proxima_em_ = mono_ms;
  }

  // Espera que sera aplicada apos a contagem atual de falhas.
  uint32_t espera_atual() const {
    if (tentativas_ == 0) return 0;
    uint64_t espera = parametros_.base_ms;
    for (uint32_t i = 1; i < tentativas_ && espera < parametros_.teto_ms; i++) {
      espera *= 2;
    }
    if (espera > parametros_.teto_ms) espera = parametros_.teto_ms;

    // Jitter deterministico em [0, jitter_ms). Mistura tentativa e semente
    // com uma constante impar grande -- basta para descorrelacionar
    // aparelhos, e nao precisa de estado global nem de `rand()`.
    if (parametros_.jitter_ms > 0) {
      uint32_t h = (semente_ * 2654435761u) ^ (tentativas_ * 40503u);
      h ^= h >> 13;
      espera += h % parametros_.jitter_ms;
    }
    return espera > 0xFFFFFFFFull ? 0xFFFFFFFFu : static_cast<uint32_t>(espera);
  }

  uint64_t proxima_tentativa_em() const { return proxima_em_; }

 private:
  ParametrosDeBackoff parametros_;
  uint32_t semente_;
  uint32_t tentativas_;
  uint64_t proxima_em_;
  bool conectado_;
  bool iniciado_;
  uint32_t falhas_totais_;
  uint32_t sucessos_totais_;
};

}  // namespace dormio

#endif  // DORMIO_NUCLEO_RECONEXAO_H
