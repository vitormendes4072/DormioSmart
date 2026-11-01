// radio.h -- quem pode usar o radio, entre as duas tarefas do sketch (FW-09).
//
// ── O DEFEITO QUE ISTO FECHA ───────────────────────────────────────────
//
// No `sketch.ino` da C2 a medicao (nucleo 1) avisa a tarefa de envio
// (nucleo 0) e volta ao topo do laco, onde decide entre sono leve e espera
// acordada olhando uma flag de "Wi-Fi ativo". Ate 01/11 quem ligava a flag
// era a tarefa de ENVIO, depois de acordar. Na janela entre o aviso e essa
// linha, a medicao via o radio livre e chamava `esp_light_sleep_start()`, que
// adormece os dois nucleos e desliga o radio no meio do `WiFi.begin()`.
// Achado A1 da auditoria de 31/10 (`docs/AUDITORIA-2026-10-31.md`).
//
// ── A REGRA ────────────────────────────────────────────────────────────
//
// Quem PEDE o radio o reserva, num passo atomico, antes de avisar. Quem o
// USA o devolve -- ao terminar, e tambem quando decide nao tentar (fila
// indisponivel, politica de reconexao mandando esperar). Esquecer a
// devolucao no caminho de desistencia deixaria a medicao acordada para
// sempre: e o lado da regra que custa bateria em vez de dado.
//
// Header-only e sem dependencia de Arduino: a regra e testada no host
// (`testes/testes_c2.cpp`), e o sketch so a usa.

#ifndef DORMIO_NUCLEO_RADIO_H
#define DORMIO_NUCLEO_RADIO_H

#include <atomic>

namespace dormio {

class CoordenacaoDoRadio {
 public:
  CoordenacaoDoRadio() : reservado_(false) {}

  // A medicao chama antes de avisar a tarefa de envio. Devolve true se
  // reservou o radio (pode avisar), false se ele ja estava reservado (um
  // envio esta em curso; nao avisar de novo).
  bool pedir_envio() {
    bool livre = false;
    return reservado_.compare_exchange_strong(livre, true);
  }

  // A medicao so entra em sono leve com o radio livre: o sono leve derruba
  // a conexao.
  bool pode_dormir() const { return !reservado_.load(); }

  // A tarefa de envio devolve o radio: ao terminar, ou ao desistir.
  void liberar() { reservado_.store(false); }

 private:
  std::atomic<bool> reservado_;
};

}  // namespace dormio

#endif  // DORMIO_NUCLEO_RADIO_H
