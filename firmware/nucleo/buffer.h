// buffer.h -- fila de epocas com degradacao de resolucao no lugar do descarte.
//
// ── POR QUE LACUNA VIRA REGISTRO ───────────────────────────────────────
//
// O acumulador entrega epocas VAZIAS quando a amostragem falhou, e elas
// entram no buffer como qualquer outra. Parece desperdicio de memoria --
// guardar 32 bytes para dizer "aqui nao houve medida". Nao e.
//
// Sem esse registro, a analise recebe uma sequencia de epocas consecutivas e
// nao tem como distinguir "a noite inteira medida" de "metade da noite, com
// os pedacos encostados". A base de tempo pareceria intacta. Para actigrafia,
// cuja unidade E a epoca de 30 s, isso nao e perda de dado: e dado ERRADO com
// aparencia de certo. Uma lacuna declarada custa 32 bytes e a analise a ve;
// uma lacuna silenciosa custa a validade da noite.
//
// ── POR QUE DEGRADAR, E NAO DESCARTAR ──────────────────────────────────
//
// Buffer cheio com amostras instantaneas so tem saidas ruins (ver o cabecalho
// de `epoca.h`). Com epocas ha uma terceira: ao passar do limiar de ocupacao,
// fundir pares adjacentes das epocas MAIS ANTIGAS e liberar metade do espaco
// que elas ocupavam.
//
// O mais antigo e o alvo certo por dois motivos. Primeiro, o inicio da noite
// e onde a resolucao de 30 s vale menos: o adormecer e uma transicao de
// dezenas de minutos, nao um evento de 30 s -- em 60 s ele continua visivel.
// Segundo, uma degradacao aplicada ao fim da fila comprometeria o dado que
// esta sendo medido AGORA, cuja resolucao ainda pode importar.
//
// E a degradacao nao introduz erro nenhum: o pico de duas epocas e o pico da
// epoca dobrada, exato. Ver `epoca.h`.
//
// ── SEM ALOCACAO DINAMICA ──────────────────────────────────────────────
//
// Arranjo de tamanho fixo definido em tempo de compilacao. Firmware que
// fragmenta heap a noite inteira falha no pior momento possivel: depois de
// horas de coleta, com o dado ainda nao entregue.

#ifndef DORMIO_NUCLEO_BUFFER_H
#define DORMIO_NUCLEO_BUFFER_H

#include <stdint.h>

#include "epoca.h"

namespace dormio {

struct EstatisticasDoBuffer {
  uint32_t epocas_guardadas;
  uint32_t epocas_drenadas;
  uint32_t degradacoes;        // quantas vezes a fila foi degradada
  uint32_t fusoes;             // quantos pares foram fundidos ao todo
  uint8_t nivel_maximo;        // pior resolucao ja produzida
  uint32_t descartes;          // epocas perdidas de vez -- ver `guardar`

  EstatisticasDoBuffer()
      : epocas_guardadas(0), epocas_drenadas(0), degradacoes(0), fusoes(0),
        nivel_maximo(0), descartes(0) {}
};

// `Capacidade` em numero de epocas. O valor certo sai da medicao: veja
// `capacidade.cpp` e o README deste diretorio.
template <uint32_t Capacidade>
class BufferDeEpocas {
 public:
  BufferDeEpocas() : inicio_(0), tamanho_(0), limiar_percentual_(75) {}

  // Ocupacao (em %) a partir da qual a fila degrada antes de aceitar a
  // proxima epoca. Abaixo de 100 de proposito: degradar so na borda faria a
  // fusao competir com a escrita no instante mais apertado.
  void definir_limiar(uint8_t percentual) { limiar_percentual_ = percentual; }

  uint32_t tamanho() const { return tamanho_; }
  uint32_t capacidade() const { return Capacidade; }
  bool vazio() const { return tamanho_ == 0; }
  bool cheio() const { return tamanho_ == Capacidade; }
  uint8_t ocupacao_percentual() const {
    return static_cast<uint8_t>((static_cast<uint64_t>(tamanho_) * 100u) / Capacidade);
  }
  const EstatisticasDoBuffer &estatisticas() const { return stats_; }

  const Epoca &em(uint32_t i) const { return dados_[(inicio_ + i) % Capacidade]; }

  // Guarda uma epoca. Degrada antes, se a ocupacao passou do limiar.
  //
  // Devolve false quando nem a degradacao liberou espaco. Isso exige a fila
  // inteira ja no nivel 6 (o teto do contrato), o que significa mais de
  // `Capacidade * 32 min` de coleta sem entregar nada -- com 128 epocas, 68
  // horas. Se isso acontecer numa noite, o problema nao e o buffer.
  //
  // Nesse extremo a escolha e recusar o NOVO, nao sobrescrever o velho: o que
  // ja esta na fila e um registro continuo e verificavel, e furar o meio dele
  // para caber mais uma epoca trocaria uma perda declarada (o contador
  // `descartes`, que o firmware loga) por uma serie com buraco silencioso.
  // Mesmo principio da epoca vazia: perda visivel e melhor que perda muda.
  bool guardar(const Epoca &e) {
    if (ocupacao_percentual() >= limiar_percentual_) {
      degradar();
    }
    if (cheio()) {
      // Ultimo recurso: degradar de novo, agressivamente.
      degradar();
    }
    if (cheio()) {
      stats_.descartes++;
      return false;
    }
    dados_[(inicio_ + tamanho_) % Capacidade] = e;
    tamanho_++;
    stats_.epocas_guardadas++;
    if (e.nivel > stats_.nivel_maximo) stats_.nivel_maximo = e.nivel;
    return true;
  }

  // Le a epoca mais antiga sem remover. Drenar e confirmar sao separados de
  // proposito: a epoca so sai da fila depois que o backend confirmou 201. Se
  // o POST falhar no meio, o dado continua aqui.
  bool primeira(Epoca *saida) const {
    if (tamanho_ == 0) return false;
    *saida = dados_[inicio_];
    return true;
  }

  // Remove a mais antiga. Chame SO apos confirmacao de entrega.
  bool confirmar_entrega() {
    if (tamanho_ == 0) return false;
    inicio_ = (inicio_ + 1) % Capacidade;
    tamanho_--;
    stats_.epocas_drenadas++;
    return true;
  }

  // Funde pares adjacentes e compativeis, varrendo do mais antigo para o mais
  // novo. Um par so funde se estiver no mesmo nivel e for adjacente na grade
  // daquele nivel (indice par seguido do impar imediato) -- assim o instante
  // de cada epoca continua derivavel da grade, sem nenhuma reancoragem.
  //
  // Devolve quantos pares foram fundidos.
  uint32_t degradar() {
    if (tamanho_ < 2) return 0;

    uint32_t escrita = 0;
    uint32_t leitura = 0;
    uint32_t fundidos = 0;

    while (leitura < tamanho_) {
      Epoca atual = dados_[(inicio_ + leitura) % Capacidade];

      if (leitura + 1 < tamanho_) {
        const Epoca &prox = dados_[(inicio_ + leitura + 1) % Capacidade];
        bool mesmo_nivel = (atual.nivel == prox.nivel);
        bool alinhada = (atual.indice % 2u == 0u);
        bool adjacente = (prox.indice == atual.indice + 1u);
        // Teto imposto pelo backend: acima do nivel 6 a epoca passa de 3600 s
        // e `validar_agregacao` responde 400. Ver a nota em `epoca.h`.
        bool cabe_no_contrato = (atual.nivel < NIVEL_MAXIMO);
        if (mesmo_nivel && alinhada && adjacente && cabe_no_contrato) {
          fundir(&atual, prox);
          leitura += 2;
          fundidos++;
        } else {
          leitura += 1;
        }
      } else {
        leitura += 1;
      }

      dados_[(inicio_ + escrita) % Capacidade] = atual;
      escrita++;
    }

    tamanho_ = escrita;
    if (fundidos > 0) {
      stats_.degradacoes++;
      stats_.fusoes += fundidos;
      for (uint32_t i = 0; i < tamanho_; i++) {
        if (em(i).nivel > stats_.nivel_maximo) stats_.nivel_maximo = em(i).nivel;
      }
    }
    return fundidos;
  }

  // Quantas horas de cobertura a fila guarda hoje.
  double horas_cobertas() const {
    uint64_t segundos = 0;
    for (uint32_t i = 0; i < tamanho_; i++) segundos += em(i).duracao_s;
    return static_cast<double>(segundos) / 3600.0;
  }

 private:
  Epoca dados_[Capacidade];
  uint32_t inicio_;
  uint32_t tamanho_;
  uint8_t limiar_percentual_;
  EstatisticasDoBuffer stats_;
};

}  // namespace dormio

#endif  // DORMIO_NUCLEO_BUFFER_H
