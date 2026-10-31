// fila_flash.h -- fila de epocas na flash, que sobrevive a reset (FW-08).
//
// ── O PROBLEMA ─────────────────────────────────────────────────────────
//
// A fila em RAM (`buffer.h`) tem tres limites que a noite com features nao
// aguenta: nao guarda o vetor, perde tudo num reset, e quando enche funde
// epocas -- e epoca fundida nao tem features. A flash do ESP32 resolve os
// tres: e nao-volatil, e a particao de dados cabe mais de uma semana de
// epocas de 30 s (`make capacidade`).
//
// ── O DESENHO: UM LOG CIRCULAR SOBRE A PARTICAO CRUA ───────────────────
//
// Registros de 64 B (`registro_flash.h`) gravados em sequencia; ao chegar ao
// fim da particao, volta ao comeco. Antes de gravar no primeiro slot de um
// setor, o setor e apagado -- e SO se nao tiver nenhum registro pendente.
// Se tiver, a fila esta cheia: a epoca NOVA e recusada e contada, como a
// fila em RAM faz no limite. Nunca se apaga o que o servidor nao confirmou.
//
// Escolhido no lugar de LittleFS e NVS (decisao de 31/10, no plano do
// FW-08): LittleFS grava metadado do proprio sistema de arquivos a cada
// registro, e testa-lo no host exigiria a biblioteca; NVS foi feito para
// configuracao, nao para dezenas de milhares de registros. O log circular
// cabe neste arquivo e e testado inteiro contra uma flash simulada que
// obedece as regras da NOR (testes/testes_fila_flash.cpp).
//
// O desgaste e nivelado por construcao: cada setor e apagado uma vez por
// volta do log, e a volta passa por todos os setores na mesma ordem.
//
// ── O QUE SOBREVIVE A UM CORTE DE ENERGIA ──────────────────────────────
//
// `montar()` le a particao inteira ao ligar e reconstroi o estado:
//
//   - a cabeca fica logo depois do registro de maior `seq`;
//   - a cauda e o primeiro registro valido e pendente a partir da cabeca,
//     dando a volta -- a ordem fisica e a ordem de gravacao;
//   - a sessao nova e a maior sessao gravada mais um.
//
// Gravacao cortada deixa um slot nem vazio nem valido: o CRC o recusa, ele e
// contado como corrompido e pulado, e nada do que veio antes se perde.
// Apagamento cortado deixa o setor com lixo; como ele so comeca quando o
// setor nao tem pendente, o lixo nao custa dado, e o setor e apagado de novo.
//
// ── SEM ALOCACAO DINAMICA ──────────────────────────────────────────────
//
// O estado e meia duzia de inteiros. Os registros moram na flash; a RAM so
// ve um lote por vez, num arranjo de quem chama.

#ifndef DORMIO_NUCLEO_FILA_FLASH_H
#define DORMIO_NUCLEO_FILA_FLASH_H

#include <stdint.h>

#include "caracteristicas.h"
#include "epoca.h"
#include "payload.h"
#include "registro_flash.h"
#include "relogio.h"

namespace dormio {

const uint32_t TAMANHO_DO_SETOR_BYTES = 4096;
const uint32_t REGISTROS_POR_SETOR = TAMANHO_DO_SETOR_BYTES / TAMANHO_DO_REGISTRO_FLASH_BYTES;

// A flash vista pela fila. Enderecos relativos ao inicio da particao. A
// implementacao do ESP32 esta em `firmware/midia_flash_esp32.h`; a dos
// testes, em `testes/testes_fila_flash.cpp`.
//
// Semantica de NOR, que a fila respeita e o simulador confere: `programar`
// so leva bits de 1 a 0, e `apagar_setor` leva os 4 KiB inteiros a 0xFF.
class MidiaFlash {
 public:
  virtual ~MidiaFlash() {}
  virtual uint32_t tamanho() const = 0;
  virtual bool ler(uint32_t endereco, void *destino, uint32_t n) = 0;
  virtual bool programar(uint32_t endereco, const void *origem, uint32_t n) = 0;
  virtual bool apagar_setor(uint32_t endereco) = 0;
};

struct EstatisticasDaFila {
  uint32_t guardados;
  uint32_t confirmados;
  uint32_t descartes;            // fila cheia: epoca nova recusada
  uint32_t falhas_de_escrita;    // programar falhou, ou a releitura nao conferiu
  uint32_t apagamentos;
  uint32_t corrompidos_na_montagem;
  uint32_t slots_pulados;        // slot sujo encontrado no caminho da cabeca

  EstatisticasDaFila()
      : guardados(0), confirmados(0), descartes(0), falhas_de_escrita(0), apagamentos(0),
        corrompidos_na_montagem(0), slots_pulados(0) {}
};

enum ResultadoDaGuarda {
  GUARDADO = 0,
  FILA_CHEIA = 1,       // o setor seguinte tem pendente; a epoca foi recusada
  FALHA_NA_FLASH = 2,   // a midia recusou; o slot e pulado na proxima
  FILA_NAO_MONTADA = 3,
};

class FilaNaFlash {
 public:
  explicit FilaNaFlash(MidiaFlash *midia);

  // Le a particao inteira e reconstroi cabeca, cauda e sessao. Devolve false
  // se a particao nao serve (menos de dois setores, ou tamanho que nao e
  // multiplo de setor) ou se a leitura falhou.
  bool montar();

  // Grava uma epoca. `vetor` nulo = sem features (o payload sai sem `f`).
  ResultadoDaGuarda guardar(const Epoca &e, const VetorDeFeatures *vetor,
                            const InstanteDaEpoca &instante);

  // Copia ate `max` registros pendentes, do mais antigo, para `destino`.
  // Devolve quantos copiou. Nao tira nada da fila.
  uint32_t ler_pendentes(RegistroDeEpoca *destino, uint32_t max);

  // Marca como entregues os `k` pendentes mais antigos -- chame so depois de
  // o servidor confirmar (`interpretar_resposta_do_lote`). Devolve quantos
  // marcou. Diferente da fila em RAM, nao precisa de geracao: nada na flash
  // funde nem reordena, entao os `k` mais antigos de agora sao os `k` lidos.
  uint32_t confirmar(uint32_t k);

  uint32_t pendentes() const { return pendentes_; }
  uint16_t sessao() const { return sessao_; }
  bool montada() const { return montada_; }
  uint32_t slots() const { return slots_; }
  // Pendentes que cabem com certeza antes de a fila recusar: todos os setores
  // menos o da cabeca, que pode estar pela metade.
  uint32_t capacidade_garantida() const {
    return slots_ >= REGISTROS_POR_SETOR ? slots_ - REGISTROS_POR_SETOR : 0;
  }
  const EstatisticasDaFila &estatisticas() const { return stats_; }

 private:
  uint32_t proximo(uint32_t slot) const { return (slot + 1u) % slots_; }
  EstadoDoSlot ler_slot(uint32_t slot, RegistroDeEpoca *r, bool *ok);
  bool slot_em_branco(uint32_t slot, bool *ok);
  bool setor_tem_pendente(uint32_t primeiro_slot, bool *ok);
  void avancar_cauda();

  MidiaFlash *midia_;
  bool montada_;
  uint32_t slots_;
  uint32_t cabeca_;
  uint32_t cauda_;
  uint32_t pendentes_;
  uint32_t prox_seq_;
  uint16_t sessao_;
  EstatisticasDaFila stats_;
};

// Do registro guardado ao JSON do contrato: data o registro
// (`resolucao_para_envio`), desfaz a quantizacao do vetor e chama
// `montar_payload` com a taxa da grade da C2. Mesmos retornos que ele.
ResultadoDeMontagem montar_payload_do_registro(const RegistroDeEpoca &r, uint16_t sessao_atual,
                                               const ResolucaoDeParede &parede_atual,
                                               char *destino, uint32_t tamanho,
                                               uint32_t *escritos,
                                               bool *features_incluidas = 0);

}  // namespace dormio

#endif  // DORMIO_NUCLEO_FILA_FLASH_H
