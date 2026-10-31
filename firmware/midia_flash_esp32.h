// midia_flash_esp32.h -- a particao `dormio` vista pela fila do nucleo (FW-08).
//
// E a unica parte da fila que depende do ESP32: quatro chamadas da API de
// particoes do ESP-IDF. Todo o resto -- o log circular, o CRC, a montagem
// depois de um corte de energia -- esta em `nucleo/fila_flash.h` e e testado
// no host contra uma flash simulada.
//
// ⚠️ NAO EXERCITADO NA PLACA. Este arquivo so passa pelo `make sintaxe`, com
// um stub de `esp_partition.h`. Quem o liga ao laco e o sketch do FW-07 (b),
// e quem o mede e o primeiro boot na placa: `abrir()` falha se a tabela
// gravada nao for a de `partitions.csv`.
//
// Uso:
//   MidiaFlashEsp32 midia;
//   dormio::FilaNaFlash fila(&midia);
//   if (!midia.abrir() || !fila.montar()) { /* sem particao: logar e seguir em RAM */ }

#ifndef DORMIO_MIDIA_FLASH_ESP32_H
#define DORMIO_MIDIA_FLASH_ESP32_H

#include <esp_partition.h>

#include "nucleo/fila_flash.h"

// O subtipo e o nome declarados em `partitions.csv`. Os dois tem de bater,
// senao `abrir()` devolve false -- e e melhor descobrir no boot do que gravar
// a noite numa particao de outra coisa.
const uint8_t SUBTIPO_DA_PARTICAO_DORMIO = 0x40;
#define NOME_DA_PARTICAO_DORMIO "dormio"

class MidiaFlashEsp32 : public dormio::MidiaFlash {
 public:
  MidiaFlashEsp32() : p_(0) {}

  bool abrir() {
    p_ = esp_partition_find_first(
        ESP_PARTITION_TYPE_DATA, static_cast<esp_partition_subtype_t>(SUBTIPO_DA_PARTICAO_DORMIO),
        NOME_DA_PARTICAO_DORMIO);
    return p_ != 0;
  }

  uint32_t tamanho() const { return p_ ? static_cast<uint32_t>(p_->size) : 0; }

  bool ler(uint32_t endereco, void *destino, uint32_t n) {
    return p_ && esp_partition_read(p_, endereco, destino, n) == ESP_OK;
  }

  // Sem criptografia de flash, `esp_partition_write` programa bytes crus, de
  // qualquer tamanho e alinhamento -- inclusive o byte unico de `entregue`.
  bool programar(uint32_t endereco, const void *origem, uint32_t n) {
    return p_ && esp_partition_write(p_, endereco, origem, n) == ESP_OK;
  }

  bool apagar_setor(uint32_t endereco) {
    return p_ && esp_partition_erase_range(p_, endereco, dormio::TAMANHO_DO_SETOR_BYTES) == ESP_OK;
  }

 private:
  const esp_partition_t *p_;
};

#endif  // DORMIO_MIDIA_FLASH_ESP32_H
